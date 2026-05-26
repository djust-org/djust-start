from djust import LiveView


class BaseLiveView(LiveView):
    login_required = False

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        self._request_path = request.path

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["request_path"] = self._request_path
        return ctx
