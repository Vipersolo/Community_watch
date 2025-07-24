from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserRegisterForm(UserCreationForm):
    # By explicitly defining all the fields here, we override any
    # confusing default behavior and gain full control over validation.
    username = forms.CharField(
        required=True,
        label="Username",
        max_length=150,
        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
    )
    email = forms.EmailField(
        required=True,
        label="Email Address"
    )
    first_name = forms.CharField(required=False, label="First Name")
    last_name = forms.CharField(required=False, label="Last Name")

    class Meta(UserCreationForm.Meta):
        model = User
        # This list tells the form which fields to handle. The password fields
        # are handled automatically by inheriting from UserCreationForm.
        fields = ("username", "email", "first_name", "last_name")


class UserUpdateForm(forms.ModelForm):
    # We can add custom validation or widgets here if needed later
    first_name = forms.CharField(max_length=150, required=True, help_text="Please enter your first name.")
    last_name = forms.CharField(max_length=150, required=True, help_text="Please enter your last name.")

    class Meta:
        model = User
        fields = ['first_name', 'last_name']