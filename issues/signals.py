# issues/signals.py
import requests
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
            instance._original_assigned_to_manager_from_db = original_instance_from_db.assigned_to_manager # NEW
        except sender.DoesNotExist:
            # Object doesn't exist in DB yet, so it's effectively a new object or edge case
            instance._original_status_from_db = None
            instance._original_assigned_to_manager_from_db = None # NEW
    else:
        # This is a new instance being created, no original status yet from DB
        instance._original_status_from_db = None
        instance._original_assigned_to_manager_from_db = None # NEW



@receiver(post_save, sender=Issue)
def issue_status_changed_and_assignment_notifications(sender, instance, created, **kwargs):
    """
    Handles notifications for:
    1. Issue status changes (to the reporter).
    2. Issue assignments to managers (to the manager).
    3. New issue creation (to admins - if this logic is also here).
    Separated the assignment logic into its own function above for clarity.
    This function will now primarily focus on status changes and new issue admin notifications.
    """
    original_status = getattr(instance, '_original_status_from_db', None)
    current_status = instance.status

    # --- Logic for Status Change Notification to Reporter ---
    if not created and original_status is not None and original_status != current_status:
        print(f"DEBUG: issue_status_changed_notification: Status has changed from '{original_status}' to '{current_status}' for Issue PK {instance.pk}.")
        try:
            user_to_notify = instance.user # The original reporter
            if not user_to_notify or not user_to_notify.email:
                print(f"DEBUG: Reporter ({user_to_notify}) or their email is missing. No status change email sent.")
                return # Exit this part of the function

            subject = f"Update on Your Reported Issue: '{instance.title[:50]}...'"

            status_choices_dict = dict(Issue.STATUS_CHOICES)
            old_status_display = status_choices_dict.get(original_status, original_status)
            new_status_display = instance.get_status_display()

            context = {
                'user_name': user_to_notify.username,
                'issue_title': instance.title,
                'issue_pk': instance.pk,
                'old_status': old_status_display,
                'new_status': new_status_display,
                'issue_url': settings.SITE_URL + instance.get_absolute_url() if hasattr(instance, 'get_absolute_url') else f"{settings.SITE_URL}/issues/{instance.pk}/",
                'resolution_notes': None, # Initialize
                'resolution_image_url': None # Initialize
            }

            # Add resolution details if the issue is marked Resolved and details exist
            if instance.status == 'Resolved': # Or any other status you consider "resolved by manager"
                if instance.resolution_notes:
                    context['resolution_notes'] = instance.resolution_notes
                if instance.resolution_image:
                    context['resolution_image_url'] = settings.SITE_URL + instance.resolution_image.url # Construct full URL

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
    elif not created and original_status == current_status:
        print(f"DEBUG: issue_status_changed_notification: Status for issue PK {instance.pk} did not change ('{current_status}'). No status change email sent for this save.")

    # --- Logic for New Issue Admin Notification (Keep your existing working version) ---
    if created: # This should be your existing, working admin notification logic
        print(f"DEBUG: New issue admin notification logic triggered for Issue PK {instance.pk} (created={created}).")
        # ... (your existing code for new_issue_admin_notification) ...
        # Example:
        # admin_users = User.objects.filter(is_staff=True, is_active=True, email__isnull=False).exclude(email__exact='')
        # admin_emails = [user.email for user in admin_users if user.email]
        # if admin_emails:
        #     subject_admin = f"New Civic Issue Reported: '{instance.title[:50]}...'"
        #     # ... context_admin and render_to_string for admin email ...
        #     send_mail(...)
        #     print(f"SUCCESS: New issue admin notification sent for issue PK {instance.pk}")


# Ensure only one @receiver(post_save, sender=Issue) decorator is used for a single function,
# OR ensure that if you have multiple functions decorated with this, their logic is clearly distinct
# (e.g., one handles 'created=True', another handles 'created=False and specific field change').
# The new_issue_admin_notification was previously a separate function.
# It's cleaner to keep them as separate functions, each with its own @receiver.



@receiver(post_save, sender=Issue)
def issue_status_changed_notification(sender, instance, created, **kwargs):
    """
    Sends an email notification to the issue reporter when the issue's status changes.
    """
    if not created: # Only on updates
        original_status = getattr(instance, '_original_status_from_db', None)
        current_status = instance.status

        print(f"DEBUG: issue_status_changed_notification called for Issue PK {instance.pk}")
        print(f"DEBUG: Original status (from pre_save): {original_status}")
        print(f"DEBUG: Current status (after save): {current_status}")

        if original_status is not None and original_status != current_status:
            print(f"DEBUG: Status has changed from '{original_status}' to '{current_status}'. Preparing email for reporter.")
            try:
                user_to_notify = instance.user
                if not user_to_notify or not user_to_notify.email:
                    print(f"DEBUG: Reporter ({user_to_notify}) or their email is missing. No status change email sent.")
                    return

                subject = f"Update on Your Reported Issue: '{instance.title[:50]}...'"

                status_choices_dict = dict(Issue.STATUS_CHOICES)
                old_status_display = status_choices_dict.get(original_status, original_status)
                new_status_display = instance.get_status_display()

                context = {
                    'user_name': user_to_notify.username,
                    'issue_title': instance.title,
                    'issue_pk': instance.pk,
                    'old_status': old_status_display,
                    'new_status': new_status_display,
                    'issue_url': settings.SITE_URL + instance.get_absolute_url() if hasattr(instance, 'get_absolute_url') else f"{settings.SITE_URL}/issues/{instance.pk}/",
                    'resolution_notes': None,
                    'resolution_image_url': None
                }

                if instance.status == 'Resolved': # Check if issue is resolved
                    if instance.resolution_notes:
                        context['resolution_notes'] = instance.resolution_notes
                    if instance.resolution_image and hasattr(instance.resolution_image, 'url'): # Check if image exists and has a URL
                        context['resolution_image_url'] = request.build_absolute_uri(instance.resolution_image.url) if hasattr(settings,'SITE_URL') else instance.resolution_image.url
                        # Note: request object is not available in signals. Construct full URL using settings.SITE_URL
                        # context['resolution_image_url'] = settings.SITE_URL + instance.resolution_image.url

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
            print(f"DEBUG: Status for issue PK {instance.pk} did not change ('{current_status}'). No status change email sent.")
        else:
             print(f"DEBUG: No original status found or it was None for issue PK {instance.pk}. No status change email sent based on this logic path (created={created}).")





