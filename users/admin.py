from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    model = User
    # Add 'role' and 'email_verified_at' to the display and editing forms in the admin
    list_display = ('email', 'username', 'first_name', 'last_name', 'role', 'is_staff', 'email_verified_at', 'is_active')
    list_filter = UserAdmin.list_filter + ('role', 'is_staff', 'is_active') # Add 'role' to filters
    # Ensure 'role' is in fieldsets for editing
    # This example assumes you're extending the default UserAdmin fieldsets
    # If you defined fieldsets from scratch, ensure 'role' is included.
    # Example adding 'role' to personal info section:
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (("Personal info"), {"fields": ("first_name", "last_name", "email", "role")}), # Added role here
        (
            ("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (("Important dates"), {"fields": ("last_login", "date_joined", "email_verified_at")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role',)}),
    )
    # Ensure 'email' is prominent
    ordering = ('email',)

admin.site.register(User, CustomUserAdmin)