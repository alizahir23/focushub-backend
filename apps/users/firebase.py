"""
Thin wrapper around the Firebase Admin SDK.

Responsibilities:
- Initialize the Firebase Admin app exactly once at process start.
- Verify Firebase ID tokens sent by the client (Google/Apple sign-in).

Everything in this module is server-side. The Firebase credentials JSON
must never leave the server.
"""

from __future__ import annotations

import logging
import os
from typing import TypedDict

import firebase_admin
from firebase_admin import auth, credentials
from rest_framework.exceptions import AuthenticationFailed

logger = logging.getLogger(__name__)


class FirebaseUserPayload(TypedDict, total=False):
    uid: str
    email: str
    email_verified: bool
    name: str
    picture: str
    firebase: dict


def initialize_firebase() -> None:
    """Initialize the default Firebase Admin app once."""
    if firebase_admin._apps:
        return

    credentials_path = os.getenv("FIREBASE_CREDENTIALS")
    if not credentials_path:
        raise RuntimeError(
            "FIREBASE_CREDENTIALS is not set. "
            "Add the absolute path to your Firebase service account JSON to .env"
        )
    if not os.path.isfile(credentials_path):
        raise RuntimeError(
            f"Firebase credentials file not found at: {credentials_path}"
        )

    cred = credentials.Certificate(credentials_path)
    firebase_admin.initialize_app(cred)
    logger.info("Firebase Admin SDK initialized")


def verify_id_token(id_token: str) -> FirebaseUserPayload:
    """
    Verify a Firebase ID token coming from the client.

    Returns the decoded token payload (uid, email, name, picture, ...).
    Raises DRF AuthenticationFailed if the token is invalid or expired,
    so views can let DRF handle the 401 response automatically.
    """
    if not id_token:
        raise AuthenticationFailed("Missing Firebase ID token")

    try:
        return auth.verify_id_token(id_token)
    except auth.ExpiredIdTokenError:
        raise AuthenticationFailed("Firebase ID token has expired")
    except auth.RevokedIdTokenError:
        raise AuthenticationFailed("Firebase ID token has been revoked")
    except auth.InvalidIdTokenError as exc:
        raise AuthenticationFailed(f"Invalid Firebase ID token: {exc}")
    except Exception as exc:
        logger.exception("Unexpected error verifying Firebase ID token")
        raise AuthenticationFailed("Could not verify Firebase ID token") from exc
