from .base import *  # noqa: F401, F403

DEBUG = True

# State channel layer — in-process, no Redis needed in dev.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}
