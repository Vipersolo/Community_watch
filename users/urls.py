from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views # Django's built-in auth views

app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('activate/<slug:uidb64>/<slug:token>/', views.activate_account, name='activate'),
    # We'll add login, logout, password reset URLs here
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'), # Default next page is LOGIN_REDIRECT_URL or LOGOUT_REDIRECT_URL

    path('profile/', views.profile, name='profile'),

    # We'll add password reset/change URLs later
    path('password_change/',
         auth_views.PasswordChangeView.as_view(template_name='users/password_change_form.html', success_url=reverse_lazy('users:password_change_done')),
         name='password_change'),
    path('password_change/done/',
         auth_views.PasswordChangeDoneView.as_view(template_name='users/password_change_done.html'),
         name='password_change_done'),

    path('password_reset/',
         auth_views.PasswordResetView.as_view(
             template_name='users/password_reset_form.html',
             email_template_name='users/email/password_reset_email.html', # Our custom email template
             subject_template_name='users/email/password_reset_subject.txt', # Can create this simple text file
             success_url=reverse_lazy('users:password_reset_done')
         ),
         name='password_reset'),
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'),
         name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html', success_url=reverse_lazy('users:password_reset_complete')),
         name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'),
         name='password_reset_complete'),
]