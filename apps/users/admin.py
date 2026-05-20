from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "display_name", "is_premium", "is_active", "created_at")
    search_fields = ("email", "display_name", "firebase_uid")
    list_filter = ("is_premium", "is_active", "is_staff")
    readonly_fields = ("id", "firebase_uid", "created_at", "updated_at", "last_login")
