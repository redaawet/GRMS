from django.core.exceptions import FieldDoesNotExist


def valid_autocomplete_fields(model, fields):
    """
    Return only fields that exist on model and are FK or M2M.
    Prevents admin.E037 / admin.E038.
    """
    out = []
    for name in fields:
        try:
            field = model._meta.get_field(name)
        except FieldDoesNotExist:
            continue
        if getattr(field, "many_to_one", False) or getattr(field, "many_to_many", False):
            out.append(name)
    return tuple(out)


def valid_list_display(model, admin_cls, fields):
    """
    Return only fields/callables valid for list_display.
    Prevents admin.E108.
    """
    out = []
    model_fields = {field.name for field in model._meta.get_fields() if getattr(field, "name", None)}
    for name in fields:
        if name in model_fields:
            out.append(name)
        elif hasattr(admin_cls, name):
            out.append(name)
        elif hasattr(model, name):
            out.append(name)
    return tuple(out)
