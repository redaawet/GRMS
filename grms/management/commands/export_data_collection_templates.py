from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import models
from openpyxl import Workbook

EXCLUDED_FIELD_NAMES = {
    "id",
    "created",
    "created_at",
    "created_on",
    "modified",
    "updated",
    "updated_at",
    "updated_on",
}


class Command(BaseCommand):
    help = "Export offline data collection templates as CSV or XLSX."

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default="./offline_templates",
            help="Output directory for template files (default: ./offline_templates).",
        )
        parser.add_argument(
            "--format",
            choices=("csv", "xlsx"),
            default="csv",
            help="Output format: csv (one file per model) or xlsx (one workbook).",
        )
        parser.add_argument(
            "--apps",
            nargs="*",
            default=["grms", "traffic"],
            help="App labels to include (default: grms traffic).",
        )
        parser.add_argument(
            "--models",
            nargs="*",
            default=None,
            help="Optional model whitelist (e.g. grms.Road traffic.TrafficSurvey).",
        )
        parser.add_argument(
            "--include",
            default=None,
            help="Regex to include model names (matches app_label.ModelName or ModelName).",
        )
        parser.add_argument(
            "--exclude",
            default=None,
            help="Regex to exclude model names (matches app_label.ModelName or ModelName).",
        )

    def handle(self, *args, **options):
        out_dir = Path(options["out"]).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)

        selected_models = self._select_models(options)
        if not selected_models:
            raise CommandError("No models matched the provided filters.")

        columns_by_model = {
            model: self._model_columns(model) for model in selected_models
        }

        if options["format"] == "csv":
            self._write_csv_templates(out_dir, selected_models, columns_by_model)
        else:
            self._write_xlsx_templates(out_dir, selected_models, columns_by_model)

        self._write_import_order(out_dir, selected_models, options["format"])

        self.stdout.write(self.style.SUCCESS("Template export complete."))

    def _select_models(self, options) -> list[type[models.Model]]:
        app_labels = {label.lower() for label in options["apps"] or []}
        include_re = re.compile(options["include"], re.IGNORECASE) if options["include"] else None
        exclude_re = re.compile(options["exclude"], re.IGNORECASE) if options["exclude"] else None
        model_whitelist = self._normalize_model_list(options["models"])

        models_list: list[type[models.Model]] = []
        for model in apps.get_models():
            app_label = model._meta.app_label
            if app_labels and app_label.lower() not in app_labels:
                continue

            model_id = f"{app_label}.{model.__name__}"
            model_id_lower = model_id.lower()
            if model_whitelist and model_id_lower not in model_whitelist:
                continue

            if include_re and not (
                include_re.search(model.__name__) or include_re.search(model_id)
            ):
                continue
            if exclude_re and (
                exclude_re.search(model.__name__) or exclude_re.search(model_id)
            ):
                continue

            models_list.append(model)

        models_list.sort(key=lambda model: (model._meta.app_label, model.__name__))
        return models_list

    def _normalize_model_list(self, models_option: list[str] | None) -> set[str]:
        if not models_option:
            return set()
        normalized: set[str] = set()
        for entry in models_option:
            for token in entry.split(","):
                token = token.strip()
                if not token:
                    continue
                normalized.add(token.lower())
        return normalized

    def _model_columns(self, model: type[models.Model]) -> list[str]:
        natural_key_field = self._natural_key_field(model)
        fk_columns: list[str] = []
        other_columns: list[str] = []

        for field in model._meta.get_fields():
            if not getattr(field, "concrete", False):
                continue
            if field.many_to_many:
                continue
            if field.is_relation:
                if field.many_to_one or field.one_to_one:
                    fk_columns.append(self._fk_column_name(field))
                continue

            if self._exclude_field(field):
                continue

            if natural_key_field and field.name == natural_key_field:
                continue
            other_columns.append(field.name)

        columns: list[str] = []
        if natural_key_field:
            columns.append(natural_key_field)
        columns.extend(fk_columns)
        columns.extend(other_columns)
        return columns

    def _exclude_field(self, field: models.Field) -> bool:
        if field.primary_key or field.auto_created:
            return True
        if field.name in EXCLUDED_FIELD_NAMES:
            return True
        if getattr(field, "auto_now", False) or getattr(field, "auto_now_add", False):
            return True
        return False

    def _natural_key_field(self, model: type[models.Model]) -> str | None:
        candidates = [
            field
            for field in model._meta.get_fields()
            if getattr(field, "concrete", False)
            and not field.is_relation
            and not field.primary_key
            and not field.auto_created
            and field.name not in EXCLUDED_FIELD_NAMES
        ]

        for predicate in (
            lambda name: name.endswith("_identifier"),
            lambda name: "identifier" in name,
            lambda name: "code" in name,
            lambda name: name == "name" or name.endswith("_name"),
        ):
            for field in candidates:
                if predicate(field.name.lower()):
                    return field.name
        return None

    def _fk_column_name(self, field: models.Field) -> str:
        related_model = getattr(field, "related_model", None)
        natural_key_field = self._natural_key_field(related_model) if related_model else None
        if not natural_key_field:
            natural_key_field = "id"
        return f"{field.name}__{natural_key_field}"

    def _write_csv_templates(
        self,
        out_dir: Path,
        models_list: Iterable[type[models.Model]],
        columns_by_model: dict[type[models.Model], list[str]],
    ) -> None:
        for model in models_list:
            filename = self._csv_filename(model)
            path = out_dir / filename
            columns = columns_by_model[model]
            with path.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(columns)

    def _write_xlsx_templates(
        self,
        out_dir: Path,
        models_list: Iterable[type[models.Model]],
        columns_by_model: dict[type[models.Model], list[str]],
    ) -> None:
        workbook = Workbook()
        workbook.remove(workbook.active)

        for model in models_list:
            sheet_name = self._sheet_name(model)
            sheet = workbook.create_sheet(title=sheet_name)
            sheet.append(columns_by_model[model])

        path = out_dir / "data_collection_templates.xlsx"
        workbook.save(path)

    def _write_import_order(
        self,
        out_dir: Path,
        models_list: Iterable[type[models.Model]],
        output_format: str,
    ) -> None:
        ordered = self._topological_order(models_list)
        lines = [
            "Import order (topological sort by FK dependencies among exported models):",
        ]
        for index, model in enumerate(ordered, start=1):
            dependencies = self._model_fk_dependencies(model, set(ordered))
            dependency_names = ", ".join(sorted(dep.__name__ for dep in dependencies)) if dependencies else "None"
            if output_format == "csv":
                location = self._csv_filename(model)
            else:
                location = f"Sheet: {self._sheet_name(model)}"
            lines.append(
                f"{index}. {model._meta.app_label}.{model.__name__} ({location}) - depends on: {dependency_names}"
            )

        lines.append("")
        lines.append("Notes:")
        lines.append("- Import roads, then sections, then segments before dependent models.")
        lines.append("- Foreign keys use natural key columns where available.")

        (out_dir / "IMPORT_ORDER.txt").write_text("\n".join(lines), encoding="utf-8")

    def _model_fk_dependencies(
        self, model: type[models.Model], model_set: set[type[models.Model]]
    ) -> set[type[models.Model]]:
        dependencies: set[type[models.Model]] = set()
        for field in model._meta.get_fields():
            if not getattr(field, "is_relation", False):
                continue
            if not (getattr(field, "many_to_one", False) or getattr(field, "one_to_one", False)):
                continue
            related = getattr(field, "related_model", None)
            if related in model_set and related is not model:
                dependencies.add(related)
        return dependencies

    def _topological_order(
        self, models_list: Iterable[type[models.Model]]
    ) -> list[type[models.Model]]:
        models_list = list(models_list)
        model_set = set(models_list)
        order_hint = {model: index for index, model in enumerate(models_list)}
        dependencies = {model: set() for model in models_list}
        dependents: dict[type[models.Model], set[type[models.Model]]] = defaultdict(set)

        for model in models_list:
            deps = self._model_fk_dependencies(model, model_set)
            dependencies[model] = set(deps)
            for dep in deps:
                dependents[dep].add(model)

        ready = [model for model in models_list if not dependencies[model]]
        ordered: list[type[models.Model]] = []

        while ready:
            ready.sort(key=lambda item: order_hint[item])
            model = ready.pop(0)
            ordered.append(model)
            for dependent in sorted(dependents.get(model, set()), key=lambda item: order_hint[item]):
                dependencies[dependent].discard(model)
                if not dependencies[dependent]:
                    if dependent not in ready and dependent not in ordered:
                        ready.append(dependent)

        remaining = [model for model in models_list if model not in ordered]
        if remaining:
            ordered.extend(sorted(remaining, key=lambda item: order_hint[item]))

        return ordered

    def _csv_filename(self, model: type[models.Model]) -> str:
        return f"{model._meta.app_label}_{model.__name__}.csv"

    def _sheet_name(self, model: type[models.Model]) -> str:
        name = f"{model._meta.app_label}.{model.__name__}"
        return name[:31]
