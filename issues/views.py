from django.views.generic import ListView
from django.contrib.admin.views.decorators import staff_member_required # For restricting access
from django.db.models import Count
from django.http import JsonResponse # For AJAX responses if you go that route later
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required,user_passes_test # For function-based views
from django.contrib import messages
from django.contrib.auth import get_user_model # To get the active User model
from .models import Issue, Comment, IssueCategory, IssueImage  # Your models
from django.utils.http import urlencode # For safely building query strings
from .forms import CommentForm, ManagerIssueUpdateForm # Import CommentForm
from .forms import IssueForm # The form we just created
from .models import Upvote # Import Upvote model
from django.db.models import Q # Import Q objects for OR queries
from django.urls import reverse # For generating admin URLs
from django.db.models import Case, When, Value, IntegerField # <-- ADD THESE EXPLICIT IMPORTS
# (If you had 'from django.db import models', these are technically under models.Case etc.,
# but explicit imports are clearer and often better for linters)

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

            # --- NEW: Handle Multiple Image Uploads ---
            images = request.FILES.getlist('images') # 'images' is the name of our file input
            for image_file in images:
                IssueImage.objects.create(issue=issue, image=image_file)

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
    comments = issue.comments.all().order_by('created_at') # Or '-created_at'

    # Determine if the current user is the assigned manager for this issue
    is_assigned_manager = (request.user.is_authenticated and 
                           hasattr(request.user, 'is_municipal_manager') and 
                           request.user.is_municipal_manager() and 
                           issue.assigned_to_manager == request.user)

    comment_form = CommentForm() # For citizens
    manager_form = None # Initialize manager_form

    if is_assigned_manager:
        manager_form = ManagerIssueUpdateForm(instance=issue) # Pre-fill with current issue data (status, notes)

    if request.method == 'POST':
        if 'submit_comment' in request.POST: # Differentiate comment submission
            if not request.user.is_authenticated:
                messages.error(request, "You must be logged in to comment.")
                return redirect('users:login')

            comment_form_submitted = CommentForm(request.POST)
            if comment_form_submitted.is_valid():
                new_comment = comment_form_submitted.save(commit=False)
                new_comment.issue = issue
                new_comment.user = request.user
                new_comment.save()
                messages.success(request, 'Your comment has been added.')
                return redirect('issues:issue_detail', pk=issue.pk)
            else:
                # If comment form is invalid, re-render with errors
                comment_form = comment_form_submitted # Pass the form with errors back

        elif 'submit_manager_update' in request.POST and is_assigned_manager: # Differentiate manager update
            manager_form_submitted = ManagerIssueUpdateForm(request.POST, request.FILES, instance=issue)
            if manager_form_submitted.is_valid():
                updated_issue = manager_form_submitted.save(commit=False)
                # The form only submits 'status', 'resolution_notes', 'resolution_image'.
                # Only update status if a new one was actually selected by the manager.
                new_status = manager_form_submitted.cleaned_data.get('status')
                if new_status: # Check if a status was selected from the dropdown
                    updated_issue.status = new_status
                # resolution_notes and resolution_image are handled by form.save() due to instance=issue
                updated_issue.save() 
                # Note: The issue_status_changed_notification signal should pick up this save.
                messages.success(request, 'Issue details updated successfully by manager.')
                return redirect('issues:issue_detail', pk=issue.pk)
            else:
                # If manager form is invalid, re-render with errors
                manager_form = manager_form_submitted # Pass the form with errors back

    context = {
        'issue': issue,
        'comments': comments,
        'comment_form': comment_form,
        'manager_form': manager_form, # Pass manager_form to context
        'is_assigned_manager': is_assigned_manager, # Pass flag to template
        'page_title': f"Issue: {issue.title}"
    }
    return render(request, 'issues/issue_detail.html', context)



