from app.cooldown import CooldownManager


def test_allows_trigger_for_new_plate():
    cd = CooldownManager(cooldown_seconds=60, clock=lambda: 1000.0)
    assert cd.should_trigger("A123BC777") is True


def test_suppresses_repeat_trigger_within_window():
    now = {"t": 1000.0}
    cd = CooldownManager(cooldown_seconds=60, clock=lambda: now["t"])
    assert cd.should_trigger("A123BC777") is True
    now["t"] += 10  # 10s later, still within 60s window
    assert cd.should_trigger("A123BC777") is False


def test_allows_trigger_again_after_window_elapses():
    now = {"t": 1000.0}
    cd = CooldownManager(cooldown_seconds=60, clock=lambda: now["t"])
    assert cd.should_trigger("A123BC777") is True
    now["t"] += 61  # past the 60s window
    assert cd.should_trigger("A123BC777") is True


def test_tracks_plates_independently():
    now = {"t": 1000.0}
    cd = CooldownManager(cooldown_seconds=60, clock=lambda: now["t"])
    assert cd.should_trigger("A123BC777") is True
    assert cd.should_trigger("K777XA777") is True
