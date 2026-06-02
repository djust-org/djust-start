"""Regression tests for the two-player tic-tac-toe seat model.

These pin the behaviour that makes the demo correct *and* un-stickable — the two
bugs the feature was built to fix:

  * "both windows are X"     → seats are bonded to the per-connection presence id,
                               so two tabs/windows are distinct players.
  * "both seats taken forever"→ seats free themselves on Leave, on disconnect
                               (handle_presence_leave), and via the crash reaper.

Identity = the presence id djust assigns per connection (``anon_conn_<ws-sid>``),
exposed by ``TicTacToeView._me()``. The reaper reads ``self.list_presences()``;
we stub it with a controllable ``live`` set so seat-reaping is deterministic.
``push_to_view`` (the real WS fan-out) is monkeypatched to a no-op.
"""

import pytest

from apps.tictactoe import views as ttt_views
from apps.tictactoe.models import Game
from apps.tictactoe.views import TicTacToeView, winner_of


@pytest.fixture(autouse=True)
def _no_broadcast(monkeypatch):
    monkeypatch.setattr(ttt_views, "push_to_view", lambda *a, **k: None)


@pytest.fixture
def live():
    """The live-presence set the seat-reaper sees via list_presences()."""
    return set()


@pytest.fixture
def seat(live, monkeypatch):
    """Factory: a view bonded to presence id `pid`, seen as present in `live`."""

    def _make(pid):
        v = TicTacToeView()
        v._presence_user_id = pid
        # Stub the live-presence read the reaper uses (monkeypatch, not direct
        # method assignment, so mypy stays happy).
        monkeypatch.setattr(v, "list_presences", lambda: [{"id": x} for x in live])
        live.add(pid)
        return v

    return _make


def _game(**fields):
    g = Game.shared()
    for k, v in fields.items():
        setattr(g, k, v)
    if fields:
        g.save()
    return g


def test_winner_detection():
    assert winner_of("XO.XO.X..") == "X"  # left column
    assert winner_of("XOXXOOOXX") == "draw"
    assert winner_of(".........") == ""


@pytest.mark.django_db
def test_spectator_by_default(seat):
    v = seat("anon_conn_A")
    # mount/derivation never auto-claims; you watch until you click a seat.
    assert Game.shared().seat_of(v._me()) == ""


@pytest.mark.django_db
def test_explicit_claim_x_then_o(seat):
    a, b = seat("anon_conn_A"), seat("anon_conn_B")
    a.take_seat(seat="X")
    b.take_seat(seat="O")
    assert a.mark == "X" and b.mark == "O"
    g = Game.shared()
    assert g.player_x == "anon_conn_A" and g.player_o == "anon_conn_B"


@pytest.mark.django_db
def test_spectator_cannot_take_a_taken_seat(seat):
    a, c = seat("anon_conn_A"), seat("anon_conn_C")
    a.take_seat(seat="X")
    c.take_seat(seat="X")
    assert c.mark == ""
    assert Game.shared().player_x == "anon_conn_A"


@pytest.mark.django_db
def test_no_seat_swapping(seat):
    a, b = seat("anon_conn_A"), seat("anon_conn_B")
    a.take_seat(seat="X")
    b.take_seat(seat="O")
    a.take_seat(seat="O")  # already holds X — must not swap
    assert a.mark == "X"
    assert Game.shared().player_o == "anon_conn_B"


@pytest.mark.django_db
def test_turn_enforcement_and_spectator_cannot_play(seat):
    a, b, c = seat("anon_conn_A"), seat("anon_conn_B"), seat("anon_conn_C")
    a.take_seat(seat="X")
    b.take_seat(seat="O")
    a.play(cell=0)
    assert Game.shared().board == "X........" and Game.shared().turn == "O"
    a.play(cell=1)  # X again, but it's O's turn
    assert Game.shared().board == "X........", "X moved out of turn"
    c.play(cell=1)  # spectator
    assert Game.shared().board == "X........", "spectator moved"
    b.play(cell="1")  # O's turn, string arg coerced
    assert Game.shared().board[1] == "O" and Game.shared().turn == "X"


@pytest.mark.django_db
def test_leave_seat_frees_it_for_someone_else(seat):
    a, b, c = seat("anon_conn_A"), seat("anon_conn_B"), seat("anon_conn_C")
    a.take_seat(seat="X")
    b.take_seat(seat="O")
    b.leave_seat()
    assert b.mark == "" and Game.shared().player_o == ""
    c.take_seat(seat="O")
    assert c.mark == "O" and Game.shared().player_o == "anon_conn_C"


@pytest.mark.django_db
def test_disconnect_auto_frees_seat(seat):
    a, b = seat("anon_conn_A"), seat("anon_conn_B")
    a.take_seat(seat="X")
    b.take_seat(seat="O")
    a.handle_presence_leave({"id": "anon_conn_A"})  # X's WebSocket drops
    assert Game.shared().player_x == ""


@pytest.mark.django_db
def test_claim_race_exactly_one_winner(seat):
    r1, r2 = seat("anon_conn_R1"), seat("anon_conn_R2")
    r1.take_seat(seat="X")
    r2.take_seat(seat="X")  # same instant, same open seat
    marks = [r1.mark, r2.mark]
    assert marks.count("X") == 1 and marks.count("") == 1


@pytest.mark.django_db
def test_reaper_frees_a_dead_holders_seat(seat):
    _game(player_x="anon_conn_DEAD", player_o="")  # DEAD never added to `live`
    fresh = seat("anon_conn_FRESH")
    fresh.take_seat(seat="X")  # reaper clears DEAD, then FRESH claims the open seat
    assert fresh.mark == "X" and Game.shared().player_x == "anon_conn_FRESH"


@pytest.mark.django_db
def test_release_does_not_clobber_a_non_holder(seat):
    _game(player_x="anon_conn_A", player_o="")
    b = seat("anon_conn_B")
    b.handle_presence_leave({"id": "anon_conn_B"})  # B holds nothing
    assert Game.shared().player_x == "anon_conn_A", (
        "must not free a seat B doesn't hold"
    )


@pytest.mark.django_db
def test_take_seat_is_noop_before_websocket():
    v = TicTacToeView()  # no _presence_user_id — HTTP first paint
    v.take_seat(seat="O")
    assert Game.shared().player_o == ""


@pytest.mark.django_db
def test_take_seat_refused_while_game_finished(seat):
    _game(player_x="anon_conn_A", player_o="", winner="X")
    c = seat("anon_conn_C")
    c.take_seat(seat="O")  # can't join a finished game; "New game" must run first
    assert Game.shared().player_o == ""


@pytest.mark.django_db
def test_reset_keeps_seats(seat):
    _game(player_x="anon_conn_A", player_o="anon_conn_B", board="XOXOX....", turn="O")
    seat("anon_conn_A").reset()
    g = Game.shared()
    assert g.board == "." * 9 and g.turn == "X" and g.winner == ""
    assert g.player_x == "anon_conn_A" and g.player_o == "anon_conn_B", (
        "reset is a rematch, not a kick"
    )
