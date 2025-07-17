from django.contrib import admin
from .models import User, Profile

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "phone", "role", "is_active", "is_staff", "created_at")
    search_fields = ("name", "email", "phone")
    list_filter = ("is_active", "is_staff", "role")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "bio", "avatar")
    search_fields = ("user__name", "user__email")
