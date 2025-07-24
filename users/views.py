from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import AuthenticationForm # For login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordChangeView # and other auth views
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .forms import UserUpdateForm


from .forms import UserRegisterForm
from .models import User # Your custom User model

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Deactivate account till it is confirmed
            user.save()

            # Email Verification Logic
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            verification_link = request.build_absolute_uri(
                reverse_lazy('users:activate', kwargs={'uidb64': uid, 'token': token})
            )
            subject = 'Activate Your CommunityWatch Account'
            message = render_to_string('users/email/account_activation_email.html', {
                'user': user,
                'verification_link': verification_link,
            })
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

            messages.success(request, 'Registration successful! Please check your email to activate your account.')
            return redirect('users:login') # Or a page saying "check your email"
    else:
        form = UserRegisterForm()
    return render(request, 'users/register.html', {'form': form})

def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.email_verified_at = timezone.now()
        user.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend') # Log the user in
        messages.success(request, 'Your account has been activated successfully!')
        return redirect('home') # Or user profile
    else:
        messages.error(request, 'Activation link is invalid or has expired.')
        return redirect('home') # Or a specific error page
    


@login_required
def profile(request):
    if request.method == 'POST':
        # This is for handling the form submission
        update_form = UserUpdateForm(request.POST, instance=request.user)
        if update_form.is_valid():
            update_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('users:profile') # Redirect to the same page to see the changes
    else:
        # This is for displaying the form on a GET request
        update_form = UserUpdateForm(instance=request.user)

    context = {
        'update_form': update_form
    }
    return render(request, 'users/profile.html', context)