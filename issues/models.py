from django.db import models
from django.conf import settings # To get AUTH_USER_MODEL if needed, though not directly for Category
from django.utils import timezone # For default dates if needed, though auto_now_add handles it
from django.urls import reverse 
# from django.contrib.gis.db import models as gis_models # Not needed if skipping GeoDjango

# Create your models here.

#issue catogory
class IssueCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True, help_text="Optional description for the category.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Issue Category"
        verbose_name_plural = "Issue Categories" # How it will appear in Django Admin
        ordering = ['name'] # Default ordering when querying

    def __str__(self):
        return self.name
    


#actual civic issues reported by users.
class Issue(models.Model):
    STATUS_CHOICES = [
        ('Reported', 'Reported'),                             # Citizen
        ('Under Review', 'Under Review'),                     # Moderator may set this
        ('Verified', 'Verified & Awaiting Assignment'),     # Moderator
        ('Assigned', 'Assigned to Manager'),                  # Moderator
        ('Manager Acknowledged', 'Manager: Acknowledged'),      # Manager
        ('Manager Investigating', 'Manager: Investigating'),  # Manager
        ('Work In Progress', 'Manager: Work In Progress'),    # Manager
        ('Awaiting Resources', 'Manager: Awaiting Resources'),# Manager
        ('Requires Assistance', 'Manager: Requires Moderator Assistance'), # Manager (informal escalation)
        ('Action Taken', 'Action Taken'),                       # Moderator or Manager
        ('Resolved', 'Resolved'),                             # Moderator or Manager
        ('Closed-No Action', 'Closed-No Action'),             # Moderator
        ('Duplicate', 'Duplicate Issue'),                     # Moderator
        ('Invalid', 'Invalid Report'),                        # Moderator
    ]

    PRIORITY_CHOICES = [
        ('Low', 'Low Priority'),
        ('Medium', 'Medium Priority'),
        ('High', 'High Priority'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    # user will be the Citizen Reporter who submitted the issue
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reported_issues')
    category = models.ForeignKey(IssueCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='issues')
    # Geolocation
    latitude = models.DecimalField(max_digits=10, decimal_places=7) # e.g., 25.2048493
    longitude = models.DecimalField(max_digits=10, decimal_places=7) # e.g., 55.2707828
    # Media
    #image = models.ImageField(upload_to='issue_images/', null=True, blank=True, help_text="Optional image of the issue.")
    video_url = models.URLField(max_length=500, null=True, blank=True, help_text="Optional link to a video (e.g., YouTube, Vimeo).")
    # Status and Tracking
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Reported')
    upvotes_count = models.IntegerField(default=0) # We'll manage this more actively in a later phase
    # --- NEW FIELD ---
    internal_notes = models.TextField(blank=True, null=True, help_text="Internal notes for administrators/moderators only.")
    # --- END NEW FIELD ---
    # --- NEW FIELDS for Manager Workflow ---
    assigned_to_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL, # If manager account is deleted, issue becomes unassigned
        related_name='managed_issues',
        limit_choices_to={'role': 'manager'}, # Important: only allows users with role 'manager'
        help_text="Municipal Manager currently responsible for this issue"
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='Medium',
        help_text="Priority level of the issue (Low, Medium, High)"
    )
    resolution_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Detailed notes from the manager about the resolution or actions taken"
    )
    resolution_image = models.ImageField(
        upload_to='resolution_images/', # Store resolution images in a separate folder
        null=True,
        blank=True,
        help_text="Optional image uploaded by the manager showing the resolved issue or work done"
    )
    # is_escalated, escalation_notes ARE SKIPPED FOR NOW based on your request
    # --- END NEW FIELDS ---
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # For admin and filtering
    reported_date = models.DateTimeField(default=timezone.now) # Could also just use created_at

    municipal_area = models.CharField(
        max_length=255, 
        null=True, 
        blank=True, 
        help_text="Automatically determined municipal area/ward/suburb from location"
    )

    class Meta:
        ordering = ['-priority', '-reported_date'] # Order by priority, then by newest first

    def __str__(self):
        return f"{self.title} (Status: {self.get_status_display()})"
    
    def get_absolute_url(self):
        return reverse('issues:issue_detail', kwargs={'pk': self.pk})
    
    def is_upvoted_by_user(self, user):
        if user.is_authenticated:
            return self.upvotes.filter(user=user).exists()
        return False





class Upvote(models.Model):  # This is line 61 (or around there)
    # ALL THE FOLLOWING LINES MUST BE INDENTED
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    issue = models.ForeignKey('Issue', on_delete=models.CASCADE, related_name='upvotes') # Using string 'Issue' to avoid import order issues
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # THESE LINES MUST BE INDENTED FURTHER (relative to 'class Meta:')
        unique_together = ('user', 'issue')
        verbose_name = "Upvote"
        verbose_name_plural = "Upvotes"

    def __str__(self):
        # THIS LINE MUST BE INDENTED FURTHER (relative to 'def __str__:')
        return f"{self.user.username} upvoted '{self.issue.title}'"



class Comment(models.Model):
    issue = models.ForeignKey(
        'Issue',
        on_delete=models.CASCADE,
        related_name='comments'
    )  # Each comment is linked to one issue; deleting the issue removes its comments

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='issue_comments'
    )  # The user who made the comment; deleting the user removes their comments

    comment_text = models.TextField(
        verbose_name="Your Comment"
    )  # The content of the comment

    created_at = models.DateTimeField(
        auto_now_add=True
    )  # Automatically stores the timestamp when the comment is created

    class Meta:
        ordering = ['created_at']  # Shows oldest comments first; use ['-created_at'] for newest first
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

    def __str__(self):
        return f"Comment by {self.user.username} on '{self.issue.title}' at {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    


class IssueImage(models.Model):
    """A model to store one of the multiple images for a single issue."""
    issue = models.ForeignKey(
        'Issue', 
        on_delete=models.CASCADE, 
        related_name='images', # This is important! We'll use this to get all images for an issue.
        help_text="The issue this image is associated with."
    )
    image = models.ImageField(
        upload_to='issue_images/', # We can keep using the same directory
        help_text="One of the images for the issue."
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for Issue PK {self.issue.pk} uploaded at {self.uploaded_at.strftime('%Y-%m-%d')}"