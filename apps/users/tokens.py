from __future__ import annotations

import hashlib

from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .models import RefreshToken as StoredRefreshToken
from .models import User


def hash_token(token: str) -> str:
    """
    Hash a raw token before storing or looking it up.

    We never store raw refresh tokens in the database.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_token_pair(user: User) -> dict[str, str]:
    """
    Create a SimpleJWT access/refresh pair and store the refresh token
    server-side so it can be revoked later.
    """

    refresh = RefreshToken.for_user(user)
    refresh_token = str(refresh)
    access_token = str(refresh.access_token)

    StoredRefreshToken.objects.create(
        user=user,
        token_hash=hash_token(refresh_token),
        jti=refresh["jti"],
        expires_at=timezone.datetime.fromtimestamp(
            refresh["exp"],
            tz=timezone.get_current_timezone(),
        ),
    )

    return {
        "access": access_token,
        "refresh": refresh_token,
    }


def rotate_refresh_token(raw_refresh_token: str) -> dict[str, str]:
    """
    Validate an existing refresh token, revoke it, then issue a new pair.

    This is called by POST /api/v1/auth/refresh.
    """

    stored_token = get_valid_stored_refresh_token(raw_refresh_token)
    user = stored_token.user

    stored_token.is_revoked = True
    stored_token.save(update_fields=["is_revoked"])

    return issue_token_pair(user)


def revoke_refresh_token(raw_refresh_token: str) -> None:
    """
    Revoke one refresh token.

    This is called by POST /api/v1/auth/logout.
    """

    stored_token = get_valid_stored_refresh_token(raw_refresh_token)
    stored_token.is_revoked = True
    stored_token.save(update_fields=["is_revoked"])


def get_valid_stored_refresh_token(raw_refresh_token: str) -> StoredRefreshToken:
    """
    Validate a raw refresh token against:
    - JWT signature
    - JWT expiry
    - DB existence
    - DB revoked flag
    - DB expiry
    """

    if not raw_refresh_token:
        raise AuthenticationFailed("Missing refresh token")

    try:
        jwt_token = RefreshToken(raw_refresh_token)
    except TokenError:
        raise AuthenticationFailed("Invalid refresh token")

    token_hash = hash_token(raw_refresh_token)

    try:
        stored_token = StoredRefreshToken.objects.select_related("user").get(
            token_hash=token_hash,
            jti=jwt_token["jti"],
        )
    except StoredRefreshToken.DoesNotExist:
        raise AuthenticationFailed("Refresh token is not recognized")

    if stored_token.is_revoked:
        raise AuthenticationFailed("Refresh token has been revoked")

    if stored_token.expires_at <= timezone.now():
        raise AuthenticationFailed("Refresh token has expired")

    if not stored_token.user.is_active:
        raise AuthenticationFailed("User account is inactive")

    return stored_token


def issue_access_token(user: User) -> str:
    """
    Issue a fresh access token for a user without creating a refresh token.

    Useful later if we want an endpoint that renews only access tokens.
    """

    return str(AccessToken.for_user(user))

def revoke_all_refresh_tokens_for_user(user: User) -> None:
    """Revoke every non-revoked refresh token for this user (account delete / logout-all)."""
    StoredRefreshToken.objects.filter(user=user, is_revoked=False).update(
        is_revoked=True
    )