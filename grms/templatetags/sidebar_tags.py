from django import template

register = template.Library()


@register.filter
def underscore_to_space(value: object) -> str:
    """Convert underscores to spaces for display labels."""
    if value is None:
        return ""
    return str(value).replace("_", " ")


@register.simple_tag(takes_context=True)
def resolve_model(context: template.Context, model_name: str):
    """Resolve a model from the context-provided lookup function."""
    resolver = context.get("get_model_by_name")
    if callable(resolver):
        model = resolver(model_name)
        if model is not None:
            return getattr(model, "_meta", None)
    return None
