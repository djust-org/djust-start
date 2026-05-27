import logging
import random

from djust import LiveView
from djust.presence import PresenceMixin
from djust.push import push_to_view

logger = logging.getLogger("djust_start.presence")


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

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        self._request_path = request.path
        self._anon_user_id = f"anon_{random.randint(10_000_000, 99_999_999)}"
        is_ws = hasattr(self, "_websocket_session_id")

        logger.warning(
            "[presence] MOUNT view=%s user=%s is_ws=%s",
            self.__class__.__name__, self._anon_user_id, is_ws,
        )

        # Only track presence in the WebSocket mount — HTTP mount creates
        # a throwaway view instance just for initial render.
        if is_ws:
            try:
                self.track_presence()
                count = len(self.list_presences())
                logger.warning(
                    "[presence] TRACKED user=%s count_now=%d",
                    self._anon_user_id, count,
                )
                push_to_view(
                    f"{self.__class__.__module__}.{self.__class__.__name__}",
                    state={"_presence_tick": self._anon_user_id},
                )
            except Exception as e:
                logger.exception("[presence] TRACK FAILED: %s", e)

    def untrack_presence(self):
        """Override to log the disconnect path."""
        logger.warning(
            "[presence] UNTRACK called user=%s tracked=%s",
            getattr(self, "_presence_user_id", None),
            getattr(self, "_presence_tracked", None),
        )
        super().untrack_presence()
        try:
            count = len(self.list_presences())
            logger.warning("[presence] UNTRACK done count_now=%d", count)
        except Exception:
            pass

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["request_path"] = self._request_path
        try:
            ctx["online_count"] = len(self.list_presences()) or 1
        except Exception:
            ctx["online_count"] = 1
        return ctx
