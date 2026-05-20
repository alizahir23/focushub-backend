from __future__ import annotations

from typing import Any

from django.db import transaction

from .models import User


@transaction.atomic
def get_or_create_user_from_firebase(payload: dict[str, Any]) -> User:
    """
    Create or update a local User from a verified Firebase ID token payload.

    Expected Firebase payload fields:
    - uid: Firebase user ID
    - email: user's email
    - name: display name, optional
    - picture: profile photo URL, optional
    """

    firebase_uid = payload.get("uid")
    email = payload.get("email")

    if not firebase_uid:
        raise ValueError("Firebase payload is missing uid")

    if not email:
        raise ValueError("Firebase payload is missing email")

    defaults = {
        "email": email,
        "display_name": payload.get("name") or "",
        "photo_url": payload.get("picture") or "",
    }

    user, created = User.objects.get_or_create(
        firebase_uid=firebase_uid,
        defaults=defaults,
    )

    if not created:
        fields_to_update = []

        if user.email != email:
            user.email = email
            fields_to_update.append("email")

        display_name = payload.get("name") or ""
        if user.display_name != display_name:
            user.display_name = display_name
            fields_to_update.append("display_name")

        photo_url = payload.get("picture") or ""
        if user.photo_url != photo_url:
            user.photo_url = photo_url
            fields_to_update.append("photo_url")

        if fields_to_update:
            fields_to_update.append("updated_at")
            user.save(update_fields=fields_to_update)

    return user