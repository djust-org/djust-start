from django.urls import path

from .views import TicTacToeView

app_name = "tictactoe"

urlpatterns = [
    path("tictactoe/", TicTacToeView.as_view(), name="game"),
]
