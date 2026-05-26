from django.apps import AppConfig


class SharedConfig(AppConfig):
    name = "apps.shared"
    label = "shared"

    def ready(self):
        try:
            from . import theming_handlers  # noqa: F401  registers @register handlers
        except ImportError:
            pass
