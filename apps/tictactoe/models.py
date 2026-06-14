from django.db import models
from djust.db import notify_on_save


@notify_on_save
class Game(models.Model):
    """The single shared tic-tac-toe board + its two seated players.

    One row (pk=1). `player_x` / `player_o` hold the *presence id* of whoever
    claimed each seat (the string ``anon_conn_<ws-session-id>`` djust assigns
    per WebSocket connection). Storing the presence id — not the raw session id
    — means the seat can be matched to the live-presence set by plain string
    equality, so a seat frees itself the moment its connection drops (see
    `handle_presence_leave` / `_reap_dead_seats` in views.py). `""` means open.
    `board` is 9 chars of '.', 'X', 'O'.
    """

    board = models.CharField(max_length=9, default="." * 9)
    turn = models.CharField(max_length=1, default="X")
    winner = models.CharField(max_length=4, default="")  # "", "X", "O", "draw"
    player_x = models.CharField(max_length=64, default="")  # presence id holding X
    player_o = models.CharField(max_length=64, default="")  # presence id holding O

    @classmethod
    def shared(cls):
        return cls.objects.get_or_create(pk=1)[0]

    def seat_of(self, who):
        """Return 'X', 'O', or '' for the seat this presence id holds."""
        if who and self.player_x == who:
            return "X"
        if who and self.player_o == who:
            return "O"
        return ""

    def __str__(self):
        return f"Game(board={self.board!r}, turn={self.turn}, winner={self.winner!r})"
