import os
from urllib.parse import urlsplit
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if not DEBUG:
        raise ImproperlyConfigured('Set DJANGO_SECRET_KEY for production. Use DJANGO_DEBUG=true only for local development.')
    SECRET_KEY = 'local-development-only-not-for-hosting-sqlcraft'
ALLOWED_HOSTS = [x.strip() for x in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if x.strip()]
INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'allauth', 'allauth.account', 'allauth.socialaccount',
    'allauth.socialaccount.providers.google', 'practice',
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware', 'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware', 'practice.middleware.SecurityHeadersMiddleware',
]
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request', 'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages', 'practice.context_processors.site_settings',
    ]}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': dj_database_url.parse(os.getenv('DATABASE_URL') or f'sqlite:///{BASE_DIR / "db.sqlite3"}', conn_max_age=0)}
if not DEBUG:
    if not os.getenv('DATABASE_URL') or DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
        raise ImproperlyConfigured('Production requires DATABASE_URL for durable PostgreSQL.')
    if not os.getenv('DJANGO_ALLOWED_HOSTS') or '*' in ALLOWED_HOSTS or not ALLOWED_HOSTS:
        raise ImproperlyConfigured('Set explicit production hostnames; wildcard hosts are not supported.')
    runner_address = urlsplit(os.getenv('SQL_RUNNER_URL', ''))
    if (runner_address.scheme not in ('http', 'https') or not runner_address.hostname
            or runner_address.username or runner_address.password or runner_address.query or runner_address.fragment
            or len(os.getenv('SQL_RUNNER_TOKEN', '')) < 32):
        raise ImproperlyConfigured('Configure SQL_RUNNER_URL and a SQL_RUNNER_TOKEN of at least 32 characters.')
    if bool(os.getenv('GOOGLE_CLIENT_ID')) != bool(os.getenv('GOOGLE_CLIENT_SECRET')):
        raise ImproperlyConfigured('Set both Google OAuth values, or leave both unset.')
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    DATABASES['default']['OPTIONS'] = {'timeout': 20}
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.db.DatabaseCache', 'LOCATION': 'app_cache', 'TIMEOUT': 300}}
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend', 'allauth.account.auth_backends.AuthenticationBackend']
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_PREVENT_ENUMERATION = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 1
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[SQLCraft] '
ACCOUNT_RATE_LIMITS = {'login': '15/m/ip', 'login_failed': '5/5m/key', 'signup': '5/h/ip', 'reset_password': '5/h/ip'}
LOGIN_REDIRECT_URL = '/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
SOCIALACCOUNT_LOGIN_ON_GET = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION = False
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = False
GOOGLE_ENABLED = bool(os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET'))
SOCIALACCOUNT_PROVIDERS = {'google': {'SCOPE': ['profile', 'email'], 'AUTH_PARAMS': {'prompt': 'select_account'}}}
if GOOGLE_ENABLED:
    SOCIALACCOUNT_PROVIDERS['google']['APP'] = {
        'client_id': os.environ['GOOGLE_CLIENT_ID'], 'secret': os.environ['GOOGLE_CLIENT_SECRET'], 'key': '',
    }
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
EMAIL_TIMEOUT = 10
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'SQLCraft <noreply@example.invalid>')
if not DEBUG and EMAIL_BACKEND in {'django.core.mail.backends.console.EmailBackend', 'django.core.mail.backends.locmem.EmailBackend', 'django.core.mail.backends.dummy.EmailBackend', 'django.core.mail.backends.filebased.EmailBackend'}:
    raise ImproperlyConfigured('Use a production email backend, not a development mail sink.')
if not DEBUG and (not EMAIL_HOST or not os.getenv('DEFAULT_FROM_EMAIL')):
    raise ImproperlyConfigured('Configure EMAIL_HOST and DEFAULT_FROM_EMAIL before production startup.')
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}, 'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = 'Lax'
SECURE_SSL_REDIRECT = not DEBUG
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
DATA_UPLOAD_MAX_MEMORY_SIZE = 32768
DATA_UPLOAD_MAX_NUMBER_FIELDS = 20
# Enable only behind a trusted proxy that removes incoming forwarded headers.
if os.getenv('TRUST_PROXY_HTTPS') == 'true':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_FAILURE_VIEW = 'practice.errors.csrf_failure'
