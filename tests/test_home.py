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
class TestHomeView:
    def _mount(self):
        from apps.home.views import HomeView

        rf = RequestFactory()
        req = rf.get("/")
        req.user = AnonymousUser()
        view = HomeView()
        view.mount(req)
        return view

    def test_mount_initializes_count_to_zero(self):
        view = self._mount()
        assert view.count == 0

    def test_increment_increases_count(self):
        view = self._mount()
        view.increment()
        assert view.count == 1

    def test_increment_is_cumulative(self):
        view = self._mount()
        view.increment()
        view.increment()
        view.increment()
        assert view.count == 3

    def test_context_data_includes_count(self):
        view = self._mount()
        view.increment()
        ctx = view.get_context_data()
        assert "count" in ctx
        assert ctx["count"] == 1


@pytest.mark.django_db
def test_home_page_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200
