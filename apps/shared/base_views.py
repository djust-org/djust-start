from djust import LiveView
from djust.presence import PresenceMixin


class BaseLiveView(PresenceMixin, LiveView):
    """Project-wide LiveView base. Adds presence tracking + request path context.

    Subclasses should set `presence_key` to share a presence bucket across
    sessions of the same view (otherwise the chip stays at "1 online").

    NOTE: when djust-org/djust#1605 lands, replace the SILENCED_SYSTEM_CHECKS
    entries for djust.V001 and djust.V005 with `abstract = True` on this class.
    """

    login_required = False

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        self._request_path = request.path
        # PresenceMixin needs WebSocket channel context. In unit-test mount
        # (RequestFactory) it raises silently — that's fine, get_context_data
        # falls back to 1 below.
        try:
            self.track_presence()
        except Exception:
            pass

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["request_path"] = self._request_path
        # Recompute every render so the chip updates when others join / leave.
        try:
            ctx["online_count"] = len(self.list_presences()) or 1
        except Exception:
            ctx["online_count"] = 1
        return ctx
