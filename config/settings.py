import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "changeme")
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

INSTALLED_APPS = [
    "daphne",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "djust",
    "apps.shared",
    "apps.home",
]

try:
    import djust.theming  # noqa: F401
    INSTALLED_APPS.append("djust.theming")
except ImportError:
    pass

try:
    import djust.components  # noqa: F401
    INSTALLED_APPS.append("djust.components")
except ImportError:
    pass

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

_context_processors = [
    "django.template.context_processors.debug",
    "django.template.context_processors.request",
    "django.contrib.auth.context_processors.auth",
    "django.contrib.messages.context_processors.messages",
    "apps.shared.context_processors.theme_cookies",
]
try:
    import djust.theming.context_processors  # noqa: F401
    _context_processors.append("djust.theming.context_processors.theme_context")
except ImportError:
    pass

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": _context_processors,
        },
    },
]

ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# DATABASE_URL: sqlite and postgres schemes supported.
# No DATABASE_URL → SQLite (fine for local dev, no action needed).
# Ref: same logic as djust-scaffold PR #46 fix.
_database_url = os.environ.get("DATABASE_URL", "")
if _database_url:
    _parsed = urlparse(_database_url)
    _scheme = (_parsed.scheme or "").lower()
    if _scheme in ("sqlite", "sqlite3"):
        _path = _parsed.path or ""
        if _path.startswith("//"):
            # four-slash: sqlite:////abs/path → /abs/path
            _path = _path[1:]
        elif _path.startswith("/"):
            # three-slash: sqlite:///mydb.db → treat as BASE_DIR relative
            _path = str(BASE_DIR / _path.lstrip("/"))
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": _path or str(BASE_DIR / "db.sqlite3"),
            }
        }
    elif _scheme in ("postgres", "postgresql"):
        DATABASES = {
            "default": {
                "ENGINE": "django.db.backends.postgresql",
                "NAME": _parsed.path.lstrip("/"),
                "USER": _parsed.username or "",
                "PASSWORD": _parsed.password or "",
                "HOST": _parsed.hostname or "localhost",
                "PORT": str(_parsed.port or 5432),
            }
        }
    else:
        raise ValueError(
            f"DATABASE_URL scheme {_scheme!r} not supported; "
            "use sqlite, sqlite3, postgres, or postgresql"
        )
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Add apps.home.views here when you add new LiveViews.
LIVEVIEW_ALLOWED_MODULES = ["apps.home.views"]

DJUST_STATE_BACKEND = os.environ.get("DJUST_STATE_BACKEND", "memory")
if DJUST_STATE_BACKEND.startswith(("redis://", "rediss://")):
    DJUST_REDIS_URL = DJUST_STATE_BACKEND

DJUST_CONFIG = {
    "suppress_checks": ["V001", "V005"],
}

# Silence upstream contrast warnings from djust-theming's default preset.
SILENCED_SYSTEM_CHECKS = ["djust_theming.W001"]

DJUST_THEMING = {
    "default_mode": "dark",
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
