from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.workspaces.models import WorkspaceMember, WorkspaceRole
from apps.workspaces.permissions import (
    get_active_workspace_or_404,
    get_membership,
    require_min_role,
)
from apps.workspaces.serializers import (
    WorkspaceCreateSerializer,
    WorkspaceSerializer,
)
from apps.workspaces.services import create_workspace


@extend_schema(methods=["GET"], responses={200: WorkspaceSerializer(many=True)})
@extend_schema(methods=["POST"], request=WorkspaceCreateSerializer, responses={201: WorkspaceSerializer})
@api_view(["GET", "POST"])
def workspace_list_create(request: Request) -> Response:
    """
    GET  /api/v1/workspaces  — list workspaces I belong to
    POST /api/v1/workspaces  — create workspace; caller becomes owner
    """
    if request.method == "GET":
        memberships = (
            WorkspaceMember.objects.filter(
                user=request.user,
                workspace__is_active=True,
            )
            .select_related("workspace")
            .order_by("-workspace__created_at")
        )
        data = [
            WorkspaceSerializer(
                m.workspace,
                context={"request": request, "membership": m},
            ).data
            for m in memberships
        ]
        return Response(data)

    # POST
    serializer = WorkspaceCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    workspace = create_workspace(
        name=serializer.validated_data["name"],
        description=serializer.validated_data.get("description", ""),
        user=request.user,
    )
    membership = WorkspaceMember.objects.get(workspace=workspace, user=request.user)

    return Response(
        WorkspaceSerializer(
            workspace,
            context={"request": request, "membership": membership},
        ).data,
        status=status.HTTP_201_CREATED,
    )

@extend_schema(methods=["GET"], responses={200: WorkspaceSerializer})
@extend_schema(methods=["PATCH"], request=WorkspaceCreateSerializer, responses={200: WorkspaceSerializer})
@extend_schema(methods=["DELETE"], responses={204: None})
@api_view(["GET", "PATCH", "DELETE"])
def workspace_detail(request: Request, workspace_id) -> Response:
    """
    GET    /api/v1/workspaces/:id
    PATCH  /api/v1/workspaces/:id   (owner only)
    DELETE /api/v1/workspaces/:id   (owner only, soft delete)
    """
    workspace = get_active_workspace_or_404(workspace_id)
    membership = get_membership(workspace, request.user)

    if request.method == "GET":

        return Response(
            WorkspaceSerializer(
                workspace, 
                context={"request": request, "membership": membership},
                ).data, 
                status=status.HTTP_200_OK
            )

    if request.method == "PATCH":
        require_min_role(membership, WorkspaceRole.OWNER)
        serializer = WorkspaceCreateSerializer(
            workspace,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            WorkspaceSerializer(
                workspace, 
                context={"request": request, "membership": membership},
                ).data, 
                status=status.HTTP_200_OK
            )

    # DELETE — soft delete workspace
    require_min_role(membership, WorkspaceRole.OWNER)
    workspace.is_active = False
    workspace.save(update_fields=["is_active", "updated_at"])
    return Response(status=status.HTTP_204_NO_CONTENT)