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

    def _refresh_online_count(self):
        """Recompute online_count from the presence backend.

        Stored on the instance (not just in get_context_data context) so
        djust's render diff picks up the change and patches the chip in
        the DOM. Putting it only in context kept the template render fresh
        but the diff layer never saw a 'changed field' and emitted no patches.
        """
        try:
            self.online_count = len(self.list_presences()) or 1
        except Exception:
            self.online_count = 1

    @event_handler
    def _on_presence_change(self, **kwargs):
        """Re-sync the count when another session joined or left."""
        self._refresh_online_count()

    def _broadcast_presence_change(self):
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
            self._refresh_online_count()
            self._broadcast_presence_change()
        else:
            # HTTP mount runs BEFORE the WebSocket connects, so we're not
            # in the backend yet. Anticipate ourselves with +1 so the
            # HTTP-rendered chip matches what the WS mount will show after
            # track_presence(). If they diverge, djust's has_prerendered
            # optimization keeps the chip stuck at the HTTP value.
            try:
                self.online_count = len(self.list_presences()) + 1
            except Exception:
                self.online_count = 1

    def untrack_presence(self):
        super().untrack_presence()
        self._refresh_online_count()
        self._broadcast_presence_change()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["request_path"] = self._request_path
        return ctx
