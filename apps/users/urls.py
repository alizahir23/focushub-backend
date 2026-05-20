from django.urls import path

from .views import user_me
from .views import auth_logout, auth_refresh, firebase_login

app_name = "users"

urlpatterns = [
    path("auth/firebase", firebase_login, name="auth-firebase"),
    path("auth/refresh", auth_refresh, name="auth-refresh"),
    path("auth/logout", auth_logout, name="auth-logout"),
    path("users/me", user_me, name="users-me"),
]
