from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'change-me-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

USE_POSTGIS = os.environ.get('USE_POSTGIS', '').lower() in {'1', 'true', 'yes'}

WINDOWS_GDAL_PATH = Path(r"C:\\Users\\LENOVO\\AppData\\Local\\Programs\\OSGeo4W\\bin\\gdal311.dll")
if WINDOWS_GDAL_PATH.exists():
    GDAL_LIBRARY_PATH = str(WINDOWS_GDAL_PATH)

WINDOWS_GEOS_PATH = Path(r"C:\\Users\\LENOVO\\AppData\\Local\\Programs\\OSGeo4W\\bin\\geos_c.dll")
if WINDOWS_GEOS_PATH.exists():
    GEOS_LIBRARY_PATH = str(WINDOWS_GEOS_PATH)

WINDOWS_GDAL_DATA = Path(r"C:\\Users\\LENOVO\\AppData\\Local\\Programs\\OSGeo4W\\share\\gdal")
if WINDOWS_GDAL_DATA.exists():
    os.environ.setdefault("GDAL_DATA", str(WINDOWS_GDAL_DATA))

WINDOWS_PROJ_LIB = Path(r"C:\\Users\\LENOVO\\AppData\\Local\\Programs\\OSGeo4W\\share\\proj")
if WINDOWS_PROJ_LIB.exists():
    os.environ.setdefault("PROJ_LIB", str(WINDOWS_PROJ_LIB))

INSTALLED_APPS = [
    'grms.admin_config.GRMSAdminConfig',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'grms',
]

if USE_POSTGIS:
    INSTALLED_APPS.insert(6, 'django.contrib.gis')

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
        'DIRS': [],
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
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': os.environ.get('SQLITE_NAME', str(BASE_DIR / 'db.sqlite3')),
        }
    }

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

# Use cookie-based sessions so the admin can function even when the
# database-backed session table has not been created yet.  This keeps the
# project self-contained when running the lightweight SQLite setup.
SESSION_ENGINE = os.environ.get(
    'SESSION_ENGINE', 'django.contrib.sessions.backends.signed_cookies'
)
