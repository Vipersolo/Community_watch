from django.views.generic import ListView
from django.contrib.admin.views.decorators import staff_member_required # For restricting access
from django.db.models import Count
from django.http import JsonResponse # For AJAX responses if you go that route later
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required # For function-based views
from django.contrib import messages
from django.contrib.auth import get_user_model # To get the active User model
from .models import Issue, IssueCategory, Comment
from django.utils.http import urlencode # For safely building query strings
from .forms import CommentForm # Import CommentForm
from .forms import IssueForm # The form we just created
from .models import Upvote # Import Upvote model
from django.db.models import Q # Import Q objects for OR queries
from django.urls import reverse # For generating admin URLs

# (Any existing views like temp_report_issue_placeholder can be removed or commented out)
User = get_user_model()

@login_required # Ensures only logged-in users can access this view
def report_issue(request):
    if request.method == 'POST':
        form = IssueForm(request.POST, request.FILES) # request.FILES is for image uploads
        if form.is_valid():
            issue = form.save(commit=False) # Create Issue instance but don't save to DB yet
            issue.user = request.user # Assign the currently logged-in user

            # Latitude and Longitude should be in form.cleaned_data if populated by JS
            # and defined in the form.
            # The status defaults to 'Reported' as per the model definition.
            # The upvotes_count defaults to 0 as per the model definition.
            # The reported_date defaults to timezone.now as per the model definition.

            issue.save() # Now save the issue to the database
            messages.success(request, 'Your issue has been reported successfully! Thank you for your contribution.')
            # Redirect to a new URL: to the detail page of the new issue (we'll create this view later)
            # For now, let's redirect to the homepage.
            # Replace 'home' with 'issues:issue_detail' and pass issue.pk when detail view is ready
            return redirect('home') # Or: return redirect('issues:issue_detail', pk=issue.pk)
    else: # GET request
        form = IssueForm()

    context = {
        'form': form,
        'page_title': 'Report a New Civic Issue'
    }
    return render(request, 'issues/report_issue.html', context)


