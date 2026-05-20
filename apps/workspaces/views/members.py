from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.workspaces.models import WorkspaceMember, WorkspaceRole
from apps.workspaces.permissions import (
    get_active_workspace_or_404,
    get_membership,
    is_last_owner,
    require_min_role,
)
from apps.workspaces.serializers import (
    WorkspaceMemberRoleUpdateSerializer,
    WorkspaceMemberSerializer,
)


@extend_schema(methods=["GET"], responses={200: WorkspaceMemberSerializer(many=True)})
@api_view(["GET"])
def member_list(request: Request, workspace_id) -> Response:
    """
    GET /api/v1/workspaces/:id/members
    Any member can list members.
    """
    workspace = get_active_workspace_or_404(workspace_id)
    get_membership(workspace, request.user)  # 404 if not a member

    members = (
        WorkspaceMember.objects.filter(workspace=workspace)
        .select_related("user")
        .order_by("-joined_at")
    )
    serializer = WorkspaceMemberSerializer(members, many=True)
    return Response(serializer.data)


@extend_schema(methods=["PATCH"], request=WorkspaceMemberRoleUpdateSerializer, responses={200: WorkspaceMemberSerializer})
@extend_schema(methods=["DELETE"], responses={204: None})
@api_view(["PATCH", "DELETE"])
def member_detail(request: Request, workspace_id, user_id) -> Response:
    """
    PATCH  /api/v1/workspaces/:id/members/:userId  — owner changes role (admin/member)
    DELETE /api/v1/workspaces/:id/members/:userId  — leave (self) or kick (owner/admin)
    """
    workspace = get_active_workspace_or_404(workspace_id)
    actor = get_membership(workspace, request.user)

    try:
        target = WorkspaceMember.objects.select_related("user").get(
            workspace=workspace,
            user_id=user_id,
        )
    except WorkspaceMember.DoesNotExist:
        raise NotFound("Member not found")

    if request.method == "PATCH":
        require_min_role(actor, WorkspaceRole.OWNER)

        if target.role == WorkspaceRole.OWNER:
            raise PermissionDenied("Cannot change an owner's role via this endpoint.")

        serializer = WorkspaceMemberRoleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target.role = serializer.validated_data["role"]
        target.save(update_fields=["role"])
        return Response(WorkspaceMemberSerializer(target).data)

    # DELETE
    is_self = request.user.id == target.user_id

    if is_self:
        if is_last_owner(workspace, request.user.id):
            raise PermissionDenied("Cannot leave as the last owner of this workspace.")
        target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # Kick someone else
    if actor.role == WorkspaceRole.OWNER:
        if target.role == WorkspaceRole.OWNER:
            raise PermissionDenied("Cannot remove another owner.")
        target.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if actor.role == WorkspaceRole.ADMIN:
        if target.role == WorkspaceRole.MEMBER:
            target.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        raise PermissionDenied("Admins can only remove members.")

    raise PermissionDenied("You do not have permission to remove this member.")