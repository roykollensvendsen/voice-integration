"""Where the person is while they move: direction, speed, and what is on each side."""

import json
import threading
import time
import urllib.request

import pytest
from conftest import TOKEN

from voice_bridge import budget, moving, quick, server, sessions

#: Skuggevik, heading due east at 60 km/h.
DRIVING = moving.Fix(latitude=58.6, longitude=9.0, heading=90.0, speed=60 / 3.6, at=time.time())
STILL = moving.Fix(latitude=58.6, longitude=9.0, heading=None, speed=0.0, at=time.time())


def _thing(name, north_m, east_m, **tags):
    """A named thing this far north and east of DRIVING."""
    lat = DRIVING.latitude + north_m / 111_195
    lon = DRIVING.longitude + east_m / (111_195 * 0.5210)  # cos(58.6°)
    return {"type": "node", "lat": lat, "lon": lon, "tags": {"name": name, **tags}}


@pytest.fixture
def bridge(url, tmp_path, claude_voice):
    running = server.Bridge(
        ("127.0.0.1", 0), url, budget.Ledger(tmp_path / "spend.json"), chosen_file=tmp_path / "target.json"
    )
    running.sessions = sessions.Client(f"http://127.0.0.1:{claude_voice.server_port}/mcp", TOKEN)
    yield running
    running.server_close()


def post(where, payload):
    request = urllib.request.Request(
        where, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=10) as reply:
        return reply.status, json.loads(reply.read())


NEAR = [
    _thing("Skuggevik kirke", 200, 0, amenity="place_of_worship"),  # north: left when going east
    _thing("Holmen", -150, 20, natural="islet"),  # south: right
    _thing("Butikken", 0, 300, amenity="supermarket"),  # east: ahead
]


@pytest.mark.parametrize(
    ("said", "side"),
    [
        ("Hva er det til venstre for oss?", "venstre"),
        ("hva er det vi kjører forbi på høyre side", "høyre"),
        ("Hva er det foran oss nå", "foran"),
        ("what is that on the left", "venstre"),
        ("kjør til venstre", None),
    ],
)
def test_a_question_about_a_side_is_recognised(said, side):
    assert moving.side_asked(said) == side


def test_what_is_on_each_side_is_found_from_the_direction_of_travel():
    assert moving.on_the_side(DRIVING, "venstre", NEAR).startswith(
        "Til venstre: Skuggevik kirke, kirke, omtrent 200 meter"
    )
    assert moving.on_the_side(DRIVING, "høyre", NEAR).startswith("Til høyre: Holmen, holme")
    assert moving.on_the_side(DRIVING, "foran", NEAR).startswith(
        "Foran deg: Butikken, butikk, omtrent 300 meter"
    )
    assert "finner ikke" in moving.on_the_side(DRIVING, "bak", NEAR)


def test_standing_still_there_is_no_left_or_right():
    assert "i bevegelse" in moving.on_the_side(STILL, "venstre", NEAR)


def test_where_you_are_says_the_way_and_the_speed_while_moving():
    assert (
        moving.described(DRIVING, "Skuggevik")
        == "Du er i Skuggevik, på vei øst i omtrent 60 kilometer i timen."
    )
    assert moving.described(STILL, "Skuggevik") == "Du er i Skuggevik."


def test_the_place_is_looked_up_again_only_after_a_real_move(bridge, monkeypatch):
    looked = []
    monkeypatch.setattr(quick, "place_of", lambda lat, _lon: looked.append(lat) or f"Sted {len(looked)}")
    first = bridge.where({"latitude": 58.6, "longitude": 9.0, "heading": 90, "speed": 16})
    again = bridge.where({"latitude": 58.6001, "longitude": 9.0, "heading": 90, "speed": 16})
    moved = bridge.where({"latitude": 58.61, "longitude": 9.0, "heading": 0, "speed": 16})
    assert (first["changed"], again["changed"], moved["changed"]) == (True, False, True)
    assert len(looked) == 2
    assert bridge.fix.heading == 0


def test_hermes_is_told_where_the_person_is_only_when_they_ask_about_it(bridge):
    bridge.fix, bridge.placed = DRIVING, "Skuggevik"
    told = server.whereabouts_for_hermes(bridge, "Hva er det rundt meg her?")
    # Way, speed and the time of the reading: Roy, 2026-10-10.
    assert "Du er i Skuggevik, på vei øst i omtrent 60 kilometer i timen. Målt klokka " in told
    assert server.whereabouts_for_hermes(bridge, "Hvordan går det med testene?") == ""


def test_where_the_person_is_never_reaches_the_trace(bridge):
    bridge.fix, bridge.placed = STILL, "Svennskotveien 23, Skuggevik"
    thread = threading.Thread(target=bridge.serve_forever, daemon=True)
    thread.start()
    try:
        post(f"http://127.0.0.1:{bridge.server_port}/turn", {"who": "You", "text": "Hvor er jeg?"})
    finally:
        bridge.shutdown()
        thread.join(timeout=5)
    (row,) = bridge.store.rows("action")
    assert "Svennskotveien" not in row["detail"]
    assert "(where you are, said)" in row["detail"]
