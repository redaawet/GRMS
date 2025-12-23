import os
import pytest

# Default environment for PostGIS-backed test runs
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
os.environ.setdefault("USE_POSTGIS", "true")
os.environ.setdefault("ALLOW_SPATIAL_FALLBACK", "false")
os.environ.setdefault("POSTGRES_DB", os.environ.get("POSTGRES_DB", "grms_test"))
os.environ.setdefault("POSTGRES_TEST_DB", os.environ.get("POSTGRES_TEST_DB", "grms_test"))
os.environ.setdefault("POSTGRES_USER", os.environ.get("POSTGRES_USER", "postgres"))
os.environ.setdefault("POSTGRES_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "postgres"))
os.environ.setdefault("POSTGRES_HOST", os.environ.get("POSTGRES_HOST", "localhost"))
os.environ.setdefault("POSTGRES_PORT", os.environ.get("POSTGRES_PORT", "5432"))


@pytest.fixture(scope="session", autouse=True)
def enforce_postgis_engine():
    from django.conf import settings

    engine = settings.DATABASES.get("default", {}).get("ENGINE", "")
    if "postgis" not in engine:
        raise RuntimeError(
            "Tests must run against the PostGIS backend. Check environment variables and spatial dependencies."
        )
