import os
import sys
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', True)

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

MODEL_URL = os.getenv('MODEL_URL')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'auth_',
    'api',
    'lms',
    'redis',
    'nltk',
]


MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

CORS_ALLOW_CREDENTIALS = True


CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
]


ROOT_URLCONF = 'instrumate.urls'

AUTH_USER_MODEL = 'auth_.CustomUser'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'auth_.authentication.CookieJWTAuthentication',
    ),
}


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'instrumate.wsgi.application'

DATABASE_ROUTERS = ['routers.MovementRouter']

if 'test' in sys.argv:
    default_db = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
else:
    default_db = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('PSQL_DB_NAME'),
        'USER': os.getenv('PSQL_DB_USER'),
        'PASSWORD': os.getenv('PSQL_DB_PASSWORD'),
        'HOST': os.getenv('PSQL_DB_HOST', os.getenv('DOCKER_DB_SERVICE_NAME', 'localhost')),
        'PORT': os.getenv('PSQL_DB_PORT', 5432)
    }

DATABASES = {
    'default': default_db,
    'movement_files': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.getenv('SQLITE_DB_NAME'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
