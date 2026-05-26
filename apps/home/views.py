from djust import action

from apps.shared.base_views import BaseLiveView


class HomeView(BaseLiveView):
    template_name = "home/home.html"

    def mount(self, request, **kwargs):
        super().mount(request, **kwargs)
        self.count = 0

    @action
    def increment(self, **kwargs):
        self.count += 1
