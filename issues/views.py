from django.views.generic import ListView
from django.http import JsonResponse # For AJAX responses if you go that route later
from django.db import IntegrityError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required # For function-based views
from django.contrib import messages
from .models import Issue, IssueCategory, Comment
from .forms import CommentForm # Import CommentForm
from .forms import IssueForm # The form we just created
from .models import Upvote # Import Upvote model

# (Any existing views like temp_report_issue_placeholder can be removed or commented out)

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
    template_name = 'issues/issue_list.html' # Specify your own template name
    context_object_name = 'issues' # How you'll refer to the list in the template
    paginate_by = 10 # Show 10 issues per page
    ordering = ['-reported_date'] # Default ordering

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = "All Reported Civic Issues"
        # For the map, we'll pass all issues (or at least their coordinates and titles)
        # If performance is an issue with many issues, you might only pass issues for the current page,
        # or implement more advanced map clustering/loading strategies.
        # For now, let's pass all for simplicity in map display.
        #-----------------------------------------------------------
        # Pass the Python list of dictionaries directly
        # Ensure it's converted to a list from a QuerySet for json_script
        issues_data_list = list(Issue.objects.all().values('pk', 'title', 'latitude', 'longitude', 'status'))
        context['all_issues_for_map_data'] = issues_data_list # Renamed for clarity
        # You could also get distinct categories for filtering options
        context['categories'] = IssueCategory.objects.all()
        return context

    def get_queryset(self):
        queryset = super().get_queryset()
        category_filter = self.request.GET.get('category')
        status_filter = self.request.GET.get('status')

        if category_filter:
            queryset = queryset.filter(category__name=category_filter)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

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