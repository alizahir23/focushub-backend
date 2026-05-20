from rest_framework.exceptions import NotFound, PermissionDenied
from .models import Workspace, WorkspaceMember, WorkspaceRole

ROLE_RANK = {
    WorkspaceRole.MEMBER: 1,
    WorkspaceRole.ADMIN: 2,
    WorkspaceRole.OWNER: 3,
}

def get_active_workspace_or_404(workspace_id) -> Workspace:
    try:
        return Workspace.objects.get(id=workspace_id, is_active=True)
    except Workspace.DoesNotExist:
        raise NotFound("Workspace not found")

def get_membership(workspace, user) -> WorkspaceMember:
    try:
        return WorkspaceMember.objects.select_related("workspace", "user").get(
            workspace=workspace, user=user
        )
    except WorkspaceMember.DoesNotExist:
        raise NotFound("Workspace not found")  # don't leak existence

def require_min_role(membership, min_role: str) -> None:
    if ROLE_RANK[membership.role] < ROLE_RANK[min_role]:
        raise PermissionDenied("You do not have permission for this action.")

def count_owners(workspace) -> int:
    return WorkspaceMember.objects.filter(
        workspace=workspace, role=WorkspaceRole.OWNER
    ).count()

def is_last_owner(workspace, user_id) -> bool:
    return (
        count_owners(workspace) == 1
        and WorkspaceMember.objects.filter(
            workspace=workspace, user_id=user_id, role=WorkspaceRole.OWNER
        ).exists()
    )