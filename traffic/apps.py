from django.apps import AppConfig


class TrafficConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "traffic"

    def ready(self):  # pragma: no cover - side effect registration
        from . import signals  # noqa: F401
