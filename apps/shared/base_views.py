import random

from djust import LiveView
from djust.decorators import event_handler
from djust.presence import PresenceMixin
from djust.push import push_to_view


class BaseLiveView(PresenceMixin, LiveView):
    """Project-wide LiveView base. Adds presence tracking + request path context.

    Subclasses should set `presence_key` to share a presence bucket across
    sessions of the same view (otherwise the chip stays at "1 online").

    NOTE: when djust-org/djust#1605 lands, replace the SILENCED_SYSTEM_CHECKS
    entries for djust.V001 and djust.V005 with `abstract = True` on this class.
    """

    login_required = False

    def get_presence_user_id(self):
        """Authenticated users count as one identity across their tabs.

        Anonymous viewers get a stable per-instance id so two tabs in the
        same browser session register as two distinct presences (instead
        of overwriting each other under the shared session key).
        """
        request = getattr(self, "request", None)
        if request is not None and getattr(request, "user", None) \
                and request.user.is_authenticated:
            return str(request.user.id)
        return self._anon_user_id

    @event_handler
    def _on_presence_change(self, **kwargs):
        """Receive a broadcast that someone joined or left.

        The empty body is intentional — the act of handling this event
        triggers a re-render, and get_context_data recomputes online_count
        from list_presences(). No state mutation needed here.
        """

    def _broadcast_presence_change(self):
        """Tell every open session to re-render so chips reflect the new count."""
        try:
            push_to_view(
                f"{self.__class__.__module__}.{self.__class__.__name__}",
                handler="_on_presence_change",
                payload={},
            )
        except Exception:
            pass

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        self._request_path = request.path
        self._anon_user_id = f"anon_{random.randint(10_000_000, 99_999_999)}"

        # Only track presence in the WebSocket mount — HTTP mount creates
        # a throwaway view instance just for initial render.
        if hasattr(self, "_websocket_session_id"):
            try:
                self.track_presence()
            except Exception:
                pass
            self._broadcast_presence_change()

    def untrack_presence(self):
        super().untrack_presence()
        self._broadcast_presence_change()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["request_path"] = self._request_path
        try:
            ctx["online_count"] = len(self.list_presences()) or 1
        except Exception:
            ctx["online_count"] = 1
        return ctx
