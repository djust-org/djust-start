from .base import *  # noqa: F401, F403

DEBUG = True

# Permissive in dev — DEBUG=True already excludes this settings module from
# production. Lets you hit the server via 0.0.0.0, ngrok tunnels, LAN IP, etc.
ALLOWED_HOSTS = ["*"]

# State channel layer — in-process, no Redis needed in dev.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}
