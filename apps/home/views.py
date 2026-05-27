from djust import action
from djust.push import push_to_view

from apps.shared.base_views import BaseLiveView

from .models import GuestbookMessage, PollVote, ReactionCount

EMOJIS = ["🔥", "❤️", "🚀", "👏", "💯", "😍"]
POLL_OPTIONS = ["Forms", "Components", "Realtime", "Auth"]


class HomeView(BaseLiveView):
    template_name = "home/home.html"

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        self.emojis = EMOJIS
        self.poll_options = POLL_OPTIONS
        self._rebuild_reactions()
        self._rebuild_poll()
        self._rebuild_messages()

    # ─── state helpers ────────────────────────────────────────────────────

    def _rebuild_reactions(self):
        counts = dict(ReactionCount.objects.values_list("emoji", "count"))
        self.reactions = [{"emoji": e, "count": counts.get(e, 0)} for e in EMOJIS]

    def _rebuild_poll(self):
        counts = dict(PollVote.objects.values_list("option", "count"))
        total = sum(counts.values())
        self.poll_data = [
            {
                "option": opt,
                "count": counts.get(opt, 0),
                "pct": (counts.get(opt, 0) / total * 100) if total > 0 else 0,
            }
            for opt in POLL_OPTIONS
        ]

    def _rebuild_messages(self):
        rows = GuestbookMessage.objects.order_by("-created_at")[:5].values(
            "text", "created_at"
        )
        self.messages = [
            {"text": r["text"], "created_at": r["created_at"].isoformat()}
            for r in rows
        ]
