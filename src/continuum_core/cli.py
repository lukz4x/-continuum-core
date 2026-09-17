from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .core import PersistentCore
from .reflection import model_reflection, offline_reflection
from .storage import Store


def default_db_path() -> Path:
    return Path(os.environ.get("CONTINUUM_DB", "data/continuum.db")).expanduser()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="continuum",
        description="Persistent-core research harness",
    )
    parser.add_argument("--db", type=Path, default=default_db_path())
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize the persistent store")
    sub.add_parser("tick", help="Advance the persistent core once")

    run = sub.add_parser("run", help="Run the persistent heartbeat")
    run.add_argument("--interval", type=float, default=60.0)
    run.add_argument("--max-ticks", type=int)

    remember = sub.add_parser("remember", help="Add a human-supplied autobiographical event")
    remember.add_argument("text")
    remember.add_argument("--kind", default="autobiographical")

    sub.add_parser("status", help="Show current state and self-model")

    reflect = sub.add_parser("reflect", help="Create and store a reflection")
    reflect.add_argument("--offline", action="store_true")

    timeline = sub.add_parser("timeline", help="Show recent events and reflections")
    timeline.add_argument("--limit", type=int, default=20)

    export = sub.add_parser("export", help="Export an auditable JSON snapshot")
    export.add_argument("--output", type=Path, default=Path("exports/snapshot.json"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    store = Store(args.db)
    core = PersistentCore(store)

    if args.command == "init":
        core.initialize()
        print(f"Initialized {args.db}")
    elif args.command == "tick":
        print(json.dumps(core.tick(), indent=2))
    elif args.command == "run":
        if args.interval <= 0:
            raise SystemExit("--interval must be greater than zero")
        if args.max_ticks is not None and args.max_ticks <= 0:
            raise SystemExit("--max-ticks must be greater than zero")
        core.run(interval=args.interval, max_ticks=args.max_ticks)
    elif args.command == "remember":
        core.initialize()
        event_id = store.add_event(args.kind, args.text, source="human")
        print(f"Recorded event {event_id}")
    elif args.command == "status":
        core.initialize()
        snapshot = store.snapshot()
        print(json.dumps({"state": snapshot["state"], "self_model": snapshot["self_model"]}, indent=2))
    elif args.command == "reflect":
        core.initialize()
        if args.offline:
            content = offline_reflection(store)
            mode, model = "offline", None
        else:
            content, model = model_reflection(store)
            mode = "model"
        reflection_id = store.add_reflection(content, mode=mode, model_name=model)
        print(f"Reflection {reflection_id}\n\n{content}")
    elif args.command == "timeline":
        core.initialize()
        print("EVENTS")
        for event in store.recent_events(args.limit):
            print(f"{event['created_at']} [{event['kind']}/{event['source']}] {event['content']}")
        print("\nREFLECTIONS")
        for reflection in store.recent_reflections(args.limit):
            label = reflection["model_name"] or reflection["mode"]
            print(f"{reflection['created_at']} [{label}]\n{reflection['content']}\n")
    elif args.command == "export":
        core.initialize()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(store.snapshot(), indent=2) + "\n", encoding="utf-8")
        print(f"Exported {args.output}")


if __name__ == "__main__":
    main()

