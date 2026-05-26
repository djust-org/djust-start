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
