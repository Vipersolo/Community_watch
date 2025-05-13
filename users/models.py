from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone # For email_verified_at

class User(AbstractUser):
    ROLE_CHOICES = (
        ('citizen', 'Citizen Reporter'),
        ('admin', 'Administrator'),
    )
    # We want email to be the unique identifier for login
    email = models.EmailField(unique=True) # Override to make it unique
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='citizen')
    email_verified_at = models.DateTimeField(null=True, blank=True)
    # 'name' field from your project plan can be covered by first_name/last_name
    # or add a separate 'full_name' field if preferred.
    # For simplicity, we'll rely on first_name and last_name.

    # If you want 'email' to be the username field:
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] # 'username' still needed for createsuperuser, but email is for login
                                   # If you truly want to get rid of username,
                                   # REQUIRED_FIELDS can be empty, but requires more UserAdmin customization.
                                   # For now, let's keep username for simplicity with admin and createsuperuser.

    def __str__(self):
        return self.email

    def is_platform_admin(self): # A helper method
        return self.role == 'admin'