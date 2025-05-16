from django.contrib import admin
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
    list_display = ('title', 'user', 'category', 'status', 'reported_date', 'upvotes_count', 'image_preview')
    search_fields = ('title', 'description', 'user__username', 'user__email') # Search in related user fields
    list_filter = ('status', 'category', 'reported_date')
    raw_id_fields = ('user', 'category') # Better for lots of users/categories
    readonly_fields = ('reported_date', 'created_at', 'updated_at', 'image_preview_display') # Fields not to be edited directly

    # For displaying the image thumbnail in list_display and readonly_fields
    def image_preview(self, obj):
        from django.utils.html import format_html
        if obj.image:
            return format_html('<a href="{}"><img src="{}" width="50" height="50" style="object-fit: cover;"/></a>', obj.image.url, obj.image.url)
        return "(No image)"
    image_preview.short_description = 'Image Preview'

    def image_preview_display(self, obj): # For the detail view
        from django.utils.html import format_html
        if obj.image:
            return format_html('<img src="{}" width="300" />', obj.image.url)
        return "(No image)"
    image_preview_display.short_description = 'Current Image'


    # To make image_preview_display work in fieldsets, you need to define fieldsets
    # or add it to readonly_fields as done above.
    # If you want more control over layout, use fieldsets:
    # fieldsets = (
    #     (None, {
    #         'fields': ('title', 'description', 'user', 'category', 'status')
    #     }),
    #     ('Location', {
    #         'fields': ('latitude', 'longitude')
    #     }),
    #     ('Media', {
    #         'fields': ('image', 'image_preview_display', 'video_url')
    #     }),
    #     ('Tracking', {
    #         'fields': ('upvotes_count', 'reported_date', 'created_at', 'updated_at'),
    #         'classes': ('collapse',) # Makes this section collapsible
    #     }),
    # )



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