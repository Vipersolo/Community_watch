# issues/admin.py

from django.contrib import admin, messages
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import IssueCategory, Issue, Upvote, Comment, IssueImage

# ------------------------------
# IssueCategory Admin
# ------------------------------
@admin.register(IssueCategory)
class IssueCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at',)


# ------------------------------
# Inline: Multiple Issue Images
# ------------------------------
class IssueImageInline(admin.TabularInline):
    model = IssueImage
    extra = 1
    readonly_fields = ('image_thumbnail',)

    def image_thumbnail(self, obj):
        if obj.image:
            return format_html('<a href="{}"><img src="{}" width="150" /></a>', obj.image.url, obj.image.url)
        return "No Image"
    image_thumbnail.short_description = 'Thumbnail Preview'


# ------------------------------
# Issue Admin
# ------------------------------
@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    # Display manager's full name or username
    def assigned_manager_name(self, obj):
        if obj.assigned_to_manager:
            return obj.assigned_to_manager.get_full_name() or obj.assigned_to_manager.username
        return "Not Assigned"
    assigned_manager_name.short_description = 'Manager Name'

    # Show thumbnail in list view
    def list_image_preview(self, obj):
        first_image = obj.images.first()
        if first_image and first_image.image:
            return format_html(
                '<a href="{}"><img src="{}" width="50" height="50" style="object-fit: cover;"/></a>',
                first_image.image.url, first_image.image.url
            )
        return "(No images)"
    list_image_preview.short_description = 'Image Preview'

    list_display = (
        'title',
        'user',
        'category',
        'status',
        'priority',
        'municipal_area',
        'assigned_to_manager',
        'reported_date',
        'upvotes_count',
        'list_image_preview',
    )

    search_fields = (
        'title',
        'description',
        'user__username',
        'user__email',
        'assigned_to_manager__username'
    )

    list_filter = (
        'status',
        'category',
        'priority',
        'municipal_area',
        'assigned_to_manager',
        'reported_date'
    )

    list_editable = ('status', 'priority')
    raw_id_fields = ('user', 'category', 'assigned_to_manager')

    fieldsets = (
        (None, {'fields': ('title', 'description', 'user', 'category')}),
        ('Assignment & Workflow', {
            'fields': (
                'status',
                'priority',
                ('assigned_to_manager', 'assigned_manager_name'),
                'internal_notes',
                'municipal_area'
            )
        }),
        ('Location & Media', {
            'fields': ('latitude', 'longitude', 'video_url')
        }),
        ('Manager Resolution Details (Read-Only for Moderator)', {
            'fields': ('resolution_notes', 'resolution_image'),
            'classes': ('collapse',)
        }),
        ('Tracking & Dates (Read-Only)', {
            'fields': ('upvotes_count', 'reported_date', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = (
        'reported_date', 'created_at', 'updated_at',
        'upvotes_count', 'resolution_notes', 'resolution_image', 'municipal_area',
        'assigned_manager_name'
    )

    inlines = [IssueImageInline]

    # ---------- Custom Admin Actions ----------
    @admin.action(description='Mark selected issues as Verified & Awaiting Assignment')
    def make_verified_awaiting_assignment(self, request, queryset):
        updated_count = queryset.update(status='Verified')
        self.message_user(request, f'{updated_count} issues marked as Verified & Awaiting Assignment.', messages.SUCCESS)

    @admin.action(description='Mark selected issues as Under Review')
    def make_under_review(self, request, queryset):
        updated_count = queryset.update(status='Under Review')
        self.message_user(request, f'{updated_count} issues marked as Under Review.', messages.SUCCESS)

    @admin.action(description='Mark selected issues as Resolved')
    def make_resolved(self, request, queryset):
        updated_count = queryset.update(status='Resolved')
        self.message_user(request, f'{updated_count} issues marked as Resolved.', messages.SUCCESS)

    actions = ['make_verified_awaiting_assignment', 'make_under_review', 'make_resolved']


# ------------------------------
# Upvote Admin
# ------------------------------
@admin.register(Upvote)
class UpvoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'issue', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'issue__title')


# ------------------------------
# Comment Admin
# ------------------------------
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('user', 'issue_link', 'short_comment_text', 'created_at', 'is_recent_comment')
    list_filter = ('created_at', 'user')
    search_fields = ('comment_text', 'user__username', 'issue__title')
    readonly_fields = ('created_at',)

    def issue_link(self, obj):
        if obj.issue:
            url = reverse('admin:issues_issue_change', args=[obj.issue.pk])
            return format_html('<a href="{}">{}</a>', url, obj.issue.title)
        return "No associated issue"
    issue_link.short_description = 'Issue'

    def short_comment_text(self, obj):
        return obj.comment_text[:75] + '...' if len(obj.comment_text) > 75 else obj.comment_text
    short_comment_text.short_description = 'Comment (Excerpt)'

    @admin.display(boolean=True, description='Recent?')
    def is_recent_comment(self, obj):
        return obj.created_at >= timezone.now() - timezone.timedelta(days=7)
