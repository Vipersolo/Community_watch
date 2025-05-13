from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserRegisterForm(UserCreationForm):
    # Add any extra fields from your User model you want on the registration form
    # For example, first_name, last_name
    first_name = forms.CharField(max_length=30, required=False, help_text='Optional.')
    last_name = forms.CharField(max_length=150, required=False, help_text='Optional.')
    email = forms.EmailField(required=True) # Ensure email is present and validated

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email')
        # If USERNAME_FIELD is 'email', 'username' might not be needed here if you adjust UserCreationForm
        # But since we kept 'username' for createsuperuser, we include it.
        # Ensure 'email' is listed if it's not the USERNAME_FIELD.
        # fields = ('username', 'email', 'first_name', 'last_name') # if you want explicit order