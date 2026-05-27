import logging

from djust import LiveView
from djust.presence import PresenceMixin

logger = logging.getLogger("djust_start.presence")


class BaseLiveView(PresenceMixin, LiveView):
    """Project-wide LiveView base.

    With djust ≥ 1.0.0rc12 (PR #1615), PresenceMixin handles the heavy lifting:
      - track_presence() is auto-skipped during HTTP mount (no orphan entries)
      - track/untrack auto-broadcast to all sessions via _on_presence_change
      - self.online_count is auto-refreshed and exposed to templates
      - presence_unique_per_connection=True makes anonymous tabs count separately

    NOTE: when djust-org/djust#1605 lands, replace the SILENCED_SYSTEM_CHECKS
    entries for djust.V001 and djust.V005 with `abstract = True` on this class.
    """

    login_required = False
    # Anonymous tabs in the same browser share a Django session_key and would
    # otherwise overwrite each other in the presence dict. Opt in to the
    # per-connection user_id so the chip reflects real tab count.
    presence_unique_per_connection = True

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        self._request_path = request.path
        ws_sid = getattr(self, "_websocket_session_id", None)
        flag = getattr(self, "presence_unique_per_connection", "MISSING")
        logger.warning(
            "[presence-diag] MOUNT cls=%s ws_sid=%s unique_flag=%r",
            self.__class__.__name__, ws_sid, flag,
        )
        self.track_presence()
        uid = getattr(self, "_presence_user_id", None)
        try:
            ids = [p.get("id") for p in self.list_presences()]
        except Exception:
            ids = []
        logger.warning(
            "[presence-diag] post-track user_id=%s all_ids=%s online_count=%s",
            uid, ids, getattr(self, "online_count", "<unset>"),
        )
        if not hasattr(self, "online_count"):
            self.online_count = 1

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["request_path"] = self._request_path
        return ctx
