from djust import LiveView
from djust.presence import PresenceMixin


class BaseLiveView(PresenceMixin, LiveView):
    """Project-wide LiveView base. Adds presence tracking + request path context.

    NOTE: when djust-org/djust#1605 lands, replace the SILENCED_SYSTEM_CHECKS
    entries for djust.V001 and djust.V005 with `abstract = True` on this class.
    """

    login_required = False

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        self._request_path = request.path
        # PresenceMixin needs WebSocket channel context. In unit-test mount
        # (RequestFactory) it may raise or no-op; either way the viewer counts
        # as 1, so we floor at 1.
        try:
            self.track_presence()
            self.online_count = len(self.list_presences()) or 1
        except Exception:
            self.online_count = 1

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["request_path"] = self._request_path
        return ctx
