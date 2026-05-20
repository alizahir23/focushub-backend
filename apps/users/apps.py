import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class UsersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.users"
    label = "users"

    def ready(self) -> None:
        from .firebase import initialize_firebase

        try:
            initialize_firebase()
        except Exception:
            logger.exception("Firebase Admin SDK failed to initialize")
