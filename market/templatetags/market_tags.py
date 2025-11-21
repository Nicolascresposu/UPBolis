# market/templatetags/market_tags.py
from django import template

register = template.Library()

@register.filter
def is_vendor(user):
    """Return True if the user is staff or in the Vendors group."""
    if not user.is_authenticated:
        return False
    return user.is_staff or user.groups.filter(name="Vendors").exists()
