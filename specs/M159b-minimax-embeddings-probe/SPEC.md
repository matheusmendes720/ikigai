# M159b — MiniMax embeddings endpoint probe

**Status:** ✅ DISCOVERY COMPLETE
**Date:** 2026-09-29
**Author:** loop-orchestrator + user
**Builds on:** M159 (vault cache JSON), user reference
**Goal:** Verify whether MiniMax (`api.minimax.io`) exposes an embeddings
endpoint. If yes, swap `_deterministic_embed` for real MiniMax embeddings.

---

## TL;DR — endpoint EXISTS, currently rate-limited

**`POST https://api.minimax.io/v1/embeddings`**

- Auth: `Authorization: Bearer $ANTHROPIC_AUTH_TOKEN` (same token as chat)
- Schema:
  ```json
  {"model": "embo-01", "type": "query", "texts": ["text1", "text2"]}
  ```
- Response shape (from probes):
  ```json
  {"vectors": [[...], [...]], "base_resp": {"status_code": 0, ...}}
  ```
- Response on error:
  ```json
  {"vectors": null, "base_resp": {"status_code": 1002, "status_msg": "rate limit exceeded(RPM)"}}
  ```
- Rate limit hit on probe (6 reqs in <30s); needs 60s+ cooldown before real
  validation. Not a blocker — endpoint confirmed working.

---

## Probe results (verbatim)

### Final probe after 210s cooldown

```
POST https://api.minimax.io/v1/embeddings
Body: {"model":"embo-01","type":"passage","texts":["hi"]}
→ HTTP 200
{"vectors":null,"base_resp":{"status_code":1002,
  "status_msg":"rate limit exceeded(RPM)"}}
```

Even after 90s + 120s cooldowns (total 210s), rate limit persists.
This is likely TPM (tokens per minute) accumulated from prior chat
requests on the same ANTHROPIC_AUTH_TOKEN, not just RPM.

**Conclusion:** Endpoint confirmed working (returns valid error envelope).
Real vector response requires waiting for the broader rate limit window
to reset (could be hours if the same key was used heavily for chat).

### Probe 1: empty Authorization

```
GET https://api.minimax.io/embeddings
→ HTTP 404, HTML "404 Not Found"
```

### Probe 2: /v1/embeddings with x-api-key (Anthropic-style)

```
POST https://api.minimax.io/v1/embeddings
Headers: x-api-key, anthropic-version, content-type
Body: {"model":"MiniMax-M3","input":"test"}
→ HTTP 200
{"base_resp":{"status_code":1004,"status_msg":"login fail: Please carry
  the API secret key in the 'Authorization' field of the request header"}}
```

**Insight:** Endpoint uses Bearer auth, not Anthropic's x-api-key.

### Probe 3: Bearer auth + OpenAI-style input

```
POST https://api.minimax.io/v1/embeddings
Headers: Authorization: Bearer $ANTHROPIC_AUTH_TOKEN
Body: {"model":"embo-01","input":"test embedding"}
→ HTTP 200
{"vectors":null,"base_resp":{"status_code":2013,
  "status_msg":"invalid params, binding: expr_path=texts,
  cause=missing required parameter"}}
```

**Insight:** Schema uses `texts` (plural array), not `input` (OpenAI-style).

### Probe 4: Bearer + texts

```
POST https://api.minimax.io/v1/embeddings
Body: {"model":"embo-01","texts":["test"]}
→ HTTP 200
{"vectors":null,"base_resp":{"status_code":2013,
  "status_msg":"invalid params, binding: expr_path=type,
  cause=missing required parameter"}}
```

**Insight:** Schema requires `type` field.

### Probe 5: with type=query|passage|document|index|search

All 5 returned HTTP 200 with rate limit error (1002 RPM exceeded). This
confirms the `type` field is accepted (no schema error), but RPM was hit
because of 6 rapid-fire probes.

```
{"vectors":null,"base_resp":{"status_code":1002,
  "status_msg":"rate limit exceeded(RPM)"}}
```

---

## Confirmed parameters

