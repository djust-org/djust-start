"""
Rust tag handlers for djust-theming template tags.

Registers {% theme_head %} and {% theme_panel %} with the djust Rust template
engine. The Rust engine strips HttpRequest from context before passing it to
tag handlers. apps.shared.context_processors.theme_cookies injects the cookie
values as plain strings; this module reads them back to build a _MockRequest
for ThemeManager.
"""

import logging
from typing import Any, Dict, List

from djust.template_tags import TagHandler, register

logger = logging.getLogger(__name__)


class _MockCookies:
    def __init__(self, data: dict):
        self._data = data

    def get(self, key, default=None):
        return self._data.get(key, default)


class _MockSession(dict):
    pass


class _MockRequest:
    def __init__(self, cookies: dict):
        self.COOKIES = _MockCookies(cookies)
        self.session = _MockSession()


def _make_mock_request(context: Dict[str, Any]) -> "_MockRequest":
    return _MockRequest(
        {
            "djust_theme_preset": context.get("_djust_theme_preset", ""),
            "djust_theme_pack": context.get("_djust_theme_pack", ""),
            "djust_theme": context.get("_djust_theme", ""),
            "djust_theme_mode": context.get("_djust_theme_mode", ""),
        }
    )


def _format_kwarg(key: str, value: str) -> str:
    if value in ("true", "True"):
        return " %s=True" % key
    if value in ("false", "False"):
        return " %s=False" % key
    if value.isdigit():
        return " %s=%s" % (key, value)
    return ' %s="%s"' % (key, value)


def _render_theme_tag(tag_str: str, context: Dict[str, Any]) -> str:
    from django.template import Context, Template

    tpl = "{% load theme_tags %}" + tag_str
    try:
        mock_request = _make_mock_request(context)
        return Template(tpl).render(Context({"request": mock_request}, autoescape=True))
    except Exception:
        logger.exception("Error rendering theme tag: %s", tag_str)
        return "<!-- theme tag render failed -->"


@register("theme_head")
class ThemeHeadHandler(TagHandler):
    def render(self, args: List[str], context: Dict[str, Any]) -> str:
        kwargs_str = ""
        for arg in args:
            resolved = self._resolve_arg(arg, context)
            if isinstance(resolved, tuple):
                kwargs_str += _format_kwarg(resolved[0], resolved[1])
        return _render_theme_tag("{%% theme_head%s %%}" % kwargs_str, context)


@register("theme_panel")
class ThemePanelHandler(TagHandler):
    def render(self, args: List[str], context: Dict[str, Any]) -> str:
        kwargs_str = ""
        for arg in args:
            resolved = self._resolve_arg(arg, context)
            if isinstance(resolved, tuple):
                kwargs_str += _format_kwarg(resolved[0], resolved[1])
        return _render_theme_tag("{%% theme_panel%s %%}" % kwargs_str, context)
