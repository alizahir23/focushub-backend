from rest_framework import serializers
from django.conf import settings

from apps.users.models import User
from .models import Workspace, WorkspaceMember, WorkspaceRole, WorkspaceInvitation


class WorkspaceSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "id", 
            "name", 
            "description",
            "created_at",
            "updated_at",
            "my_role"
        ]
    
    def get_my_role(self, obj: Workspace) -> str:
        membership = self.context["membership"]
        return membership.role

class WorkspaceCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Workspace
        fields = [
            "name",
            "description"
        ]

class WorkspaceMemberUserSerializer(serializers.ModelSerializer):
    """Small public user shape inside a member list — not full UserSerializer."""

    class Meta:
        model = User
        fields = ["id", "email", "display_name", "photo_url"]


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user = WorkspaceMemberUserSerializer(read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = ["id", "user", "role", "joined_at"]


class WorkspaceMemberRoleUpdateSerializer(serializers.Serializer):
    """PATCH body: only role changes, and only to admin/member in v1."""

    role = serializers.ChoiceField(
        choices=[
            (WorkspaceRole.ADMIN, "Admin"),
            (WorkspaceRole.MEMBER, "Member"),
        ]
    )


class InvitationCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(
        choices=[WorkspaceRole.ADMIN, WorkspaceRole.MEMBER],
        default=WorkspaceRole.MEMBER,
    )

class InvitationSerializer(serializers.ModelSerializer):
    invite_url = serializers.SerializerMethodField()

    class Meta:
        model = WorkspaceInvitation
        fields = [
            "id", "email", "role", "status", "token",
            "expires_at", "created_at", "invite_url",
        ]
        read_only_fields = fields  # all read on list/create response

    def get_invite_url(self, obj) -> str:
        base = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        return f"{base.rstrip('/')}/invitations/{obj.token}"
