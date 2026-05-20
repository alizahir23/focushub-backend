# Register your models here.
from django.contrib import admin
from .models import Workspace, WorkspaceInvitation, WorkspaceMember

@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)

@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):
    list_display = ("workspace", "user", "role", "joined_at")
    list_filter = ("role",)

@admin.register(WorkspaceInvitation)
class WorkspaceInvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "token", "status", "invited_by", "created_at")
    list_filter = ("status",)