@receiver(post_save, sender=Issue)
def new_issue_admin_notification(sender, instance, created, **kwargs):
    pass
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




# --- NEW SIGNAL HANDLER for Manager Assignment ---
@receiver(post_save, sender=Issue)
def issue_assigned_to_manager_notification(sender, instance, created, **kwargs):
    """
    Sends an email notification to a Municipal Manager when an issue is newly assigned to them
    or if the assignment changes to them.
    """
    if not created: # Only on updates
        original_manager = getattr(instance, '_original_assigned_to_manager_from_db', None)
        current_manager = instance.assigned_to_manager

        # Print statements for detailed debugging
        print(f"DEBUG: issue_assigned_notification called for Issue PK {instance.pk}")
        print(f"DEBUG: Original manager (from pre_save): {original_manager}")
        print(f"DEBUG: Current manager (after save): {current_manager}")

        if current_manager and (original_manager != current_manager):
            # Assigned to a new manager, or was unassigned and now assigned
            print(f"DEBUG: Issue PK {instance.pk} assigned/re-assigned to manager {current_manager.username}. Preparing email.")
            try:
                if not current_manager.email:
                    print(f"DEBUG: Manager {current_manager.username} has no email address. No assignment email sent.")
                    return

                subject = f"New Issue Assigned to You: '{instance.title[:50]}...'"
                context = {
                    'manager_name': current_manager.username,
                    'issue_title': instance.title,
                    'issue_pk': instance.pk,
                    'issue_priority': instance.get_priority_display(),
                    'reported_by': instance.user.username,
                    'reported_date': instance.reported_date,
                    'issue_url': settings.SITE_URL + instance.get_absolute_url() if hasattr(instance, 'get_absolute_url') else f"{settings.SITE_URL}/issues/{instance.pk}/"
                }

                text_message = render_to_string('emails/issue_assigned_notification.txt', context)
                html_message = render_to_string('emails/issue_assigned_notification.html', context)

                send_mail(
                    subject,
                    text_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [current_manager.email],
                    html_message=html_message,
                    fail_silently=False
                )
                print(f"SUCCESS: Issue assignment email sent to {current_manager.email} for issue PK {instance.pk}")
            except Exception as e:
                print(f"ERROR sending issue assignment email for issue PK {instance.pk} to manager {current_manager.username if current_manager else 'N/A'}: {e}")
        elif not current_manager and original_manager:
             print(f"DEBUG: Issue PK {instance.pk} was unassigned from manager {original_manager.username}. No assignment email sent for this action.")
        # else:
        #    print(f"DEBUG: Manager assignment for issue PK {instance.pk} did not change or manager is still None. No assignment email sent.")





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



@receiver(post_save, sender=Issue)
def fetch_municipal_area_for_new_issue(sender, instance, created, **kwargs):
    """
    When a new issue is created, use its lat/lon to call the Nominatim API
    and save the local municipal area/ward/suburb name.
    """
    # 'created' is True only when the issue is first saved to the database.
    # We also check if the area has not already been populated.
    if created and instance.latitude and instance.longitude and not instance.municipal_area:
        lat = instance.latitude
        lon = instance.longitude

        # Construct the Nominatim API URL. addressdetails=1 is important for getting structured data.
        api_url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&addressdetails=1"

        # It's good practice to set a custom User-Agent for Nominatim's policy
        headers = {
            'User-Agent': 'CommunityWatchProject/1.0 (Contact: your-email@example.com)'
        }

        print(f"Fetching municipal area for new Issue PK {instance.pk}...")

        try:
            response = requests.get(api_url, headers=headers, timeout=10) # 10-second timeout
            response.raise_for_status() # Raise an exception for HTTP errors (like 4xx or 5xx)

            data = response.json()
            address = data.get('address', {})

            # Intelligently find the most specific local area name available.
            # We try a prioritized list of keys that Nominatim might return for a locality.
            # For Kochi, 'suburb' (e.g., 'Kaloor'), 'neighbourhood', or 'quarter' are common.
            area_name = (
                address.get('suburb') or 
                address.get('neighbourhood') or 
                address.get('quarter') or
                address.get('county') # This might be the Taluk name, e.g., 'Kochi Taluk'
            )

            if area_name:
                print(f"SUCCESS: Area found: '{area_name}'. Saving to issue.")
                # Save the retrieved area name back to the issue instance
                instance.municipal_area = area_name

                # We must disconnect the signal temporarily before saving again
                # to prevent an infinite loop of post_save calls.
                post_save.disconnect(fetch_municipal_area_for_new_issue, sender=Issue)
                instance.save(update_fields=['municipal_area'])
                post_save.connect(fetch_municipal_area_for_new_issue, sender=Issue)
            else:
                print(f"WARNING: Could not determine a specific area name from API response for Issue PK {instance.pk}.")

        except requests.exceptions.RequestException as e:
            print(f"ERROR: Could not connect to Nominatim API. {e}")
        except Exception as e:
            print(f"ERROR: An unexpected error occurred while fetching municipal area for Issue PK {instance.pk}: {e}")