from django.db import transaction
import secrets
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound

from .models import (
    InvitationStatus,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMember,
    WorkspaceRole,
)

@transaction.atomic
def create_workspace(*, name: str, description: str, user) -> Workspace:
    workspace = Workspace.objects.create(name=name, description=description)
    WorkspaceMember.objects.create(
        workspace=workspace,
        user=user,
        role=WorkspaceRole.OWNER,
    )
    return workspace


def _generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


@transaction.atomic
def create_invitation(
    *,
    workspace: Workspace,
    email: str,
    role: str,
    invited_by,
    expires_in_days: int = 7,
) -> WorkspaceInvitation:
    email = email.strip().lower()

    if role == WorkspaceRole.OWNER:
        raise ValidationError("Cannot invite someone as owner.")

    if WorkspaceMember.objects.filter(workspace=workspace, user__email__iexact=email).exists():
        raise ValidationError("User is already a member of this workspace.")

    if WorkspaceInvitation.objects.filter(
        workspace=workspace,
        email__iexact=email,
        status=InvitationStatus.PENDING,
    ).exists():
        raise ValidationError("A pending invitation already exists for this email.")

    return WorkspaceInvitation.objects.create(
        workspace=workspace,
        email=email,
        role=role,
        token=_generate_invite_token(),
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(days=expires_in_days),
    )


def get_valid_pending_invitation(token: str) -> WorkspaceInvitation:
    try:
        invite = WorkspaceInvitation.objects.select_related(
            "workspace", "invited_by"
        ).get(token=token)
    except WorkspaceInvitation.DoesNotExist:
        raise NotFound("Invitation not found")

    if invite.status != InvitationStatus.PENDING:
        raise ValidationError("This invitation is no longer valid.")

    if invite.expires_at <= timezone.now():
        raise ValidationError("This invitation has expired.")

    if not invite.workspace.is_active:
        raise ValidationError("This workspace is no longer active.")

    return invite


@transaction.atomic
def accept_invitation(*, invite: WorkspaceInvitation, user) -> WorkspaceMember:
    if user.email.lower() != invite.email.lower():
        raise PermissionDenied("Sign in with the email address that received this invitation.")

    if WorkspaceMember.objects.filter(workspace=invite.workspace, user=user).exists():
        raise ValidationError("You are already a member of this workspace.")

    member = WorkspaceMember.objects.create(
        workspace=invite.workspace,
        user=user,
        role=invite.role,
    )
    invite.status = InvitationStatus.ACCEPTED
    invite.responded_at = timezone.now()
    invite.save(update_fields=["status", "responded_at"])
    return member


@transaction.atomic
def decline_invitation(*, invite: WorkspaceInvitation, user) -> None:
    if user.email.lower() != invite.email.lower():
        raise PermissionDenied(
            "Sign in with the email address that received this invitation."
        )

    invite.status = InvitationStatus.DECLINED
    invite.responded_at = timezone.now()
    invite.save(update_fields=["status", "responded_at"])


def revoke_invitation(*, invite: WorkspaceInvitation) -> None:
    if invite.status != InvitationStatus.PENDING:
        raise ValidationError("Only pending invitations can be revoked.")
    invite.status = InvitationStatus.REVOKED
    invite.responded_at = timezone.now()
    invite.save(update_fields=["status", "responded_at"]) 