import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY — set SECRET_KEY in .env before deploying to production.
SECRET_KEY = os.environ.get("SECRET_KEY", "changeme")

# Set DEBUG=False in production. Never commit True to a public repo.
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")

# Comma-separated list of allowed hostnames. In production add your domain.
# Example: ALLOWED_HOSTS=myapp.com,www.myapp.com
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

INSTALLED_APPS = [
    "daphne",                          # ASGI server (required for WebSockets)
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "djust",                           # Core LiveView framework
    "apps.shared",                     # BaseLiveView, context processors, theming handlers
    "apps.home",                       # Home page — your first LiveView
]

# djust[theming] — 60+ theme packs, dark/light mode, CSS variable system.
# Installed automatically when djust[theming] extra is present.
try:
    import djust.theming  # noqa: F401
    INSTALLED_APPS.append("djust.theming")
except ImportError:
    pass

# djust[components] — buttons, cards, modals, tabs, and more.
# Installed automatically when djust[components] extra is present.
try:
    import djust.components  # noqa: F401
    INSTALLED_APPS.append("djust.components")
except ImportError:
    pass

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # Static file serving (compression + caching)
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
    # Extracts theme cookies to plain strings — required because the Rust
    # template renderer cannot serialise HttpRequest objects directly.
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

# State channel layer. InMemoryChannelLayer is fine for single-process dev.
# Switch to RedisChannelLayer in production (see DJUST_STATE_BACKEND below).
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# DATABASE_URL — unset defaults to SQLite (fine for local dev, no action needed).
# Supported schemes:
#   sqlite:///db.sqlite3          → BASE_DIR-relative SQLite file
#   sqlite:////abs/path/db.sqlite → absolute path SQLite
#   postgres://user:pass@host/db  → PostgreSQL
#   postgresql://user:pass@host/db
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

# Register every module that contains LiveView subclasses you want mountable
# over WebSockets. Unregistered views will silently fail to connect.
# Example: LIVEVIEW_ALLOWED_MODULES = ["apps.home.views", "apps.dashboard.views"]
LIVEVIEW_ALLOWED_MODULES = ["apps.home.views"]

# LiveView state backend.
# "memory"          — in-process, lost on restart. Fine for single-server dev.
# "redis://..."     — Redis. Required for multi-process or multi-server deploys.
# "rediss://..."    — Redis over TLS.
DJUST_STATE_BACKEND = os.environ.get("DJUST_STATE_BACKEND", "memory")
if DJUST_STATE_BACKEND.startswith(("redis://", "rediss://")):
    DJUST_REDIS_URL = DJUST_STATE_BACKEND

DJUST_CONFIG = {
    # V001/V005 fire on BaseLiveView because it has no template_name and is
    # intentionally abstract — not meant to be mounted directly.
    "suppress_checks": ["V001", "V005"],
}

# djust_theming.W001 — contrast ratio warnings on the built-in default preset.
# These are upstream issues in the theme pack, not fixable in user code.
SILENCED_SYSTEM_CHECKS = ["djust_theming.W001"]

# djust-theming options.
# default_mode: "dark" | "light" | "system"
# default_preset: name of a theme preset (e.g. "default", "nord", "rose")
DJUST_THEMING = {
    "default_mode": "dark",
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
