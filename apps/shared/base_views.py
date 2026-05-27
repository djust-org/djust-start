import logging

from djust import LiveView
from djust.presence import PresenceMixin

logger = logging.getLogger("djust_start.presence")


class BaseLiveView(PresenceMixin, LiveView):
    """Project-wide LiveView base.

    djust ≥ 1.0.0rc12 makes presence zero-config:
      - track_presence() no-ops during HTTP mount (no orphan entries)
      - track/untrack auto-broadcast so peer sessions refresh their chip
      - self.online_count is auto-set; templates use {{ online_count|default:1 }}
      - presence_unique_per_connection=True gives anonymous tabs distinct user_ids
      - abstract = True opts this base out of V001/V005 mount-readiness checks
    """

    abstract = True
    login_required = False  # acknowledge public access (silences djust.S005)
    presence_unique_per_connection = True

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        ws_sid = getattr(self, "_websocket_session_id", "ABSENT")
        self.track_presence()
        uid = getattr(self, "_presence_user_id", None)
        tracked = getattr(self, "_presence_tracked", None)
        try:
            ids = [p.get("id") for p in self.list_presences()]
        except Exception as e:
            ids = f"ERR: {e}"
        logger.warning(
            "[diag] MOUNT ws_sid=%s uid=%s tracked=%s online_count=%s all_ids=%s",
            ws_sid, uid, tracked,
            getattr(self, "online_count", "<unset>"), ids,
        )

    def untrack_presence(self):
        uid = getattr(self, "_presence_user_id", None)
        logger.warning("[diag] UNTRACK uid=%s", uid)
        super().untrack_presence()
        try:
            ids = [p.get("id") for p in self.list_presences()]
        except Exception:
            ids = []
        logger.warning(
            "[diag] UNTRACK done online_count=%s all_ids=%s",
            getattr(self, "online_count", "<unset>"), ids,
        )
