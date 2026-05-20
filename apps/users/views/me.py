from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response
from apps.users.serializers import UserMeUpdateSerializer, UserSerializer
from apps.users.tokens import revoke_all_refresh_tokens_for_user


@extend_schema(methods=["GET"], responses={200: UserSerializer})
@extend_schema(methods=["PATCH"], request=UserMeUpdateSerializer, responses={200: UserSerializer})
@extend_schema(methods=["DELETE"], responses={204: OpenApiResponse(description="Account deactivated")})
@api_view(["GET", "PATCH", "DELETE"])
def user_me(request: Request) -> Response:
    user = request.user  # set by JWTAuthentication

    if request.method == "GET":
        return Response(UserSerializer(user).data)

    if request.method == "PATCH":
        serializer = UserMeUpdateSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(user).data)

    # DELETE
    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])
    revoke_all_refresh_tokens_for_user(user)
    return Response(status=status.HTTP_204_NO_CONTENT)