from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    # Add 'role' and 'email_verified_at' to the display and editing forms in the admin
    list_display = ('email', 'username', 'first_name', 'last_name', 'role', 'is_staff', 'email_verified_at', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'email_verified_at')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )
    # Ensure 'email' is prominent
    ordering = ('email',)

admin.site.register(User, CustomUserAdmin)