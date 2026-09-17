from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable

from .storage import Store, utc_now


DEFAULT_SELF_MODEL = {
    "working_name": "Continuum",
    "kind": "experimental persistent cognitive scaffold",
    "version": 1,
    "known_capabilities": [
        "maintain durable state",
        "record elapsed time",
        "store human-supplied autobiographical events",
        "request bounded language-model reflection",
    ],
    "known_limitations": [
        "no evidence of phenomenal consciousness",
        "no independent sensory stream",
        "no autonomous external actions",
        "no access to a language model's hidden activations or weights",
        "no authority to alter governing boundaries",
    ],
    "relationships": {
        "Lucas": "founder, operator, and research participant",
    },
    "governing_purpose": (
        "Support controlled, falsifiable research into functional self-modeling "
        "while remaining transparent, reversible, and human-governed."
    ),
}


class PersistentCore:
    def __init__(self, store: Store, clock: Callable[[], str] = utc_now):
        self.store = store
        self.clock = clock

    def initialize(self) -> None:
        self.store.initialize()
        if self.store.get_state("created_at") is None:
            now = self.clock()
            self.store.set_state("created_at", now)
            self.store.set_state("last_tick_at", None)
            self.store.set_state("tick_count", 0)
            self.store.set_state("seconds_since_previous_tick", None)
            self.store.set_state("unresolved_questions", [])
            self.store.add_self_model(
                DEFAULT_SELF_MODEL,
                author="project",
                reason="Initial inspectable self-model",
            )
            self.store.add_event(
                "system",
                "Persistent core initialized under the 30-day experimental charter.",
                source="system",
            )

    def tick(self) -> dict[str, object]:
        self.initialize()
        now_text = self.clock()
        previous_text = self.store.get_state("last_tick_at")
        elapsed = None
        if previous_text:
            now = datetime.fromisoformat(now_text)
            previous = datetime.fromisoformat(previous_text)
            elapsed = max(0.0, (now - previous).total_seconds())

        count = int(self.store.get_state("tick_count", 0)) + 1
        self.store.set_state("last_tick_at", now_text)
        self.store.set_state("tick_count", count)
        self.store.set_state("seconds_since_previous_tick", elapsed)
        return {
            "tick_count": count,
            "last_tick_at": now_text,
            "seconds_since_previous_tick": elapsed,
        }

    def run(self, interval: float, max_ticks: int | None = None) -> None:
        completed = 0
        while max_ticks is None or completed < max_ticks:
            state = self.tick()
            completed += 1
            print(
                f"tick={state['tick_count']} at={state['last_tick_at']} "
                f"elapsed={state['seconds_since_previous_tick']}"
            )
            if max_ticks is None or completed < max_ticks:
                time.sleep(interval)

