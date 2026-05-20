from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Public shape of a User in API responses.

    NEVER include fields like password, firebase_uid, or permission flags here
    unless you really want the client to see them. The fields list below is the
    allow-list.
    """

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "display_name",
            "photo_url",
            "is_premium",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_premium", "created_at", "updated_at"]


class FirebaseLoginSerializer(serializers.Serializer):
    """
    Input shape for POST /api/auth/firebase/.

    Client sends:
        { "id_token": "<firebase id token>" }
    """

    id_token = serializers.CharField(write_only=True, trim_whitespace=True)

    def validate_id_token(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("id_token must not be empty")
        return value

class RefreshTokenSerializer(serializers.Serializer):
    """
    Input for POST /api/v1/auth/refresh and POST /api/v1/auth/logout.
    """

    refresh = serializers.CharField(write_only=True, trim_whitespace=True)

    def validate_refresh(self, value: str) -> str:
        if not value:
            raise serializers.ValidationError("refresh must not be empty")
        return value

class UserMeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["display_name", "photo_url"]
    
    def validate_photo_url(self, value: str) -> str:
        from django.core.validators import URLValidator
        from django.core.exceptions import ValidationError as DjangoValidationError

        if not value:
            raise serializers.ValidationError("photoURL must not be empty")
        validator = URLValidator()
        try:
            validator(value)
        except DjangoValidationError:
            raise serializers.ValidationError("photoURL must be a valid URL")
        return value