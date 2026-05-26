def theme_cookies(request):
    """
    Inject djust-theming cookie values as plain strings into template context.

    The Rust template engine cannot traverse HttpRequest — this processor
    extracts the 4 theme cookies upfront so theming_handlers.py can read
    them from context after Rust serialization.
    """
    return {
        "_djust_theme_preset": request.COOKIES.get("djust_theme_preset", ""),
        "_djust_theme_pack": request.COOKIES.get("djust_theme_pack", ""),
        "_djust_theme": request.COOKIES.get("djust_theme", ""),
        "_djust_theme_mode": request.COOKIES.get("djust_theme_mode", ""),
    }
