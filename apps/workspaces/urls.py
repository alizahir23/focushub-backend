from django.urls import path

from .views import (
    member_detail,
    member_list,
    workspace_detail,
    workspace_list_create,
    invitation_list_create,
    invitation_revoke,
    invitation_accept,
    invitation_decline,
)

app_name = "workspaces"

urlpatterns = [
    path("workspaces", workspace_list_create, name="workspace-list-create"),
    path("workspaces/<uuid:workspace_id>", workspace_detail, name="workspace-detail"),
    path(
        "workspaces/<uuid:workspace_id>/members",
        member_list,
        name="workspace-member-list",
    ),
    path(
        "workspaces/<uuid:workspace_id>/members/<uuid:user_id>",
        member_detail,
        name="workspace-member-detail",
    ),
    path(
        "workspaces/<uuid:workspace_id>/invitations",
        invitation_list_create,
        name="invitation-list-create",
    ),
    path(
        "workspaces/<uuid:workspace_id>/invitations/<uuid:invitation_id>",
        invitation_revoke,
        name="invitation-revoke",
    ),
    path(
        "invitations/<str:token>/accept",
        invitation_accept,
        name="invitation-accept",
    ),
    path(
        "invitations/<str:token>/decline",
        invitation_decline,
        name="invitation-decline",
    ),
]