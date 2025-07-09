from django.contrib import admin
from .models import CustomUser, UserProfile

# Basic registration
admin.site.register(CustomUser)
admin.site.register(UserProfile)