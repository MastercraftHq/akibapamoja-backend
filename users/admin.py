from django.contrib import admin
from .models import User, Profile


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id", "full_name", "email", "phone", "role", "is_active", "is_staff", "created_at"
    )
    search_fields = ("first_name", "last_name", "email", "phone")
    list_filter = ("is_active", "is_staff", "role")

    @admin.display(description="Name")
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "bio", "avatar")
    search_fields = ("user__first_name", "user__last_name", "user__email")