import os
import secrets

os.environ.setdefault("DJANGO_SECRET_KEY", secrets.token_urlsafe(64))
os.environ.setdefault("USE_SQLITE", "1")
from .settings import *  # noqa: F403,E402

DEBUG = True
TRUST_PROXY = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}
