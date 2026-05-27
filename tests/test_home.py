import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory


@pytest.mark.django_db
def test_base_live_view_mount_sets_request_path():
    from apps.shared.base_views import BaseLiveView

    rf = RequestFactory()
    req = rf.get("/some/path/")
    req.user = AnonymousUser()
    view = BaseLiveView()
    view.mount(req)
    assert view._request_path == "/some/path/"


@pytest.mark.django_db
def test_base_live_view_context_exposes_request_path():
    from apps.shared.base_views import BaseLiveView

    rf = RequestFactory()
    req = rf.get("/hello/")
    req.user = AnonymousUser()
    view = BaseLiveView()
    view.mount(req)
    ctx = view.get_context_data()
    assert ctx["request_path"] == "/hello/"


def test_theme_cookies_returns_empty_strings_when_no_cookies():
    from apps.shared.context_processors import theme_cookies

    class FakeRequest:
        COOKIES = {}

    result = theme_cookies(FakeRequest())
    assert result == {
        "_djust_theme_preset": "",
        "_djust_theme_pack": "",
        "_djust_theme": "",
        "_djust_theme_mode": "",
    }


def test_theme_cookies_extracts_cookie_values():
    from apps.shared.context_processors import theme_cookies

    class FakeRequest:
        COOKIES = {
            "djust_theme_preset": "nord",
            "djust_theme_pack": "bootstrap5",
            "djust_theme": "dark",
            "djust_theme_mode": "dark",
        }

    result = theme_cookies(FakeRequest())
    assert result["_djust_theme_preset"] == "nord"
    assert result["_djust_theme_pack"] == "bootstrap5"
    assert result["_djust_theme"] == "dark"
    assert result["_djust_theme_mode"] == "dark"


@pytest.mark.django_db
class TestHomeViewRebuildHelpers:
    """Test the data-shaping helpers directly, without going through @action."""

    def _mount(self):
        from apps.home.views import HomeView

        rf = RequestFactory()
        req = rf.get("/")
        req.user = AnonymousUser()
        view = HomeView()
        view.mount(req)
        return view

    def test_mount_initializes_reactions_in_canonical_order(self):
        from apps.home.views import EMOJIS

        view = self._mount()
        assert [r["emoji"] for r in view.reactions] == EMOJIS
        assert all(r["count"] == 0 for r in view.reactions)

    def test_mount_initializes_poll_in_canonical_order(self):
        from apps.home.views import POLL_OPTIONS

        view = self._mount()
        assert [r["option"] for r in view.poll_data] == POLL_OPTIONS
        assert all(r["count"] == 0 for r in view.poll_data)
        assert all(r["pct"] == 0 for r in view.poll_data)

    def test_mount_initializes_messages_as_empty_list(self):
        view = self._mount()
        assert view.messages == []

    def test_rebuild_reactions_reflects_db_counts(self):
        from apps.home.models import ReactionCount

        ReactionCount.objects.create(emoji="🔥", count=5)
        view = self._mount()
        fire = next(r for r in view.reactions if r["emoji"] == "🔥")
        assert fire["count"] == 5

    def test_rebuild_poll_computes_percentages(self):
        from apps.home.models import PollVote

        PollVote.objects.create(option="Forms", count=3)
        PollVote.objects.create(option="Components", count=1)
        view = self._mount()
        forms = next(r for r in view.poll_data if r["option"] == "Forms")
        components = next(r for r in view.poll_data if r["option"] == "Components")
        realtime = next(r for r in view.poll_data if r["option"] == "Realtime")
        assert forms["count"] == 3
        assert forms["pct"] == 75.0
        assert components["pct"] == 25.0
        assert realtime["pct"] == 0

    def test_rebuild_messages_limits_to_five_newest_first(self):
        from apps.home.models import GuestbookMessage

        for i in range(7):
            GuestbookMessage.objects.create(text=f"msg {i}")
        view = self._mount()
        assert len(view.messages) == 5
        assert view.messages[0]["text"] == "msg 6"
        assert view.messages[4]["text"] == "msg 2"

    def test_context_data_exposes_demo_state(self):
        view = self._mount()
        ctx = view.get_context_data()
        assert ctx["reactions"] == view.reactions
        assert ctx["poll_data"] == view.poll_data
        assert ctx["messages"] == view.messages
        assert ctx["online_count"] == view.online_count


@pytest.mark.django_db
def test_home_page_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_reactioncount_starts_at_zero_when_created():
    from apps.home.models import ReactionCount

    row, created = ReactionCount.objects.get_or_create(emoji="🔥")
    assert created is True
    assert row.count == 0


@pytest.mark.django_db
def test_pollvote_starts_at_zero_when_created():
    from apps.home.models import PollVote

    row, created = PollVote.objects.get_or_create(option="Forms")
    assert created is True
    assert row.count == 0


@pytest.mark.django_db
def test_guestbookmessage_stores_text_and_timestamps():
    from apps.home.models import GuestbookMessage

    msg = GuestbookMessage.objects.create(text="hello")
    assert msg.text == "hello"
    assert msg.created_at is not None


@pytest.mark.django_db
def test_base_live_view_sets_online_count_after_mount():
    """online_count is always at least 1 — the viewer themselves count."""
    from apps.shared.base_views import BaseLiveView

    rf = RequestFactory()
    req = rf.get("/some/path/")
    req.user = AnonymousUser()
    view = BaseLiveView()
    view.mount(req)
    assert hasattr(view, "online_count")
    assert view.online_count >= 1