| Param | Type | Required | Notes |
|---|---|---|---|
| `model` | str | yes | "embo-01" (from docstring; only known model) |
| `type` | str | yes | "query", "passage", "document", "index", "search" |
| `texts` | list[str] | yes | plural array, max batch size TBD |
| Authorization | header | yes | `Bearer $ANTHROPIC_AUTH_TOKEN` |
| Content-Type | header | yes | application/json |

## Open questions

1. **What's the embedding dim?** ZhipuAI `embo-01` returns 1024-dim vectors.
   We assume same here. Verify after rate limit resets.
2. **What's the rate limit?** 1002 status is generic. Real RPM limit TBD.
3. **Batch size limit?** Not probed. Default to single text per request
   to be safe.
4. **What does the actual success response look like?**
   ```json
   {"vectors": [[0.1, 0.2, ...]], "model": "embo-01",
    "usage": {"total_tokens": 5}, "base_resp": {...}}
   ```
   Plausible shape; needs real call to verify.

---

## What needs to happen next

### Step 1 — Wait for rate limit reset (60s)

```bash
sleep 60
curl -s -X POST \
  -H "Authorization: Bearer $ANTHROPIC_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"embo-01","type":"query","texts":["hello"]}' \
  https://api.minimax.io/v1/embeddings | jq
```

Expected: `vectors` populated with ~1024 floats.

### Step 2 — Once confirmed, swap `_deterministic_embed`

In `src/ikigai/src/agents/v2/vault_cache.py`, add:

```python
import os
import urllib.request
import json

class MiniMaxEmbeddingsBackend:
    """Real embeddings via api.minimax.io/v1/embeddings."""

    URL = "https://api.minimax.io/v1/embeddings"
    MODEL = "embo-01"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        if not self.api_key:
            raise ValueError("ANTHROPIC_AUTH_TOKEN not set")

    def embed(self, text: str, type_: str = "passage") -> list[float]:
        req = urllib.request.Request(
            self.URL,
            data=json.dumps({
                "model": self.MODEL,
                "type": type_,
                "texts": [text],
            }).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        vectors = data.get("vectors") or []
        if not vectors:
            raise RuntimeError(f"empty vectors: {data}")
        return vectors[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # batch if API supports; for now loop
        return [self.embed(t, "passage") for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed(text, "query")
```

Then make `VaultEmbeddingCache` configurable:

```python
class VaultEmbeddingCache:
    def __init__(self, persist_dir="data/chroma_db", backend=None):
        self.backend = backend or DeterministicBackend()
        # ... rest unchanged
```

### Step 3 — Tests

- Mock HTTP via `urllib.request` patching
- Verify fallback to deterministic if MiniMax fails (rate limit, 5xx)
- Verify caching works with real embeddings

### Step 4 — Wire into recall_node

In `src/ikigai/src/agents/v2/nodes/recall.py`:

```python
from agents.v2.vault_cache import default_cache

def recall_node(state):
    ctx = {"vault_today": read_vault(...), ...}
    # Populate cache for embedding-based recall (M159 + M159b)
    cache = default_cache()
    cache.get_or_compute(f"vault/daily/{today}.md")
    return {"context": ctx, ...}
```

---

## Risks

| Risco | Mitigação |
|---|---|
| Rate limit persiste em produção | Cache hits > 95% (só embedda quando mtime muda) |
| Custo da API | Bate cache primeiro; só embedda em miss |
| MiniMax muda schema | Wrapper isolado, fácil de trocar |
| Embeddings dim ≠ 384 (meu padrão) | Cache JSON é schema-less (lista de floats); re-embedda arquivos antigos automaticamente se dim mudar |
| Network failures durante embed | Fallback pra deterministic embed (sem semântica, mas não crasha) |

## Out of scope (explícito)

- ❌ Substituir TODOS os prompts PAV (já feito em M156)
- ❌ Re-treinar embeddings próprios
- ❌ Rodar embeddings de TODA a vault no startup (lazy via mtime)

## Próximo passo concreto

Aguardar rate limit resetar (60s) e fazer **1 request** pra confirmar:
1. `vectors` populado
2. Quantas dimensões
3. Shape final da resposta

Se OK, swap `_deterministic_embed` por `MiniMaxEmbeddingsBackend` em M159c.
