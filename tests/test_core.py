from __future__ import annotations

from pathlib import Path

from continuum_core.core import PersistentCore
from continuum_core.reflection import offline_reflection
from continuum_core.storage import Store


class SequenceClock:
    def __init__(self, values: list[str]):
        self.values = iter(values)

    def __call__(self) -> str:
        return next(self.values)


def test_core_persists_ticks_and_elapsed_time(tmp_path: Path) -> None:
    store = Store(tmp_path / "continuum.db")
    clock = SequenceClock(
        [
            "2026-09-17T12:00:00+00:00",
            "2026-09-17T12:00:01+00:00",
            "2026-09-17T12:00:04+00:00",
        ]
    )
    core = PersistentCore(store, clock=clock)
    core.initialize()

    first = core.tick()
    second = core.tick()

    assert first["tick_count"] == 1
    assert first["seconds_since_previous_tick"] is None
    assert second["tick_count"] == 2
    assert second["seconds_since_previous_tick"] == 3.0

    reopened = Store(tmp_path / "continuum.db")
    assert reopened.get_state("tick_count") == 2
    assert reopened.current_self_model()["working_name"] == "Continuum"


def test_events_and_offline_reflection_are_auditable(tmp_path: Path) -> None:
    store = Store(tmp_path / "continuum.db")
    core = PersistentCore(store)
    core.initialize()
    core.tick()
    store.add_event("autobiographical", "A controlled test occurred.")

    reflection = offline_reflection(store)

    assert "A controlled test occurred." in reflection
    assert "recorded 1 ticks" in reflection
    snapshot = store.snapshot()
    assert snapshot["events"][-1]["source"] == "human"

