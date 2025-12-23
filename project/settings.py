from pathlib import Path
import os
import warnings

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-in-production')
DEBUG = os.environ.get('DEBUG', 'true').lower() in ('1', 'true', 'yes')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
USE_POSTGIS = os.environ.get('USE_POSTGIS', 'true').lower() in ('1', 'true', 'yes')
ALLOW_SPATIAL_FALLBACK = os.environ.get('ALLOW_SPATIAL_FALLBACK', 'false').lower() in ('1', 'true', 'yes')

# -----------------------
# Windows GDAL + GEOS paths (REAL OSGeo4W path)
# -----------------------
# -----------------------
# Windows GDAL + GEOS paths (OSGeo4W)
# -----------------------
GDAL_LIBRARY_PATH = os.environ.get("GDAL_LIBRARY_PATH")
GEOS_LIBRARY_PATH = os.environ.get("GEOS_LIBRARY_PATH")

if os.name == "nt":
    GDAL_LIBRARY_PATH = GDAL_LIBRARY_PATH or r"C:\OSGeo4W\bin\gdal312.dll"
    GEOS_LIBRARY_PATH = GEOS_LIBRARY_PATH or r"C:\OSGeo4W\bin\geos_c.dll"
    os.environ.setdefault("GDAL_DATA", r"C:\OSGeo4W\share\gdal")
    os.environ.setdefault("PROJ_LIB", r"C:\OSGeo4W\share\proj")


INSTALLED_APPS = [
    'django.contrib.humanize',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'traffic',
    'grms',
    # Custom admin site needs to load after dependent apps (including `traffic`)
    # so that imports in `grms.admin` can locate all models during app registry
    # initialization.
    'grms.admin_config.GRMSAdminConfig',
]

if USE_POSTGIS:
    def _spatial_libs_available() -> bool:
        try:
            from django.contrib.gis.gdal import libgdal  # noqa: F401
            from django.contrib.gis.geos import geos_version  # noqa: F401

            return True
        except Exception as exc:  # pragma: no cover - environment dependent
            if ALLOW_SPATIAL_FALLBACK:
                warnings.warn(
                    "USE_POSTGIS was requested but spatial libraries could not be loaded; "
                    "falling back to non-GIS configuration."
                )
                warnings.warn(str(exc))
                return False
            raise RuntimeError(
                "USE_POSTGIS is enabled but required spatial libraries could not be loaded. "
                "Install GDAL/GEOS system packages or set ALLOW_SPATIAL_FALLBACK=true to run without GIS."
            ) from exc

    if _spatial_libs_available():
        INSTALLED_APPS.insert(6, 'django.contrib.gis')
    else:
        USE_POSTGIS = False

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'project.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Load the custom admin templates (grouped dashboard and base site)
        # before falling back to app templates.
        'DIRS': [BASE_DIR / 'grms' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'

if USE_POSTGIS:
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
            'NAME': os.environ.get('POSTGRES_DB', 'grms'),
            'USER': os.environ.get('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'Mniece@01-25'),
            'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
            'PORT': os.environ.get('POSTGRES_PORT', '5432'),
            'TEST': {
                'NAME': os.environ.get('POSTGRES_TEST_DB', os.environ.get('POSTGRES_DB', 'grms_test')),
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.environ.get('SQLITE_NAME', str(BASE_DIR / 'db.sqlite3')),
        }
    }

    class DisableMigrations(dict):
        def __contains__(self, item):  # pragma: no cover - test helper
            return True

        def __getitem__(self, item):  # pragma: no cover - test helper
            return None

    MIGRATION_MODULES = DisableMigrations()

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ]
}

CORS_ALLOW_ALL_ORIGINS = True
STATIC_ROOT = BASE_DIR / "staticfiles"

LEAFLET_CONFIG = {
    'DEFAULT_CENTER': [13.5, 39.5],
    'DEFAULT_ZOOM': 8,
}

# Use cookie-based sessions so the admin can function even when the
# database-backed session table has not been created yet.  This keeps the
# project self-contained when running the lightweight SQLite setup.
SESSION_ENGINE = os.environ.get(
    'SESSION_ENGINE', 'django.contrib.sessions.backends.signed_cookies'
)
