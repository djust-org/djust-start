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


@pytest.mark.django_db
class TestHomeViewActions:
    def _mount(self):
        from apps.home.views import HomeView

        rf = RequestFactory()
        req = rf.get("/")
        req.user = AnonymousUser()
        view = HomeView()
        view.mount(req)
        return view

    # ─── react ────────────────────────────────────────────────────────────

    def test_react_increments_db_count_and_state(self):
        from apps.home.models import ReactionCount

        view = self._mount()
        view.react(emoji="🔥")
        assert ReactionCount.objects.get(emoji="🔥").count == 1
        fire = next(r for r in view.reactions if r["emoji"] == "🔥")
        assert fire["count"] == 1

    def test_react_is_cumulative(self):
        view = self._mount()
        view.react(emoji="❤️")
        view.react(emoji="❤️")
        view.react(emoji="❤️")
        heart = next(r for r in view.reactions if r["emoji"] == "❤️")
        assert heart["count"] == 3

    def test_react_ignores_invalid_emoji(self):
        from apps.home.models import ReactionCount

        view = self._mount()
        view.react(emoji="💣")  # not in EMOJIS
        assert ReactionCount.objects.filter(emoji="💣").count() == 0

    # ─── vote ─────────────────────────────────────────────────────────────

    def test_vote_increments_db_count_and_state(self):
        from apps.home.models import PollVote

        view = self._mount()
        view.vote(option="Forms")
        assert PollVote.objects.get(option="Forms").count == 1
        forms = next(r for r in view.poll_data if r["option"] == "Forms")
        assert forms["count"] == 1
        assert forms["pct"] == 100.0

    def test_vote_ignores_invalid_option(self):
        from apps.home.models import PollVote

        view = self._mount()
        view.vote(option="Nonsense")
        assert PollVote.objects.filter(option="Nonsense").count() == 0

    def test_vote_recomputes_pct_across_options(self):
        view = self._mount()
        view.vote(option="Forms")
        view.vote(option="Forms")
        view.vote(option="Forms")
        view.vote(option="Auth")
        forms = next(r for r in view.poll_data if r["option"] == "Forms")
        auth = next(r for r in view.poll_data if r["option"] == "Auth")
        assert forms["pct"] == 75.0
        assert auth["pct"] == 25.0

    # ─── post_message ────────────────────────────────────────────────────

    def test_post_message_saves_and_appears_in_state(self):
        from apps.home.models import GuestbookMessage

        view = self._mount()
        view.post_message(text="hello world")
        assert GuestbookMessage.objects.filter(text="hello world").exists()
        assert view.messages[0]["text"] == "hello world"

    def test_post_message_ignores_empty_text(self):
        from apps.home.models import GuestbookMessage

        view = self._mount()
        view.post_message(text="")
        view.post_message(text="   ")
        view.post_message(text=None)
        assert GuestbookMessage.objects.count() == 0
        assert view.messages == []

    def test_post_message_trims_to_280_chars(self):
        from apps.home.models import GuestbookMessage

        view = self._mount()
        view.post_message(text="x" * 500)
        saved = GuestbookMessage.objects.get()
        assert len(saved.text) == 280

    def test_post_message_keeps_only_five_newest_in_state(self):
        view = self._mount()
        for i in range(7):
            view.post_message(text=f"msg {i}")
        assert len(view.messages) == 5
        assert view.messages[0]["text"] == "msg 6"


@pytest.mark.django_db
def test_base_template_renders_sync_banner(client):
    response = client.get("/")
    content = response.content.decode()
    assert "Open this page in another window" in content


@pytest.mark.django_db
def test_base_template_renders_presence_chip(client):
    response = client.get("/")
    content = response.content.decode()
    assert "online" in content
    assert 'class="presence-chip"' in content


@pytest.mark.django_db
def test_home_page_renders_hero_reactions(client):
    response = client.get("/")
    content = response.content.decode()
    # Every emoji button is rendered
    for emoji in ["🔥", "❤️", "🚀", "👏", "💯", "😍"]:
        assert emoji in content
    assert 'class="reactions"' in content


@pytest.mark.django_db
def test_home_page_renders_poll(client):
    response = client.get("/")
    content = response.content.decode()
    for option in ["Forms", "Components", "Realtime", "Auth"]:
        assert option in content
    assert "Live poll" in content


@pytest.mark.django_db
def test_home_page_renders_guestbook(client):
    response = client.get("/")
    content = response.content.decode()
    assert "Live guestbook" in content
    assert "Say hi" in content


@pytest.mark.django_db
def test_home_page_includes_dj_view_binding(client):
    response = client.get("/")
    content = response.content.decode()
    assert 'dj-view="apps.home.views.HomeView"' in content
