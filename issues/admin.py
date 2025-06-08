from django.contrib import admin, messages
from .models import IssueCategory, Issue, Upvote, Comment# Import your models

# Register your models here.

@admin.register(IssueCategory)
class IssueCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)


#Register Issue

@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'user', 
        'category', 
        'status', 
        'priority',  # ADDED
        'assigned_to_manager', # ADDED
        'reported_date', 
        'upvotes_count',
        'image_preview'
    )
    search_fields = (
        'title', 
        'description', 
        'user__username', 
        'user__email', 
        'assigned_to_manager__username' # ADDED search by assigned manager
    )
    list_filter = (
        'status', 
        'category', 
        'priority', # ADDED
        'assigned_to_manager', # ADDED
        'reported_date'
    )
    list_editable = ('status', 'priority') # ADDED priority and assigned_to_manager

    raw_id_fields = ('user', 'category', 'assigned_to_manager') # ADDED assigned_to_manager for better UX if many managers

    # Define fieldsets for better layout, including new fields
    fieldsets = (
        (None, { # Main information section
            'fields': ('title', 'description', 'user', 'category')
        }),
        ('Assignment & Workflow', { # NEW/UPDATED Section
            'fields': ('status', 'priority', 'assigned_to_manager', 'internal_notes')
        }),
        ('Location & Media', {
            'fields': ('latitude', 'longitude', 'image', 'image_preview_display', 'video_url')
        }),
        ('Manager Resolution Details (Read-Only for Moderator)', { # For Moderator to view what Manager submitted
            'fields': ('resolution_notes', 'resolution_image'), # Add a preview for resolution_image if desired
            'classes': ('collapse',) # Makes this section collapsible
        }),
        ('Tracking & Dates (Read-Only)', {
            'fields': ('upvotes_count', 'reported_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = (
        'reported_date', 'created_at', 'updated_at', 
        'image_preview_display', 'upvotes_count',
        'resolution_notes', 'resolution_image' # Moderators view these, Managers edit them via their interface
    )

    # Custom Admin Actions (keep existing ones, potentially add more)
    @admin.action(description='Mark selected issues as Verified & Awaiting Assignment')
    def make_verified_awaiting_assignment(self, request, queryset):
        updated_count = queryset.update(status='Verified') # Assuming 'Verified' is a status before assignment
        self.message_user(request, f'{updated_count} issues were successfully marked as Verified & Awaiting Assignment.', messages.SUCCESS)

    @admin.action(description='Mark selected issues as Under Review')
    def make_under_review(self, request, queryset):
        updated_count = queryset.update(status='Under Review')
        self.message_user(request, f'{updated_count} issues were successfully marked as Under Review.', messages.SUCCESS)

    @admin.action(description='Mark selected issues as Resolved')
    def make_resolved(self, request, queryset):
        # Consider if resolution notes/image are mandatory when Moderator resolves
        updated_count = queryset.update(status='Resolved')
        self.message_user(request, f'{updated_count} issues were successfully marked as Resolved.', messages.SUCCESS)

    actions = ['make_verified_awaiting_assignment', 'make_under_review', 'make_resolved'] # Add new actions

    # Image preview methods (keep as they are)
    def image_preview(self, obj):
        from django.utils.html import format_html
        if obj.image:
            return format_html('<a href="{}"><img src="{}" width="50" height="50" style="object-fit: cover;"/></a>', obj.image.url, obj.image.url)
        return "(No image)"
    image_preview.short_description = 'Image Preview'

    def image_preview_display(self, obj):
        from django.utils.html import format_html
        if obj.image:
            return format_html('<img src="{}" width="300" />', obj.image.url)
        return "(No image)"
    image_preview_display.short_description = 'Current Image'



@admin.register(Upvote)
class UpvoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'issue', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'issue__title')




@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'issue_link', 'short_comment_text', 'created_at', 'is_recent_comment')
    list_filter = ('created_at', 'user')
    search_fields = ('comment_text', 'user__username', 'issue__title')
    readonly_fields = ('created_at',) # Should not be editable

    def issue_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        if obj.issue:
            # Assuming your Issue model's admin change page is the default
            url = reverse('admin:issues_issue_change', args=[obj.issue.pk])
            return format_html('<a href="{}">{}</a>', url, obj.issue.title)
        return "No associated issue"
    issue_link.short_description = 'Issue'

    def short_comment_text(self, obj):
        return obj.comment_text[:75] + '...' if len(obj.comment_text) > 75 else obj.comment_text
    short_comment_text.short_description = 'Comment (Excerpt)'

    @admin.display(boolean=True, description='Recent?') # For boolean display
    def is_recent_comment(self, obj):
        from django.utils import timezone
        return obj.created_at >= timezone.now() - timezone.timedelta(days=7)