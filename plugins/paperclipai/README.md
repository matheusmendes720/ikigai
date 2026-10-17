# Life OSS Bridge — PaperclipAI Plugin

Bridges [PaperclipAI](https://paperclip.ing) agents to the [life-oss](https://github.com/matheusak/life-oss) LangGraph system, enabling PaperclipAI agents to trigger Python graph execution and sync vault ↔ PaperclipAI issues.

## Architecture

```
PaperclipAI host
  └── life-oss plugin (this package)
        ├── ctx.http → bridge server (port 8741)
        │                   └── life-oss LangGraph v2 graph
        ├── issue.created/updated events
        │                   └── vault/paperclipai_sync/ entries
        └── vault-sync job (cron: 0 2 * * *)
                            └── bulk issue sync
```

## Tools (available to PaperclipAI agents)

| Tool | Description |
|---|---|
| `Add Life OSS Task` | Add a task to the life-oss task system |
| `Read Vault Note` | Read a note from the vault by path |
| `Run Life OSS Plan` | Trigger the v2 plan workflow |
| `Life OSS Status` | Health-check the bridge server |

## Events (subscribed)

- `issue.created` → POST `/sync/issues` to bridge
- `issue.updated` → POST `/sync/issues` to bridge

## Setup

### 1. Start the bridge server

```bash
# From src/ikigai/ in the life-oss virtual environment
cd src/ikigai
poetry install
LIFE_PAPERCLIP_BRIDGE_PORT=8741 poetry run uvicorn plugins.paperclipai_bridge.main:app --port 8741 --reload
```

### 2. Install the plugin in PaperclipAI

```bash
# Local development (from this directory)
npm install   # or: bun install
npm run build

# Then in PaperclipAI:
# Settings → Plugins → Install from file → select dist/index.js

# Or publish and install from npm:
npm publish --access public
# Then in PaperclipAI: Settings → Plugins → Install @life-oss/paperclipai
```

### 3. Configure environment

In PaperclipAI plugin settings, set:

```
LIFE_PAPERCLIP_BRIDGE_URL=http://host.docker.internal:8741
```

(`host.docker.internal` resolves to the host machine from inside Docker; use `localhost` when running PaperclipAI natively.)

## Bridge API

The plugin calls these bridge endpoints (bridge server must be running on port 8741):

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `POST` | `/invoke` | Trigger LangGraph v2 graph |
| `POST` | `/sync/issues` | Sync issue to vault |
| `POST` | `/sync/vault` | Stub for vault→PaperclipAI sync |
| `GET` | `/status` | Bridge status + graph info |
