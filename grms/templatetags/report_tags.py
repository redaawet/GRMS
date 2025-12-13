from django import template


register = template.Library()


@register.filter
def get_item(mapping, key, default=None):
    if mapping is None:
        return default
    if hasattr(mapping, "get"):
        return mapping.get(key, default)
    return default
