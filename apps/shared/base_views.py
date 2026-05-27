from djust import LiveView
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

    def get_presence_user_id(self) -> str:
        """Authenticated users count as one identity across all their tabs.

        For anonymous viewers, two tabs share a Django session and would
        otherwise overwrite each other in the presence dict (count stays at 1).
        Appending `id(self)` makes each WebSocket connection a distinct
        presence entry — which is what the "N online" chip should reflect.
        """
        request = getattr(self, "request", None)
        if request is not None and getattr(request, "user", None) \
                and request.user.is_authenticated:
            return str(request.user.id)
        return f"anon:{id(self)}"

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        self._request_path = request.path
        # PresenceMixin needs WebSocket channel context. In unit-test mount
        # (RequestFactory) track_presence raises silently — that's fine,
        # get_context_data falls back to 1 below.
        try:
            self.track_presence()
            # Re-render every other open session of this view so their
            # "N online" chip picks up the new presence count.
            push_to_view(
                f"{self.__class__.__module__}.{self.__class__.__name__}",
                state={"_presence_tick": id(self)},
            )
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
