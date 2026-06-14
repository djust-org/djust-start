from django.urls import include, path

urlpatterns = [
    path("", include("apps.home.urls")),
    path("", include("apps.tictactoe.urls")),
]
