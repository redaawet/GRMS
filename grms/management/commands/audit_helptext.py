from __future__ import annotations

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from grms.helptexts import HELP_TEXTS


class Command(BaseCommand):
    help = "Validate help text registry entries against model fields."

    def handle(self, *args, **options):
        missing_models = []
        missing_fields = []
        empty_text = []

        for model_label, fields in HELP_TEXTS.items():
            try:
                app_label, model_name = model_label.split(".", 1)
                model = apps.get_model(app_label, model_name)
            except (ValueError, LookupError):
                missing_models.append(model_label)
                continue

            for field_name, payload in fields.items():
                try:
                    model._meta.get_field(field_name)
                except Exception:
                    missing_fields.append(f"{model_label}.{field_name}")
                    continue

                help_text = payload.get("help_text") if isinstance(payload, dict) else payload
                if not help_text:
                    empty_text.append(f"{model_label}.{field_name}")

        if missing_models or missing_fields or empty_text:
            lines = []
            if missing_models:
                lines.append("Missing models:")
                lines.extend(f"  - {label}" for label in missing_models)
            if missing_fields:
                lines.append("Missing fields:")
                lines.extend(f"  - {name}" for name in missing_fields)
            if empty_text:
                lines.append("Empty help text entries:")
                lines.extend(f"  - {name}" for name in empty_text)
            raise CommandError("\n".join(lines))

        self.stdout.write(self.style.SUCCESS("Help text registry looks good."))