def issue_detail(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    comments = issue.comments.all().order_by('created_at') # Or '-created_at' for newest first

    if request.method == 'POST':
        # This part handles new comment submission
        if not request.user.is_authenticated: # Double check, though form might not show
            messages.error(request, "You must be logged in to comment.")
            return redirect('users:login') # Or redirect back to issue_detail

        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.issue = issue
            new_comment.user = request.user
            new_comment.save()
            messages.success(request, 'Your comment has been added successfully.')
            # Redirect to the same page to show the new comment and clear the form
            return redirect('issues:issue_detail', pk=issue.pk)
        else:
            # If form is invalid, we'll re-render the page with errors in comment_form
            # We still need to pass an empty form for GET requests if POST fails
            # So, we fall through to the GET request handling below,
            # but 'comment_form' will contain the errors.
            pass # Let the existing form rendering handle it
    else: # GET request
        comment_form = CommentForm() # An empty form for new comments

    context = {
        'issue': issue,
        'comments': comments,
        'comment_form': comment_form,
        'page_title': f"Issue: {issue.title}"
    }
    return render(request, 'issues/issue_detail.html', context)



# display a list of all reported issues
class IssueListView(ListView):
    model = Issue
    template_name = 'issues/issue_list.html'
    context_object_name = 'issues'
    paginate_by = 10
    ordering = ['-reported_date'] # Default ordering

    def get_queryset(self):
        queryset = super().get_queryset().select_related('user', 'category') # Optimize by prefetching related objects

        # Get filter and search parameters from GET request
        category_filter_name = self.request.GET.get('category', None)
        status_filter = self.request.GET.get('status', None)
        search_query = self.request.GET.get('q', None) # Get search query

        if category_filter_name:
            queryset = queryset.filter(category__name=category_filter_name)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # --- NEW SEARCH LOGIC ---
        if search_query:
            # Using Q objects to search in title OR description
            # title__icontains makes the search case-insensitive
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
        # --- END SEARCH LOGIC ---

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "All Reported Civic Issues"

        # Pass the search query back to the template to display or pre-fill form
        search_query = self.request.GET.get('q', '')
        if search_query:
            context['page_title'] = f"Search Results for: '{search_query}'"
        context['search_query'] = search_query # For pre-filling search bar if not in navbar

        issues_data_list = list(self.object_list.values('pk', 'title', 'latitude', 'longitude', 'status')) # Use self.object_list for current page if paginating map markers
                                                                                                       # Or Issue.objects.all() if all markers always
        context['all_issues_for_map_data'] = issues_data_list # For map markers

        context['categories'] = IssueCategory.objects.all()
        return context



# You might also want a view for "My Reported Issues" for logged-in users
@login_required
def my_reported_issues(request):
    issues = Issue.objects.filter(user=request.user).order_by('-reported_date')
    context = {
        'issues': issues,
        'page_title': "My Reported Issues"
    }
    return render(request, 'issues/my_issues_list.html', context) # Create this template too



@login_required
def toggle_upvote_issue(request, pk):
    issue = get_object_or_404(Issue, pk=pk)
    upvoted = False
    try:
        # Try to create an upvote
        Upvote.objects.create(user=request.user, issue=issue)
        issue.upvotes_count += 1
        upvoted = True
    except IntegrityError: # (user, issue) combination already exists, so it's a duplicate
        # User has already upvoted, so remove the upvote (toggle)
        Upvote.objects.filter(user=request.user, issue=issue).delete()
        issue.upvotes_count -= 1
        # Ensure count doesn't go below zero, though it shouldn't with this logic
        if issue.upvotes_count < 0:
            issue.upvotes_count = 0
        upvoted = False

    issue.save(update_fields=['upvotes_count']) # Efficiently update only this field

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest': # For AJAX calls
        return JsonResponse({'upvoted': upvoted, 'count': issue.upvotes_count})

    # For non-AJAX, redirect back to the issue detail page or where the user came from
    # Using HTTP_REFERER is common but can be unreliable.
    # Prefer redirecting to a known page like the issue detail.
    return redirect('issues:issue_detail', pk=issue.pk)



@staff_member_required
def admin_dashboard(request):
    total_issues = Issue.objects.count()

    issues_by_status_qs = Issue.objects.values('status').annotate(count=Count('status')).order_by('status')
    issues_by_status = {item['status']: item['count'] for item in issues_by_status_qs}
    for status_key, status_display_name in Issue.STATUS_CHOICES: # Use display name mapping
        if status_key not in issues_by_status:
            issues_by_status[status_key] = 0

    # Use display names for keys in the final dict for template
    issues_by_status_display = {
        dict(Issue.STATUS_CHOICES)[status_key]: count
        for status_key, count in issues_by_status.items()
    }

    total_users = User.objects.count()

    ready_for_assignment_status_key = 'Verified' # Use the actual key from STATUS_CHOICES

    # --- NEW/UPDATED STATS ---
    unassigned_issues_query = Q(assigned_to_manager__isnull=True) & Q(status=ready_for_assignment_status_key)
    unassigned_issues_count = Issue.objects.filter(unassigned_issues_query).count()

    # URL for Django Admin changelist, pre-filtered for unassigned issues

    # Build the query parameters for the admin URL
    admin_filter_params = {
        'assigned_to_manager__isnull': 'True', # Note: 'True' as a string for query params
        'status__exact': ready_for_assignment_status_key
        # You can use 'status__exact' or just 'status'. 'status__exact' is more explicit.
    }
    # Note: status__exact=Reported might need to be status__in if multiple initial statuses
    unassigned_issues_admin_url = (
        reverse('admin:issues_issue_changelist') + '?' + urlencode(admin_filter_params)
    ) 
    # You might want to filter for status='Verified' or status__in=['Reported','Verified'] depending on your workflow

    high_priority_open_issues_count = Issue.objects.filter(
        priority='High', 
        assigned_to_manager__isnull=False # Assuming you want open high priority issues that ARE assigned
    ).exclude(status__in=['Resolved', 'Closed-No Action']).count()

    issues_requiring_assistance_count = Issue.objects.filter(status='Requires Assistance').count()
    # --- END NEW/UPDATED STATS ---

    recently_reported_issues = Issue.objects.order_by('-reported_date')[:5]
    total_categories = IssueCategory.objects.count()

    context = {
        'page_title': 'Admin Dashboard',
        'total_issues': total_issues,
        'issues_by_status_display': issues_by_status_display,
        'total_users': total_users,
        'unassigned_issues_count': unassigned_issues_count, # NEW
        'unassigned_issues_admin_url': unassigned_issues_admin_url, # NEW
        'high_priority_open_issues_count': high_priority_open_issues_count, # NEW
        'issues_requiring_assistance_count': issues_requiring_assistance_count, # NEW (if you use this status)
        'recently_reported_issues': recently_reported_issues,
        'total_categories': total_categories,
        'unassigned_issues_count': unassigned_issues_count,
        'unassigned_issues_admin_url': unassigned_issues_admin_url,
    }
    return render(request, 'issues/admin_dashboard.html', context)