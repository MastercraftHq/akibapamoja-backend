from django.contrib import admin
from .models import Group, Membership

@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "admin", "created_at")
    search_fields = ("name", "slug", "admin__email")
    prepopulated_fields = {"slug": ("name",)}

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "group", "role", "status", "joined_at")
    search_fields = ("user__email", "group__name", "role", "status")