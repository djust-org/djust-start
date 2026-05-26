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
