from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required # For function-based views
from django.contrib import messages
from .models import Issue # Your Issue model
from .forms import IssueForm # The form we just created

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

