import os
from pathlib import Path
from datetime import timedelta
from django.core.exceptions import ImproperlyConfigured
import dj_database_url
BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', '')
if not SECRET_KEY:
    if DEBUG: SECRET_KEY = 'development-only-kalaa-kerala-do-not-use-in-production'
    else: raise ImproperlyConfigured('Set a random SECRET_KEY before starting production.')
ALLOWED_HOSTS = [s.strip() for s in os.getenv('ALLOWED_HOSTS','localhost,127.0.0.1').split(',') if s.strip()]
RENDER_HOST = os.getenv('RENDER_EXTERNAL_HOSTNAME', '')
if RENDER_HOST:
    ALLOWED_HOSTS.append(RENDER_HOST)
SITE_URL = os.getenv('SITE_URL',f'https://{RENDER_HOST}' if RENDER_HOST else 'http://localhost:8000').rstrip('/')
CSRF_TRUSTED_ORIGINS = [s.strip() for s in os.getenv('CSRF_TRUSTED_ORIGINS',SITE_URL).split(',') if s.strip()]
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME','clubadmin')
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','axes','club']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','whitenoise.middleware.WhiteNoiseMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware','axes.middleware.AxesMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages','club.context.site_context']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default':dj_database_url.config(default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',conn_max_age=60)}
if RENDER_HOST:
    if DEBUG or DATABASES['default']['ENGINE'] != 'django.db.backends.postgresql':
        raise ImproperlyConfigured('Render requires DEBUG=false and a PostgreSQL DATABASE_URL.')
    if not os.getenv('AWS_STORAGE_BUCKET_NAME'):
        raise ImproperlyConfigured('Render requires persistent S3-compatible photo storage.')
AUTHENTICATION_BACKENDS = ['axes.backends.AxesStandaloneBackend','django.contrib.auth.backends.ModelBackend']
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=30)
AXES_LOCKOUT_PARAMETERS = ['username','ip_address']
AUTH_PASSWORD_VALIDATORS = [{'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},{'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},{'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},{'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'}]
LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR/'staticfiles'
STATICFILES_DIRS = [BASE_DIR/'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = Path(os.getenv('MEDIA_ROOT',str(BASE_DIR/'media')))
STORAGES = {'default':{'BACKEND':'django.core.files.storage.FileSystemStorage'},'staticfiles':{'BACKEND':'whitenoise.storage.CompressedManifestStaticFilesStorage'}}
if os.getenv('AWS_STORAGE_BUCKET_NAME'):
    STORAGES['default'] = {'BACKEND':'storages.backends.s3.S3Storage','OPTIONS':{'bucket_name':os.environ['AWS_STORAGE_BUCKET_NAME'],'access_key':os.environ['AWS_ACCESS_KEY_ID'],'secret_key':os.environ['AWS_SECRET_ACCESS_KEY'],'endpoint_url':os.getenv('AWS_S3_ENDPOINT_URL') or None,'region_name':os.getenv('AWS_S3_REGION_NAME','eu-west-2'),'default_acl':None,'querystring_auth':True,'file_overwrite':False}}
    STORAGES['default']['OPTIONS'].update(signature_version='s3v4', addressing_style='path')
FILE_UPLOAD_MAX_MEMORY_SIZE = 2*1024*1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 25*1024*1024
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_AGE = 3600*8
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
if os.getenv('TRUST_PROXY_HTTPS','false').lower()=='true':
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO','https')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY','')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET','')
if os.getenv('REVIEW_MODE','false').lower() == 'true' and STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith('sk_test_'):
    raise ImproperlyConfigured('REVIEW_MODE requires a Stripe test secret key.')
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND','django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST','')
EMAIL_PORT = int(os.getenv('EMAIL_PORT','587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER','')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD','')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL','noreply@localhost')
EMAIL_TIMEOUT = 10
LOGGING = {'version':1,'disable_existing_loggers':False,'handlers':{'console':{'class':'logging.StreamHandler'}},'root':{'handlers':['console'],'level':'INFO'}}
