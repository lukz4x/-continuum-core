# Continuum Core

Continuum Core is a small, controlled research harness for testing whether a
continuously running internal state produces stronger **functional
self-modeling** than either an ordinary chatbot or a chatbot with memory alone.

It does not claim to create or detect phenomenal consciousness. Version 0.1
creates the foundation we need before connecting a language model:

- an always-running heartbeat;
- a durable SQLite event history;
- a versioned, inspectable self-model;
- human-entered autobiographical memories;
- offline and model-assisted reflection;
- exports that make every state change auditable.

## First run on a Mac

Open Terminal in this folder and run:

```bash
chmod +x scripts/setup_mac.sh
./scripts/setup_mac.sh
source .venv/bin/activate
continuum init
continuum remember "Lucas and Continuum began the first controlled experiment."
continuum run --max-ticks 5 --interval 1
continuum status
continuum reflect --offline
continuum timeline
```

The first run does not require an API key or spend money.

## Optional model-assisted reflection

Install the optional OpenAI SDK and set two environment variables:

```bash
python -m pip install -e '.[openai]'
export OPENAI_API_KEY="your_api_key_here"
export CONTINUUM_MODEL="a-model-available-to-your-api-project"
continuum reflect
```

The API key is read from the environment and is never stored in the database.
The integration uses the Responses API pattern shown in the official OpenAI
developer quickstart.

## Commands

- `continuum init` creates the database and default self-model.
- `continuum run` advances the persistent core until interrupted.
- `continuum tick` advances it exactly once.
- `continuum remember TEXT` adds an autobiographical event.
- `continuum status` shows current state and self-model.
- `continuum reflect` asks the configured model to reflect on recent state.
- `continuum reflect --offline` creates a deterministic reflection without an API.
- `continuum timeline` shows recent events and reflections.
- `continuum export` writes a human-readable JSON snapshot.

Use `CONTINUUM_DB` to place the SQLite database somewhere other than
`./data/continuum.db`.

## Research sequence

Version 0.1 verifies persistence and auditability. It deliberately has no web
browser, shell access, financial access, autonomous replication, or ability to
change its own governing instructions. Later experiments will compare:

1. the same language model with no durable state;
2. the model with retrieved memories;
3. the model connected to this persistent core.

See [CHARTER.md](CHARTER.md) for the hypothesis, measurements, and stop rules.

