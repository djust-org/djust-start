from djust import LiveView
from djust.presence import PresenceMixin


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
    # otherwise overwrite each other in the presence dict. Opt in to a
    # per-connection user_id so the chip reflects real tab count.
    presence_unique_per_connection = True

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        self._request_path = request.path
        # rc12: track_presence is a no-op during HTTP mount, sets
        # self.online_count via _refresh_online_count in WS mount, and
        # auto-broadcasts to peer sessions so every open tab's chip refreshes.
        self.track_presence()
        # HTTP prerender fallback. The WS mount will replace this with the
        # real count and the client now morphs the DOM (djust PR #1616).
        if not hasattr(self, "online_count"):
            self.online_count = 1

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["request_path"] = self._request_path
        return ctx
