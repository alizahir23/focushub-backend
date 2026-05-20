from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.workspaces.models import InvitationStatus, WorkspaceInvitation, WorkspaceRole
from apps.workspaces.permissions import (
    get_active_workspace_or_404,
    get_membership,
    require_min_role,
)
from apps.workspaces.serializers import (
    InvitationCreateSerializer,
    InvitationSerializer,
    WorkspaceMemberSerializer,
    WorkspaceSerializer,
)
from apps.workspaces.services import (
    accept_invitation,
    create_invitation,
    decline_invitation,
    get_valid_pending_invitation,
    revoke_invitation,
)


@extend_schema(methods=["GET"], responses={200: InvitationSerializer(many=True)})
@extend_schema(methods=["POST"], request=InvitationCreateSerializer, responses={201: InvitationSerializer})
@api_view(["GET", "POST"])
def invitation_list_create(request: Request, workspace_id) -> Response:
    """
    GET  /api/v1/workspaces/:id/invitations  — pending invites (admin+)
    POST /api/v1/workspaces/:id/invitations  — send invite (admin+)
    """
    workspace = get_active_workspace_or_404(workspace_id)
    membership = get_membership(workspace, request.user)

    if request.method == "GET":
        require_min_role(membership, WorkspaceRole.ADMIN)
        invites = WorkspaceInvitation.objects.filter(
            workspace=workspace,
            status=InvitationStatus.PENDING,
        ).order_by("-created_at")
        return Response(InvitationSerializer(invites, many=True).data)

    # POST
    require_min_role(membership, WorkspaceRole.ADMIN)
    serializer = InvitationCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    invite = create_invitation(
        workspace=workspace,
        email=serializer.validated_data["email"],
        role=serializer.validated_data["role"],
        invited_by=request.user,
    )
    return Response(
        InvitationSerializer(invite).data,
        status=status.HTTP_201_CREATED,
    )


@extend_schema(methods=["DELETE"], responses={204: OpenApiResponse(description="Revoked")})
@api_view(["DELETE"])
def invitation_revoke(request: Request, workspace_id, invitation_id) -> Response:
    """
    DELETE /api/v1/workspaces/:id/invitations/:invId
    Revoke a pending invitation (admin+).
    """
    workspace = get_active_workspace_or_404(workspace_id)
    membership = get_membership(workspace, request.user)
    require_min_role(membership, WorkspaceRole.ADMIN)

    try:
        invite = WorkspaceInvitation.objects.get(
            id=invitation_id,
            workspace=workspace,
        )
    except WorkspaceInvitation.DoesNotExist:
        raise NotFound("Invitation not found")

    revoke_invitation(invite=invite)
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    responses={
        200: {
            "type": "object",
            "properties": {
                "workspace": {"type": "object"},
                "membership": {"type": "object"},
            },
        }
    },
)
@api_view(["POST"])
def invitation_accept(request: Request, token: str) -> Response:
    """
    POST /api/v1/invitations/:token/accept
    Logged-in user; email must match invitation.
    """
    invite = get_valid_pending_invitation(token)
    member = accept_invitation(invite=invite, user=request.user)

    workspace = invite.workspace
    return Response(
        {
            "workspace": WorkspaceSerializer(
                workspace,
                context={"request": request, "membership": member},
            ).data,
            "membership": WorkspaceMemberSerializer(member).data,
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(responses={204: OpenApiResponse(description="Declined")})
@api_view(["POST"])
def invitation_decline(request: Request, token: str) -> Response:
    """
    POST /api/v1/invitations/:token/decline
    """
    invite = get_valid_pending_invitation(token)
    decline_invitation(invite=invite, user=request.user)
    return Response(status=status.HTTP_204_NO_CONTENT)