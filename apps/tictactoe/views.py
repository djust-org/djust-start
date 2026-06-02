import inspect
import logging

from djust import action
from djust.push import push_to_view

from apps.shared.base_views import BaseLiveView

from .models import Game

logger = logging.getLogger(__name__)

VIEW = "apps.tictactoe.views.TicTacToeView"
LINES = [
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),  # rows
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),  # cols
    (0, 4, 8),
    (2, 4, 6),
]  # diagonals


def winner_of(board):
    for a, b, c in LINES:
        if board[a] != "." and board[a] == board[b] == board[c]:
            return board[a]
    return "draw" if "." not in board else ""


class TicTacToeView(BaseLiveView):
    """Two-player tic-tac-toe over WebSocket — no API, no polling, no JS.

    Seats are *claimed explicitly* ("Play as X" / "Play as O") and *bonded to a
    connection*, so the demo can never get permanently stuck:

    * `take_seat` / `leave_seat` — explicit claim and release.
    * `handle_presence_leave` — djust's wired disconnect hook (BaseLiveView
      already tracks presence), so closing a tab frees that seat automatically.
    * `_reap_dead_seats` — a backstop that frees any seat whose holder is no
      longer in the live-presence set (covers hard crashes that never send a
      close frame, capped at the ~60s presence heartbeat).
    """

    template_name = "tictactoe/game.html"
    presence_key = "tictactoe:game"  # shares one board + online count

    def mount(self, request, **kwargs):
        # PresenceMixin.track_presence() runs here on WS mount.
        super().mount(request, **kwargs)
        g = Game.shared()
        # Clear seats whose connection is gone (e.g. after a server restart).
        self._reap_dead_seats(g)
        g = Game.shared()
        # Re-attach to a seat THIS connection already holds, else "" spectator.
        # Assigned via a local (not self.X = method_call) to dodge djust.V008's
        # can't-infer-return-type false positive; seat_of returns "X"/"O"/"".
        mark = g.seat_of(self._me())
        self.mark = mark
        self._sync(g)
        # The claim handler is the teaching source shown on the page.
        self.play_src = inspect.getsource(TicTacToeView.take_seat)

    def _me(self):
        # The presence id djust registered for this connection
        # (``anon_conn_<ws-session-id>``): unique per tab/window, stable across
        # this connection's events, and exactly what the live-presence set and
        # the disconnect hook key on. None on the initial HTTP paint.
        return getattr(self, "_presence_user_id", None)

    # ── shared state (broadcast to everyone) ──────────────────────────────
    def _sync(self, g):
        """Refresh the SHARED board state. `self.mark` is per-session (each
        session derives its own seat) and is intentionally NOT part of this."""
        self.cells = [
            {"i": i, "mark": ("" if ch == "." else ch)} for i, ch in enumerate(g.board)
        ]
        self.turn = g.turn
        self.winner = g.winner
        self.x_taken = bool(g.player_x)
        self.o_taken = bool(g.player_o)
        self.seats_full = bool(g.player_x and g.player_o)

    def _broadcast(self, g):
        self._sync(g)
        push_to_view(
            VIEW,
            state={
                "cells": self.cells,
                "turn": self.turn,
                "winner": self.winner,
                "x_taken": self.x_taken,
                "o_taken": self.o_taken,
                "seats_full": self.seats_full,
            },
        )

    # ── seat lifecycle ────────────────────────────────────────────────────
    def _free(self, g, who):
        """Release whichever seat `who` holds. Keyed on the exact holder, so we
        never clobber a seat already re-taken by someone else."""
        if not who:
            return
        Game.objects.filter(pk=1, player_x=who).update(player_x="")
        Game.objects.filter(pk=1, player_o=who).update(player_o="")

    def _reap_dead_seats(self, g):
        """Backstop for hard crashes that never deliver a disconnect frame:
        free any seat whose holder is no longer in the live-presence set."""
        try:
            live = {p["id"] for p in self.list_presences()}
        except Exception:  # presence backend hiccup must never break the page
            return
        if g.player_x and g.player_x not in live:
            Game.objects.filter(pk=1, player_x=g.player_x).update(player_x="")
        if g.player_o and g.player_o not in live:
            Game.objects.filter(pk=1, player_o=g.player_o).update(player_o="")

    @action
    def take_seat(self, seat="", **kwargs):
        if seat not in ("X", "O"):
            return  # guard the wire input
        me = self._me()
        if not me:
            return  # a seat is leased to a live WebSocket connection only
        g = Game.shared()
        self._reap_dead_seats(g)
        g = Game.shared()
        if g.winner:  # don't join a finished game; click "New game" first
            self._broadcast(g)
            return
        if g.seat_of(me):  # already seated — no seat-swapping
            self._broadcast(g)
            return
        field = "player_x" if seat == "X" else "player_o"
        # Atomic claim-if-open: the WHERE clause IS the check, applied with the
        # write in one statement, so two simultaneous claims can't both win.
        #   1 row updated → we got the seat;  0 rows → someone beat us.
        won = Game.objects.filter(pk=1, **{field: ""}).update(**{field: me})
        g = Game.shared()
        self.mark = seat if won else g.seat_of(me)
        self._broadcast(g)

    @action
    def leave_seat(self, **kwargs):
        g = Game.shared()
        self._free(g, self._me())
        self.mark = ""  # this session is now a spectator
        self._broadcast(Game.shared())

    def handle_presence_leave(self, presence):
        """djust's wired disconnect hook — fires on THIS connection's view
        instance when its WebSocket drops (consumer.disconnect →
        untrack_presence → here). Free this connection's seat and tell everyone
        else it opened up. Wrapped defensively: disconnect swallows exceptions,
        so a raise here would silently skip the broadcast."""
        who = (presence or {}).get("id") or self._me()
        try:
            g = Game.shared()
            self._free(g, who)
            self._broadcast(Game.shared())
        except Exception:
            logger.warning("tictactoe: seat-release on disconnect failed for %s", who)

    # ── gameplay ──────────────────────────────────────────────────────────
    @action
    def play(self, cell: int = -1, **kwargs):
        try:
            cell = int(cell)
        except (TypeError, ValueError):
            return
        g = Game.shared()
        # READ-only seat lookup — spectators stay spectators (no auto-claim).
        self.mark = mark = g.seat_of(self._me())
        if not mark or g.winner or g.turn != mark:
            self._broadcast(g)
            return  # spectator, game over, or not your turn
        board = list(g.board)
        if not (0 <= cell <= 8) or board[cell] != ".":
            self._broadcast(g)
            return
        board[cell] = mark
        g.board = "".join(board)
        g.winner = winner_of(g.board)
        g.turn = "O" if mark == "X" else "X"
        g.save()
        self._broadcast(g)

    @action
    def reset(self, **kwargs):
        g = Game.shared()
        g.board = "." * 9
        g.turn = "X"
        g.winner = ""
        g.save()  # board only — keep player_x / player_o (same two players, rematch)
        self.mark = g.seat_of(self._me())
        self._broadcast(g)
