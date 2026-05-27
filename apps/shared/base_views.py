import logging
import random

from djust import LiveView
from djust.decorators import event_handler
from djust.presence import PresenceMixin
from djust.push import push_to_view

logger = logging.getLogger("djust_start.presence")


class BaseLiveView(PresenceMixin, LiveView):
    """Project-wide LiveView base. Adds presence tracking + request path context."""

    login_required = False

    def get_presence_user_id(self):
        request = getattr(self, "request", None)
        if request is not None and getattr(request, "user", None) \
                and request.user.is_authenticated:
            return str(request.user.id)
        return self._anon_user_id

    @event_handler
    def _on_presence_change(self, **kwargs):
        try:
            count = len(self.list_presences())
            logger.warning("[presence] _on_presence_change received count=%d", count)
        except Exception as e:
            logger.warning("[presence] _on_presence_change list_presences failed: %s", e)

    def _broadcast_presence_change(self):
        try:
            count = len(self.list_presences())
            logger.warning("[presence] broadcasting (count from sender perspective=%d)", count)
            push_to_view(
                f"{self.__class__.__module__}.{self.__class__.__name__}",
                handler="_on_presence_change",
                payload={},
            )
        except Exception as e:
            logger.warning("[presence] broadcast failed: %s", e)

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        self._request_path = request.path
        self._anon_user_id = f"anon_{random.randint(10_000_000, 99_999_999)}"
        is_ws = hasattr(self, "_websocket_session_id")
        logger.warning(
            "[presence] MOUNT user=%s is_ws=%s",
            self._anon_user_id, is_ws,
        )

        if is_ws:
            try:
                self.track_presence()
                count = len(self.list_presences())
                logger.warning(
                    "[presence] TRACKED user=%s count_after_track=%d _presence_tracked=%s",
                    self._anon_user_id, count, self._presence_tracked,
                )
            except Exception as e:
                logger.exception("[presence] TRACK FAILED: %s", e)
            self._broadcast_presence_change()

    def untrack_presence(self):
        super().untrack_presence()
        self._broadcast_presence_change()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["request_path"] = self._request_path
        try:
            online = len(self.list_presences())
            ctx["online_count"] = online or 1
            logger.warning(
                "[presence] get_context_data online_count=%d (raw=%d)",
                ctx["online_count"], online,
            )
        except Exception as e:
            logger.warning("[presence] list_presences in get_context_data failed: %s", e)
            ctx["online_count"] = 1
        return ctx