# display a list of all reported issues
class IssueListView(ListView):
    model = Issue
    template_name = 'issues/issue_list.html'
    context_object_name = 'issues'
    paginate_by = 10
    # ordering = ['-reported_date']

    def get_queryset(self):
        queryset = super().get_queryset().select_related('user', 'category')  # Optimize DB queries

        # --- Filtering and Search ---
        category_filter_name = self.request.GET.get('category', None)
        status_filter = self.request.GET.get('status', None)
        search_query = self.request.GET.get('q', None)

        if category_filter_name:
            queryset = queryset.filter(category__name=category_filter_name)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )

        # --- Dynamic Sorting ---
        sort_option = self.request.GET.get('sort', 'newest')  # Default to 'newest'
        if sort_option == 'upvotes':
            queryset = queryset.order_by('-upvotes_count', '-reported_date')
        elif sort_option == 'oldest':
            queryset = queryset.order_by('reported_date')
        else:
            queryset = queryset.order_by('-reported_date')  # Default fallback

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Page title and search query info
        search_query = self.request.GET.get('q', '')
        if search_query:
            context['page_title'] = f"Search Results for: '{search_query}'"
        else:
            context['page_title'] = "All Reported Civic Issues"
        context['search_query'] = search_query

        # Map marker data (based on paginated results)
        issues_data_list = list(self.object_list.values(
            'pk', 'title', 'latitude', 'longitude', 'status'
        ))
        context['all_issues_for_map_data'] = issues_data_list

        # Support UI filters
        context['categories'] = IssueCategory.objects.all()
        context['current_sort'] = self.request.GET.get('sort', 'newest')

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
    # --- Basic Stats ---
    total_issues = Issue.objects.count()
    total_users = User.objects.count()
    recently_reported_issues = Issue.objects.order_by('-reported_date')[:5]
    total_categories = IssueCategory.objects.count()

    # --- Issues by Status Breakdown (for the list view) ---
    issues_by_status_map = {
        item['status']: item['count'] 
        for item in Issue.objects.values('status').annotate(count=Count('status'))
    }
    issues_by_status_display = {
        status_display: issues_by_status_map.get(status_key, 0)
        for status_key, status_display in Issue.STATUS_CHOICES
    }

    # --- Unassigned Issues Count ---
    ready_for_assignment_status_key = 'Verified'
    unassigned_issues_query = Q(assigned_to_manager__isnull=True) & Q(status=ready_for_assignment_status_key)
    unassigned_issues_count = Issue.objects.filter(unassigned_issues_query).count()
    admin_filter_params = {
        'assigned_to_manager__isnull': 'True',
        'status__exact': ready_for_assignment_status_key
    }
    unassigned_issues_admin_url = reverse('admin:issues_issue_changelist') + '?' + urlencode(admin_filter_params)

    # --- Pending and Resolved Counts ---
    final_statuses = ['Resolved', 'Closed-No Action', 'Invalid', 'Duplicate']
    pending_issues_count = Issue.objects.exclude(status__in=final_statuses).count()
    resolved_issues_count = Issue.objects.filter(status='Resolved').count()

    # --- FIX: ADDED HIGH PRIORITY COUNT CALCULATION ---
    # This counts issues with priority 'High' that are not in a final/closed state.
    high_priority_open_issues_count = Issue.objects.filter(
        priority='High'
    ).exclude(status__in=final_statuses).count()
    
    # --- Optional: Count for issues needing assistance ---
    issues_requiring_assistance_count = Issue.objects.filter(status='Requires Assistance').count()


    context = {
        'page_title': 'Admin Dashboard',
        'total_issues': total_issues,
        'total_users': total_users,
        'recently_reported_issues': recently_reported_issues,
        'total_categories': total_categories,
        'issues_by_status_display': issues_by_status_display,
        'unassigned_issues_count': unassigned_issues_count,
        'unassigned_issues_admin_url': unassigned_issues_admin_url,
        'pending_issues_count': pending_issues_count,
        'resolved_issues_count': resolved_issues_count,
        'high_priority_open_issues_count': high_priority_open_issues_count, # ADDED TO CONTEXT
        'issues_requiring_assistance_count': issues_requiring_assistance_count, # ADDED TO CONTEXT
    }
    return render(request, 'issues/admin_dashboard.html', context)




# Helper function to check if the user is a Municipal Manager
def is_manager(user):
    return user.is_authenticated and hasattr(user, 'is_municipal_manager') and user.is_municipal_manager()

@login_required
@user_passes_test(is_manager, login_url='home') # Redirect to home if not a manager. Or 'users:login'
def manager_dashboard(request):
    # Base queryset for issues assigned to the current manager that are not yet fully closed
    assigned_issues_base = Issue.objects.filter(
        assigned_to_manager=request.user
    ).exclude(
        status__in=['Resolved', 'Closed-No Action']
    )

    # Annotate the queryset with a numeric order for priority
    assigned_issues_annotated = assigned_issues_base.annotate(
        priority_order=Case(
            When(priority='High', then=Value(1)),    # High priority gets 1
            When(priority='Medium', then=Value(2)), # Medium priority gets 2
            When(priority='Low', then=Value(3)),     # Low priority gets 3
            default=Value(4),                        # Any other/null priority gets 4
            output_field=IntegerField(),             # Ensures the result is treated as an integer
        )
    )

    # Now, order by the annotated field 'priority_order', then by 'reported_date'
    assigned_issues = assigned_issues_annotated.order_by('priority_order', 'reported_date')

    context = {
        'page_title': 'My Assigned Issues',
        'assigned_issues': assigned_issues,
    }
    return render(request, 'issues/manager_dashboard.html', context)