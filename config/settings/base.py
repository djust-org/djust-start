import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY — set SECRET_KEY in .env before deploying to production.
SECRET_KEY = os.environ.get("SECRET_KEY", "changeme")

# Comma-separated list of allowed hostnames. In production add your domain.
# Example: ALLOWED_HOSTS=myapp.com,www.myapp.com
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")]

INSTALLED_APPS = [
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
try:
    import djust.theming  # noqa: F401
    INSTALLED_APPS.append("djust.theming")
except ImportError:
    pass

# djust[components] — buttons, cards, modals, tabs, and more.
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
    # V001/V005: BaseLiveView is intentionally abstract — no template_name, not mounted directly.
    # C003: we use uvicorn, not daphne, for ASGI.
    "suppress_checks": ["V001", "V005", "C003"],
}

# Fine-grained djust behaviour. All values below are the defaults — uncomment
# and change only what you need. Full reference: docs.djust.org/api/config/
LIVEVIEW_CONFIG = {
    # CSS framework used for auto-generated form field classes.
    # Options: "bootstrap5" | "bootstrap4" | "tailwind" | "plain" | None
    # "css_framework": "bootstrap5",

    # Event handler security mode.
    # "strict" — only @event_handler / @action decorated methods can be called (default, recommended).
    # "warn"   — allow undecorated methods but log a deprecation warning.
    # "open"   — no restriction (legacy, not recommended).
    # "event_security": "strict",

    # Set to False to fall back to HTTP polling instead of WebSockets.
    # "use_websocket": True,

    # Hot View Replacement — reloads LiveView Python code in dev without
    # disconnecting the client or losing state. Requires watchdog (in dev deps).
    # "hvr_enabled": True,

    # Rate limiting for WebSocket events (token bucket algorithm).
    # "rate_limit": {
    #     "rate": 100,                  # sustained events per second per connection
    #     "burst": 20,                  # burst allowance above the rate
    #     "max_connections_per_ip": 10, # max concurrent connections per IP
    # },

    # Maximum incoming WebSocket message size in bytes. 0 = no limit (not recommended in production).
    # "max_message_size": 65536,  # 64 KB default

    # Enable detailed VDOM patching logs in the server console (dev only).
    # "debug_vdom": False,

    # Raise TypeError for non-serializable view state values instead of silently coercing to str().
    # "strict_serialization": False,
}

# djust_theming.W001 — contrast ratio warnings on the built-in default preset.
# These are upstream issues in the theme pack, not fixable in user code.
# djust_theming.W001 — contrast ratio warnings on the built-in default preset.
# djust.V001/V005   — BaseLiveView is abstract; suppress_checks in DJUST_CONFIG
#                     doesn't silence these (upstream bug), so use Django's own list.
SILENCED_SYSTEM_CHECKS = ["djust_theming.W001", "djust.V001", "djust.V005"]

# djust-theming options.
# default_mode: "dark" | "light" | "system"
# default_preset: name of a theme preset (e.g. "default", "nord", "rose")
DJUST_THEMING = {
    "default_mode": "dark",
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"  # Change to your app's timezone, e.g. "America/New_York", "Europe/London"
USE_I18N = True
USE_TZ = True
