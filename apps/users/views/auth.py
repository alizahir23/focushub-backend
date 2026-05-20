from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiResponse, extend_schema

from apps.users.tokens import issue_token_pair, revoke_refresh_token, rotate_refresh_token

from ..firebase import verify_id_token
from ..serializers import (
    FirebaseLoginSerializer,
    RefreshTokenSerializer,
    UserSerializer,
)
from ..services import get_or_create_user_from_firebase


@extend_schema(
    request=FirebaseLoginSerializer,
    responses={
        200: {
            "type": "object",
            "properties": {
                "access": {"type": "string"},
                "refresh": {"type": "string"},
                "user": {"type": "object"},
            },
        }
    },
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def firebase_login(request: Request) -> Response:
    """
    POST /api/v1/auth/firebase

    Exchange a Firebase ID token (Google/Apple sign-in) for our own JWT.
    """
    serializer = FirebaseLoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    id_token = serializer.validated_data["id_token"]
    firebase_payload = verify_id_token(id_token)
    user = get_or_create_user_from_firebase(firebase_payload)
    tokens = issue_token_pair(user)

    if not user.is_active:
        raise AuthenticationFailed("This account has been deactivated.")

    return Response(
        {
            **tokens,
            "user": UserSerializer(user).data,
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(
    request=RefreshTokenSerializer,
    responses={
        200: {
            "type": "object",
            "properties": {
                "access": {"type": "string"},
                "refresh": {"type": "string"},
            },
        }
    },
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def auth_refresh(request: Request) -> Response:
    """
    POST /api/v1/auth/refresh

    Exchange a valid refresh token for a new access + refresh pair.
    Old refresh token is revoked (rotation).
    """
    serializer = RefreshTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    tokens = rotate_refresh_token(serializer.validated_data["refresh"])

    return Response(tokens, status=status.HTTP_200_OK)


@extend_schema(
    request=RefreshTokenSerializer,
    responses={204: OpenApiResponse(description="Logged out")},
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def auth_logout(request: Request) -> Response:
    """
    POST /api/v1/auth/logout

    Revoke the current refresh token.
    """
    serializer = RefreshTokenSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    revoke_refresh_token(serializer.validated_data["refresh"])

    return Response(status=status.HTTP_204_NO_CONTENT)
