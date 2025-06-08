# issues/urls.py
from django.urls import path
from . import views # Assuming you'll have views in issues/views.py later

app_name = 'issues' # THIS LINE IS CRUCIAL

urlpatterns = [
    # Example:
    path('report/', views.report_issue, name='report_issue'),
    path('<int:pk>/', views.issue_detail, name='issue_detail'),
    path('', views.IssueListView.as_view(), name='issue_list'), # For all issues
    path('my-issues/', views.my_reported_issues, name='my_reported_issues'), # For user's issues
    path('<int:pk>/upvote/', views.toggle_upvote_issue, name='toggle_upvote_issue'),
    # Add your issue-related URL patterns here as you build them
     # --- NEW URL for Admin Dashboard ---
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/manager/', views.manager_dashboard, name='manager_dashboard'), # NEW URL
]