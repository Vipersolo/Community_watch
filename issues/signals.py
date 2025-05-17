# issues/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Issue
from .models import Comment
from django.contrib.auth import get_user_model

User = get_user_model()


# Receiver to store the original status before the instance is saved
@receiver(pre_save, sender=Issue)
def store_original_issue_status(sender, instance, **kwargs):
    """
    Before saving an issue, if it's an update (not a new creation),
    store its current status from the database onto the instance
    as a temporary attribute.
    """
    if instance.pk:  # Check if this is an existing instance (has a primary key)
        try:
            # Fetch the current state from the database
            original_instance_from_db = sender.objects.get(pk=instance.pk)
            instance._original_status_from_db = original_instance_from_db.status
        except sender.DoesNotExist:
            # Object doesn't exist in DB yet, so it's effectively a new object or edge case
            instance._original_status_from_db = None
    else:
        # This is a new instance being created, no original status yet from DB
        instance._original_status_from_db = None


@receiver(post_save, sender=Issue)
def issue_status_changed_notification(sender, instance, created, **kwargs):
    """
    Sends an email notification to the issue reporter when the issue's status changes.
    Only sends if the instance is being updated (not created) and if the status field
    has actually changed compared to its state before this save operation.
    """
    if not created: # Only on updates, not new issue creation
        original_status = getattr(instance, '_original_status_from_db', None)
        current_status = instance.status

        # Print statements for detailed debugging
        print(f"DEBUG: issue_status_changed_notification called for Issue PK {instance.pk}")
        print(f"DEBUG: Is created? {created}")
        print(f"DEBUG: Original status (from pre_save): {original_status}")
        print(f"DEBUG: Current status (after save): {current_status}")

        if original_status is not None and original_status != current_status:
            print(f"DEBUG: Status has changed from '{original_status}' to '{current_status}'. Preparing email.")
            try:
                user_to_notify = instance.user
                if not user_to_notify or not user_to_notify.email:
                    print(f"DEBUG: User to notify ({user_to_notify}) or their email is missing. No email sent.")
                    return

                subject = f"Update on Your Reported Issue: '{instance.title[:50]}...'"
                
                # Get display name for statuses
                status_choices_dict = dict(Issue.STATUS_CHOICES)
                old_status_display = status_choices_dict.get(original_status, original_status) # Fallback to key if not found
                new_status_display = instance.get_status_display() # Uses model's own method

                context = {
                    'user_name': user_to_notify.username,
                    'issue_title': instance.title,
                    'issue_pk': instance.pk,
                    'old_status': old_status_display,
                    'new_status': new_status_display,
                    'issue_url': settings.SITE_URL + instance.get_absolute_url() if hasattr(instance, 'get_absolute_url') else f"{settings.SITE_URL}/issues/{instance.pk}/"
                }
                
                text_message = render_to_string('emails/issue_status_update.txt', context)
                html_message = render_to_string('emails/issue_status_update.html', context)

                send_mail(
                    subject,
                    text_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user_to_notify.email],
                    html_message=html_message,
                    fail_silently=False
                )
                print(f"SUCCESS: Status change email sent to {user_to_notify.email} for issue PK {instance.pk} (Status: {original_status} -> {current_status})")
            except Exception as e:
                print(f"ERROR sending status change email for issue PK {instance.pk}: {e}")
        elif original_status == current_status:
            print(f"DEBUG: Status for issue PK {instance.pk} did not change ('{current_status}'). No email sent.")
        else: # original_status was None (e.g. issue was just created, or pre_save didn't find it)
             print(f"DEBUG: No original status found or it was None for issue PK {instance.pk} (created={created}). No status change email sent based on this logic path.")

# Ensure your other working signal handlers (new_comment_notification, new_issue_admin_notification) are also in this file
# For example:
# @receiver(post_save, sender=Comment)
# def new_comment_notification(sender, instance, created, **kwargs):
#     # ... your working code ...

# @receiver(post_save, sender=Issue) # Note: this is also on Issue post_save
# def new_issue_admin_notification(sender, instance, created, **kwargs):
#     if created: # This one should ONLY run if created is True
#         # ... your working code for admin notification ...






@receiver(post_save, sender=Comment)
def new_comment_notification(sender, instance, created, **kwargs):
    """
    Sends an email notification to the issue reporter when a new comment is made on their issue,
    unless the reporter is the one who made the comment.
    """
    if created: # Only when a new comment is created
        issue_reporter = instance.issue.user
        commenter = instance.user

        if issue_reporter != commenter: # Don't notify if reporter comments on their own issue
            subject = f"New Comment on Your Issue: '{instance.issue.title[:50]}...'"
            
            context = {
                'issue_reporter_name': issue_reporter.username,
                'issue_title': instance.issue.title,
                'issue_pk': instance.issue.pk,
                'commenter_name': commenter.username,
                'comment_text_snippet': instance.comment_text[:100] + ('...' if len(instance.comment_text) > 100 else ''),
                'issue_url': settings.SITE_URL + instance.issue.get_absolute_url() if hasattr(instance.issue, 'get_absolute_url') else f"{settings.SITE_URL}/issues/{instance.issue.pk}/"
            }

            text_message = render_to_string('emails/new_comment_notification.txt', context)
            html_message = render_to_string('emails/new_comment_notification.html', context)

            send_mail(
                subject,
                text_message,
                settings.DEFAULT_FROM_EMAIL,
                [issue_reporter.email],
                html_message=html_message,
                fail_silently=False
            )
            print(f"New comment email sent to {issue_reporter.email} for issue PK {instance.issue.pk}")
        # else:
        #     print(f"Commenter {commenter.username} is the issue reporter. No notification sent for issue PK {instance.issue.pk}")




@receiver(post_save, sender=Issue)
def new_issue_admin_notification(sender, instance, created, **kwargs):
    """
    Sends an email notification to all staff users when a new issue is created.
    """
    if created: # Only when a new issue is first reported
        admin_users = User.objects.filter(is_staff=True, is_active=True, email__isnull=False).exclude(email__exact='')
        admin_emails = [user.email for user in admin_users if user.email] # Ensure email exists

        if admin_emails:
            subject = f"New Civic Issue Reported: '{instance.title[:50]}...'"
            
            # Construct link to the admin change page for the issue
            admin_issue_url = f"{settings.SITE_URL}/admin/issues/issue/{instance.pk}/change/"
            # Or, if you have a user-facing detail page you prefer them to see first:
            # user_issue_url = settings.SITE_URL + instance.get_absolute_url() if hasattr(instance, 'get_absolute_url') else f"{settings.SITE_URL}/issues/{instance.pk}/"


            context = {
                'issue_title': instance.title,
                'issue_description_snippet': instance.description[:150] + ('...' if len(instance.description) > 150 else ''),
                'reporter_name': instance.user.username,
                'category_name': instance.category.name if instance.category else "N/A",
                'reported_date': instance.reported_date,
                'admin_issue_url': admin_issue_url,
                # 'user_issue_url': user_issue_url # if you prefer this
            }

            text_message = render_to_string('emails/new_issue_admin_notification.txt', context)
            html_message = render_to_string('emails/new_issue_admin_notification.html', context)

            send_mail(
                subject,
                text_message,
                settings.DEFAULT_FROM_EMAIL,
                admin_emails, # Send to all staff users
                html_message=html_message,
                fail_silently=False
            )
            print(f"New issue admin notification sent for issue PK {instance.pk} to: {admin_emails}")