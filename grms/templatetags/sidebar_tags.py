from django import template

register = template.Library()


@register.filter
def underscore_to_space(value: object) -> str:
    """Convert underscores to spaces for display labels."""
    if value is None:
        return ""
    return str(value).replace("_", " ")
