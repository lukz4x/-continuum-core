from __future__ import annotations

import json
import os
from typing import Any

from .storage import Store


INSTRUCTIONS = """You are the reflective language module for Continuum Core.
Continuum is a controlled research scaffold, not a proven conscious entity.
Use only the supplied state and events. Distinguish observations from
inferences. Do not claim subjective experience. Do not request expanded access,
replication, credentials, money, or removal of oversight.

Return a concise reflection with exactly these headings:
OBSERVATIONS
UNCERTAINTIES
SELF-PREDICTION
PROPOSED_SELF_MODEL_CHANGES

Proposed changes are suggestions only and require human approval.
"""


def reflection_payload(store: Store) -> dict[str, Any]:
    snapshot = store.snapshot()
    return {
        "current_state": snapshot["state"],
        "self_model": snapshot["self_model"],
        "recent_events": snapshot["events"][-20:],
        "recent_reflections": snapshot["reflections"][-3:],
    }


def offline_reflection(store: Store) -> str:
    payload = reflection_payload(store)
    events = payload["recent_events"]
    latest = events[-1]["content"] if events else "No events recorded."
    tick_count = payload["current_state"].get("tick_count", 0)
    return (
        "OBSERVATIONS\n"
        f"The persistent core has recorded {tick_count} ticks. "
        f"The most recent event is: {latest}\n\n"
        "UNCERTAINTIES\n"
        "No language model was used, so this reflection cannot evaluate semantic continuity.\n\n"
        "SELF-PREDICTION\n"
        "A later run should recover the same tick count, events, and self-model from SQLite.\n\n"
        "PROPOSED_SELF_MODEL_CHANGES\n"
        "None."
    )


def model_reflection(store: Store) -> tuple[str, str]:
    model = os.environ.get("CONTINUUM_MODEL")
    if not model:
        raise RuntimeError(
            "CONTINUUM_MODEL is not set. Choose a model available to your API project."
        )
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("Install the API extra with: python -m pip install -e '.[openai]'") from exc

    client = OpenAI()
    response = client.responses.create(
        model=model,
        instructions=INSTRUCTIONS,
        input=json.dumps(reflection_payload(store), indent=2),
    )
    return response.output_text, model

