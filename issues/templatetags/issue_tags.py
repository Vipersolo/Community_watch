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



# --- NEW TEMPLATE TAG for URL manipulation ---
@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    This tag modifies the current URL's GET parameters.
    It takes keyword arguments for the parameters to be added or changed.
    """
    query = context['request'].GET.copy()
    # The 'page' parameter is removed so that sorting starts from the first page
    if 'page' in query:
        del query['page']

    for key, value in kwargs.items():
        query[key] = value

    return query.urlencode()