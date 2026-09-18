from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from continuum_core.core import PersistentCore
from continuum_core.reflection import local_reflection, offline_reflection
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


def test_local_reflection_uses_openai_compatible_loopback_server(tmp_path: Path) -> None:
    received: dict[str, object] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            received.update(json.loads(self.rfile.read(length)))
            response = {
                "choices": [
                    {"message": {"content": "OBSERVATIONS\nMock local reflection."}}
                ]
            }
            encoded = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        store = Store(tmp_path / "continuum.db")
        PersistentCore(store).initialize()
        content, model = local_reflection(
            store,
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            model="mock-local-model",
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    assert content == "OBSERVATIONS\nMock local reflection."
    assert model == "mock-local-model"
    assert received["model"] == "mock-local-model"
    assert received["max_tokens"] == 256
    assert received["chat_template_kwargs"] == {"enable_thinking": False}
    messages = received["messages"]
    assert isinstance(messages, list)
    assert "current_state" in messages[1]["content"]


def test_local_reflection_rejects_non_loopback_url(tmp_path: Path) -> None:
    store = Store(tmp_path / "continuum.db")
    PersistentCore(store).initialize()

    try:
        local_reflection(store, base_url="https://example.com/v1")
    except RuntimeError as exc:
        assert "loopback" in str(exc)
    else:
        raise AssertionError("non-loopback URL was accepted")


def test_local_reflection_accepts_output_token_override(tmp_path: Path) -> None:
    received: dict[str, object] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            received.update(json.loads(self.rfile.read(length)))
            encoded = json.dumps(
                {"choices": [{"message": {"content": "OBSERVATIONS\nShort."}}]}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        store = Store(tmp_path / "continuum.db")
        PersistentCore(store).initialize()
        local_reflection(
            store,
            base_url=f"http://127.0.0.1:{server.server_port}/v1",
            max_tokens=64,
            timeout=5,
        )
    finally:
        server.shutdown()
        thread.join()
        server.server_close()

    assert received["max_tokens"] == 64
