from django.db import models
from django.conf import settings # To get AUTH_USER_MODEL if needed, though not directly for Category
from django.utils import timezone # For default dates if needed, though auto_now_add handles it

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
        ('Reported', 'Reported'),
        ('Under Review', 'Under Review'),
        ('Action Taken', 'Action Taken'),
        ('Resolved', 'Resolved'),
        ('Closed-No Action', 'Closed-No Action'),
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
    image = models.ImageField(upload_to='issue_images/', null=True, blank=True, help_text="Optional image of the issue.")
    video_url = models.URLField(max_length=500, null=True, blank=True, help_text="Optional link to a video (e.g., YouTube, Vimeo).")
    # Status and Tracking
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Reported')
    upvotes_count = models.IntegerField(default=0) # We'll manage this more actively in a later phase
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # For admin and filtering
    reported_date = models.DateTimeField(default=timezone.now) # Could also just use created_at

    class Meta:
        ordering = ['-reported_date'] # Show newest issues first by default

    def __str__(self):
        return f"{self.title} (Reported by: {self.user.username if self.user else 'Unknown'})"
