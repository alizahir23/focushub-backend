import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
import uuid
from django.conf import settings

class UserManager(BaseUserManager):
    """
    Manager for the custom User model.

    There is no password-based signup here: identity comes from Firebase, so
    users are created from a verified Firebase ID token, not a password form.
    """

    use_in_migrations = True

    def create_user(self, email: str, firebase_uid: str, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        if not firebase_uid:
            raise ValueError("Users must have a firebase_uid")

        email = self.normalize_email(email)
        user = self.model(email=email, firebase_uid=firebase_uid, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("firebase_uid", f"admin:{email}")

        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    firebase_uid = models.CharField(max_length=128, unique=True)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=150, blank=True)
    photo_url = models.URLField(blank=True)

    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "users"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email


class RefreshToken(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
    )

    token_hash = models.CharField(max_length=128, unique=True)
    jti = models.CharField(max_length=64, unique=True)

    is_revoked = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "refresh_tokens"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"RefreshToken(user={self.user_id}, revoked={self.is_revoked})"