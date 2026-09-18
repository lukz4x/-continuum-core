from __future__ import annotations

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

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

DEFAULT_LOCAL_URL = "http://127.0.0.1:8080/v1"
DEFAULT_LOCAL_MODEL = "ggml-org/Qwen3.5-0.8B-GGUF:Q4_0"
DEFAULT_LOCAL_TIMEOUT = 300.0
DEFAULT_LOCAL_MAX_TOKENS = 256


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


def openai_reflection(store: Store) -> tuple[str, str]:
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


def local_reflection(
    store: Store,
    base_url: str | None = None,
    model: str | None = None,
    timeout: float | None = None,
    max_tokens: int | None = None,
) -> tuple[str, str]:
    """Request a reflection from a loopback llama.cpp HTTP server."""
    base_url = (base_url or os.environ.get("CONTINUUM_LOCAL_URL") or DEFAULT_LOCAL_URL).rstrip("/")
    model = model or os.environ.get("CONTINUUM_LOCAL_MODEL") or DEFAULT_LOCAL_MODEL
    timeout = timeout if timeout is not None else float(
        os.environ.get("CONTINUUM_LOCAL_TIMEOUT", DEFAULT_LOCAL_TIMEOUT)
    )
    max_tokens = max_tokens if max_tokens is not None else int(
        os.environ.get("CONTINUUM_LOCAL_MAX_TOKENS", DEFAULT_LOCAL_MAX_TOKENS)
    )
    if timeout <= 0:
        raise RuntimeError("Local model timeout must be greater than zero.")
    if max_tokens <= 0:
        raise RuntimeError("Local model maximum output tokens must be greater than zero.")
    parsed = urlparse(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("CONTINUUM_LOCAL_URL must be an HTTP loopback URL.")

    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": INSTRUCTIONS},
                {
                    "role": "user",
                    "content": json.dumps(reflection_payload(store), indent=2),
                },
            ],
            "chat_template_kwargs": {"enable_thinking": False},
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
    ).encode("utf-8")
    request = Request(
        f"{base_url}/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Local model server returned HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach local model server at {base_url}: {exc.reason}") from exc

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Local model server returned an invalid chat-completions response.") from exc
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("Local model server returned an empty reflection.")
    return content.strip(), model


def model_reflection(
    store: Store,
    provider: str | None = None,
    local_url: str | None = None,
    local_model: str | None = None,
    timeout: float | None = None,
    max_tokens: int | None = None,
) -> tuple[str, str]:
    provider = (provider or os.environ.get("CONTINUUM_PROVIDER") or "openai").lower()
    if provider == "local":
        return local_reflection(
            store,
            base_url=local_url,
            model=local_model,
            timeout=timeout,
            max_tokens=max_tokens,
        )
    if provider == "openai":
        return openai_reflection(store)
    raise RuntimeError("CONTINUUM_PROVIDER must be 'openai' or 'local'.")
