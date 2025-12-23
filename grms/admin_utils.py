from django.core.exceptions import FieldDoesNotExist
from django.db import models


def valid_autocomplete_fields(model_cls, fields):
    """Return only FK/M2M fields that exist on the model."""

    valid = []
    for name in fields:
        try:
            field = model_cls._meta.get_field(name)
        except FieldDoesNotExist:
            continue
        if isinstance(field, (models.ForeignKey, models.ManyToManyField, models.OneToOneField)):
            valid.append(name)
    return tuple(valid)
