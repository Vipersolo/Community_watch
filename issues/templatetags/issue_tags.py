from django import template
# No need to import models directly if they are passed as arguments to the tag

register = template.Library()

@register.simple_tag
def get_upvote_status(issue, user):
    """
    Checks if a given user has upvoted a given issue.
    Relies on the is_upvoted_by_user method on the Issue model.
    """
    if hasattr(issue, 'is_upvoted_by_user') and callable(issue.is_upvoted_by_user):
        return issue.is_upvoted_by_user(user)
    return False # Default or if method doesn't exist for some reason