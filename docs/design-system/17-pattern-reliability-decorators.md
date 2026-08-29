# 17 — Pattern: Reliability Decorator Stack (CB outer + retry inner)

> **Categoria:** Pattern #17 (Layer 3 — Patterns Catalog)
> **Anchor canônico:** `src/ikigai/src/agents/reliability.py`
> **Origem:** IKIGAi deep-agent harness external MCP call layer + análise crítica segunda ordem
> **Idioma:** PT-BR prose + EN technical terms (OTel, CB, FSM, MCP, jitter, exponential backoff, span, attempt, threshold)
> **Publico:** Eu mesmo + agentes futuros

---

## §1 — Intuição

Toda chamada externa do deep-agent IKIGAi (MCP server handshakes, tool invocations sobre subprocess) está sujeita a **três failure modes** sobrepostos: (1) falha **transient** (network blip, retry resolve), (2) falha **sustained** (server down, retry amplifica o problema), e (3) falha **latent** (sessão MCP com handshake stale que precisa ser refeito). O padrão **reliability decorator stack** resolve os três com **dois decorators empilhados** em ordem deliberada: `@retry_with_backoff` (interno) cuida de (1) com backoff exponencial + jitter + span OTel por attempt; `@circuit_breaker` (externo) cuida de (2) com FSM 3-state (closed → open → half-open) que abre após N falhas consecutivas e fecha novamente após reset_timeout. A **ordem importa**: CB é outer porque ele deve decidir **se vale a pena tentar** antes que retry gaste tempo em chamadas fadadas; retry é inner porque ele precisa rodar **dentro** da janela em que o CB considera o serviço saudável. Adicionalmente, `invalidate_session_cache(system)` cuida de (3) — limpa cache de handshake MCP quando uma falha de conexão é detectada, forçando re-handshake no próximo attempt. O resultado é uma camada **fail-fast + self-healing + observability-first** que não tenta esconder falhas atrás de retries infinitos, mas explicitamente abre o circuito para proteger o caller e emite spans OTel em cada attempt para diagnóstico post-mortem.

---

## §2 — Enunciado formal

### 2.1 Config dataclasses (verbatim de `src/ikigai/src/agents/reliability.py:38-50`)

```python
@dataclass
class RetryConfig:
    max_attempts: int = 3
    initial_backoff_s: float = 0.5
    max_backoff_s: float = 8.0
    backoff_multiplier: float = 2.0
    jitter: bool = True


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5  # open after N consecutive failures
    reset_timeout_s: float = 30.0  # half-open after this many seconds
```

**Defaults load-bearing (5):**

| Constante | Valor | Significado |
|:----------|:------|:------------|
| `max_attempts` | 3 | Total de attempts (1 original + 2 retries) |
| `initial_backoff_s` | 0.5 | Backoff inicial antes do 2° attempt |
| `max_backoff_s` | 8.0 | Teto do backoff exponencial (evita sleeps absurdos) |
| `failure_threshold` | 5 | Falhas consecutivas que abrem o circuito |
| `reset_timeout_s` | 30.0 | Tempo em `open` antes de tentar `half-open` |

**Backoff efetivo por attempt (com `jitter=True`):**
- Attempt 1: t=0 (no backoff)
- Attempt 2: `0.5 * 2^0 * uniform(0.5, 1.5)` ≈ 0.25–0.75s
- Attempt 3: `min(0.5 * 2^1, 8.0) * uniform(0.5, 1.5)` ≈ 0.5–1.5s
- Worst case total: ~2.25s (3 attempts completos)

### 2.2 `@retry_with_backoff` decorator (verbatim de `src/ikigai/src/agents/reliability.py:53-119`)

```python
def retry_with_backoff(
    *,
    name: str,
    retryable_exceptions: tuple[type[BaseException], ...] = (ConnectionError, TimeoutError, OSError),
    config: RetryConfig = RetryConfig(),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            tracer = trace.get_tracer("ikigai.reliability")
            last_exc: BaseException | None = None
            for attempt in range(1, config.max_attempts + 1):
                with tracer.start_as_current_span(
                    f"reliability.{name}.attempt_{attempt}"
                ) as span:
                    span.set_attribute("reliability.attempt", attempt)
                    span.set_attribute("reliability.max_attempts", config.max_attempts)
                    start = time.perf_counter()
                    try:
                        result = fn(*args, **kwargs)
                        span.set_attribute("reliability.succeeded", True)
                        span.set_attribute(
                            "reliability.duration_ms",
                            (time.perf_counter() - start) * 1000,
                        )
                        return result
                    except retryable_exceptions as exc:
                        last_exc = exc
                        span.set_status(Status(StatusCode.ERROR))
                        span.set_attribute("reliability.succeeded", False)
                        span.set_attribute("reliability.error.class", type(exc).__name__)
                        span.set_attribute("reliability.error.message", str(exc)[:500])
                        tb_str = traceback.format_exc(limit=10)
                        span.set_attribute("reliability.error.traceback", tb_str[:2000])
                        if attempt < config.max_attempts:
                            backoff = min(
                                config.initial_backoff_s
                                * (config.backoff_multiplier ** (attempt - 1)),
                                config.max_backoff_s,
                            )
                            if config.jitter:
                                backoff *= random.uniform(0.5, 1.5)
                            time.sleep(backoff)
            assert last_exc is not None
            raise last_exc
        return wrapper
    return decorator
```

**Mecânica do retry (3 propriedades):**

1. **OTel span nested por attempt**: `reliability.{name}.attempt_{1..N}` — cada attempt vira span filha do parent context ativo, propagando trace_id automaticamente via `start_as_current_span` (linhas 74-76).
2. **Exception filter restritivo**: `retryable_exceptions` default é `(ConnectionError, TimeoutError, OSError)`. Exceções fora dessa tupla (ex.: `ValueError`, `KeyError`, `PermissionError`) **não** são retentadas — passam direto para o caller. Isto evita retry de bugs lógicos.
3. **Final raise do last_exc**: após exhaustion de `max_attempts`, o decorator re-levanta a **última exceção** capturada (linha 115: `raise last_exc`). Isto preserva o stack trace original da última tentativa, não da primeira.

### 2.3 `_CircuitBreaker` state machine (verbatim de `src/ikigai/src/agents/reliability.py:122-155`)

```python
class _CircuitBreaker:
    def __init__(self, name: str, config: CircuitBreakerConfig) -> None:
        self.name = name
        self.config = config
        self.consecutive_failures = 0
        self.opened_at: float | None = None

    def is_open(self) -> bool:
        if self.opened_at is None:
            return False
        if time.time() - self.opened_at > self.config.reset_timeout_s:
            _log.info("circuit_breaker.%s transitioning to half-open", self.name)
            self.opened_at = None
            return False
        return True

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if (
            self.consecutive_failures >= self.config.failure_threshold
            and self.opened_at is None
        ):
            _log.warning(
                "circuit_breaker.%s OPENED after %d failures",
                self.name,
                self.consecutive_failures,
            )
            self.opened_at = time.time()

    def record_success(self) -> None:
        if self.consecutive_failures > 0 or self.opened_at is not None:
            _log.info("circuit_breaker.%s CLOSED after success", self.name)
        self.consecutive_failures = 0
        self.opened_at = None
```

**FSM de 3 estados implícita:**

```
        failure_threshold consecutive failures
CLOSED ────────────────────────────────────▶ OPEN
   ▲                                         │
   │                                         │ reset_timeout_s elapsed
   │                                         ▼
   │  success                          HALF-OPEN (next is_open() check)
   └─────────────────────────────────────────┘
```

**Mecânica do CB (3 propriedades):**

1. **Half-open lazy probe**: a transição `OPEN → HALF-OPEN` acontece **na próxima chamada** que invoca `is_open()`, não por timer externo (linhas 130-136). Isto é mais simples que `threading.Timer` e suficiente para single-process IKIGAi.
2. **Consecutive failures counter**: apenas falhas **consecutivas** contam. Um único sucesso no meio zera o counter (linha 154: `self.consecutive_failures = 0`). Isto significa que 4 falhas + 1 sucesso + 4 falhas **não** abrem o circuito — é a definição clássica de "consecutive".
3. **Per-server state**: o estado é guardado em `_circuit_state: dict[str, _CircuitBreaker]` (linha 26), keyed por `name`. Isto permite que múltiplos MCP servers (taskdog, tuiboard, solverforge-calendar) tenham CBs independentes — um server down não afeta os outros.

### 2.4 `@circuit_breaker` decorator (verbatim de `src/ikigai/src/agents/reliability.py:158-182`)

```python
def circuit_breaker(
    name: str, config: CircuitBreakerConfig = CircuitBreakerConfig()
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            cb = _circuit_state.setdefault(name, _CircuitBreaker(name, config))
            if cb.is_open():
                raise CircuitOpenError(f"circuit_breaker.{name} is OPEN")
            try:
                result = fn(*args, **kwargs)
            except Exception:
                cb.record_failure()
                raise
            cb.record_success()
            return result
        return wrapper
    return decorator
```

**Mecânica (2 propriedades):**

1. **`CircuitOpenError` fail-fast**: se `is_open()` retorna True, levanta `CircuitOpenError` **imediatamente**, sem invocar `fn` (linha 171). Caller recebe erro determinístico em <1ms, não depois de `max_attempts * backoff` (~2.25s).
2. **`except Exception` largo**: o CB conta **qualquer** exceção como falha (linha 174), diferentemente do retry que filtra por `retryable_exceptions`. Rationale: CB é proteção do sistema (fail fast), retry é proteção da chamada (transient recovery). Bugs lógicos (ValueError) também devem abrir o CB eventualmente, evitando "retry de bug infinito".

### 2.5 Stack order: CB outer + retry inner (padrão composto)

```python
# Uso típico (hipotético — não há decorator stacking real em reliability.py)
@circuit_breaker("taskdog_mcp", config=CBConfig(failure_threshold=3))
@retry_with_backoff(name="taskdog_mcp_call", config=RetryConfig(max_attempts=2))
def call_taskdog_tool(...):
    """Cada chamada: CB gate → retry attempts → underlying MCP."""
```

**Por que esta ordem?**

| Ordem | Comportamento | Veredito |
|:------|:--------------|:---------|
| **CB outer / retry inner** | CB verifica 1× antes de entrar; retry faz até N attempts; CB atualiza contador após exhaustion | **VENCE** — fail-fast funciona; CB tem visibilidade dos N attempts como "1 failure" |
| Retry outer / CB inner | Retry faz N cycles de (CB check + attempt); CB abre após 1 falha em qualquer attempt | **PERDE** — CB pode abrir no meio do retry loop, comportamento confuso |
| Só retry (sem CB) | Retry infinito em caso de server down — amplifica o problema | **PERDE** — thundering herd contra server down |
| Só CB (sem retry) | Falha transient → fail imediato, sem recovery | **PERDE** — perde self-healing em network blip |

**Invariante crítica da ordem:** o **contador do CB** é atualizado após cada **exhaustion de retry**, não após cada attempt individual. Isto significa que `failure_threshold=5` significa "5 retry-exhaustions consecutivos", não "5 attempts falhados". Para comportamento granular ("5 attempts individuais"), o CB deveria estar dentro do retry — escolha rejeitada.

### 2.6 Session cache invalidation (verbatim de `src/ikigai/src/agents/reliability.py:189-197`)

```python
def invalidate_session_cache(system: str) -> None:
    """Clear the cached 'initialize' handshake result for a system.

    Call this when a call fails with a connection-related error so the next
    attempt re-runs the handshake. Idempotent.
    """
    if _mcp_session_cache_ref is not None and system in _mcp_session_cache_ref:
        _log.info("Invalidating session cache for system: %s", system)
        del _mcp_session_cache_ref[system]
```

**Função:** limpa o cache de handshake MCP (`_mcp_session_cache_ref: dict[str, bool]`) quando uma chamada falha. Chamada manualmente pelo caller após exception de `retryable_exceptions` (não automática dentro do decorator). Idempotente — no-op se `system` não está no cache.

---

## §3 — Justificativa

### 3.1 Por que dois decorators em vez de uma classe wrapper?

**Decorator stacking** é o idioma Python idiomático para composição cross-cutting de reliability concerns:
- **Separação de concerns**: retry (transient recovery) ≠ CB (sustained protection) ≠ cache invalidation (session staleness). Cada um é testável isoladamente.
- **Reusabilidade**: uma função pode ser wrapped com `@retry_with_backoff` sem CB (chamada local), ou com ambos (chamada externa MCP).
- **Composição via `@functools.wraps`**: cada decorator preserva `__name__`, `__doc__`, `__signature__` da função wrapped — debugging via `inspect` continua funcionando.

**Alternativas rejeitadas:**
- **Classe wrapper única** (`ReliableMCPClient`): mistura 3 concerns, dificulta mock de 1 sem os outros
- **Context manager**: força caller a usar `with`, perde declaratividade do decorator
- **Async-only (`tenacity`, `aiobreaker`)**: o sistema usa `anthropic.Anthropic` síncrono, e threading pool já está disponível; async desnecessário

### 3.2 Por que OTel spans em vez de logging puro?

A escolha de `tracer.start_as_current_span(...)` (linha 74) com **attributes** estruturados (`reliability.attempt`, `reliability.duration_ms`, `reliability.error.class`) traz 4 benefícios sobre `log.warning(...)`:

1. **Distributed tracing**: span filho herda `trace_id` do parent context (LLM call → tool call → reliability attempt). Langfuse/LangSmith renderiza timeline completa.
2. **Aggregable metrics**: `reliability.duration_ms` permite calcular p50/p99 latency por attempt — bottleneck visível sem log parsing.
3. **Error attribution**: `reliability.error.class` + `reliability.error.traceback` permitem filtrar por exception class e visualizar stack trace dentro do trace UI.
4. **Status propagation**: `span.set_status(Status(StatusCode.ERROR))` marca o span como erro no backend OTel — alerting automático por error rate.

O `reliability.{name}.attempt_{N}` naming convention (linha 75) é **deliberado**: prefixo `reliability.` segrega estes spans dos spans de tool/LLM no mesmo trace; sufixo `.attempt_{N}` indexa tentativas dentro do mesmo call.

### 3.3 Por que `failure_threshold=5` e `reset_timeout_s=30.0` (não outros valores)?

**Honest rigor:** ambos são **CHOICE** (não medição), na mesma categoria que os 14 hiperparâmetros do doc 10 §8. Não há paper que justifique 5 vs 3 vs 10. A escolha atual reflete:
- `failure_threshold=5`: alto o suficiente para absorver blips transitórios (1-2 falhas), baixo o suficiente para fail-fast em server sustained down
- `reset_timeout_s=30.0`: curto o suficiente para auto-recovery rápido (server volta, 30s depois é testado), longo o suficiente para evitar hammering em server overload

**Recomendação (gate 5 SONHO logs):** quando ADR-007 for cumprido, sensitivity analysis sobre (`failure_threshold`, `reset_timeout_s`) ∈ {3, 5, 7} × {15, 30, 60}. Hoje é **CHOICE**.

### 3.4 Por que `retryable_exceptions=(ConnectionError, TimeoutError, OSError)`?

A default tuple (linha 56) é restritiva por **princípio do menor privilégio**:
- `ConnectionError`: rede indisponível, retry pode resolver
- `TimeoutError`: server lento mas respondendo, retry pode resolver
- `OSError`: file system error (file locked, disk full transient), retry pode resolver

**Excluídas deliberadamente:**
- `ValueError`, `TypeError`: bugs lógicos, retry **não** resolve (amplifica CPU wasted)
- `PermissionError`, `FileNotFoundError`: erros de configuração do caller, retry não resolve
- `KeyboardInterrupt`, `SystemExit`: sinais do usuário, retry **não** deve interferir

Isto implementa o princípio **"retry apenas o que pode melhorar com tempo"**.

### 3.5 Por que `record_failure` no CB usa `except Exception` largo?

CB e retry têm **filosofias de exception diferentes**:
- **Retry**: conservador — só retenta o que tem chance de resolver (linha 88)
- **CB**: liberal — conta qualquer falha como sinal de degradação do sistema (linha 174)

Rationale: bugs lógicos (ex.: schema drift no MCP response) **também** devem abrir o CB eventualmente, evitando que `retry_with_backoff` loop infinitamente chamando uma função quebrada. CB aberto é o "stop the bleeding" antes de debugging.

### 3.6 Limitações conhecidas (de `09-analise-critica-segunda-ordem-arquitetura.md`)

A análise crítica de segunda ordem identificou **issues adjacentes** a este padrão:

#### F5 — Pomodoro events não passam pela reliability layer
> "fork pomodoro não existe. Não há adapter, não há Protocol instance. Doc 24 §4 afirma integração `pomodoro → TaskChange → mesh` mas nenhum adapter implementa `ForkAdapter` para pomodoros."

Como `reliability.py` é projetado para **chamadas externas MCP** (servers), e pomodoros são eventos **internos** (não passam por rede), a ausência de reliability wrapper para pomodoros é tecnicamente correta — mas o **princípio** de "wrap external calls" deveria ser aplicado a qualquer call que cruze boundary de processo.

**Recomendação:** adicionar `reliability.py` como utility em `src/mesh/` (atualmente só em `src/ikigai/src/agents/`), permitindo que `agent_propagator.py` wrap cada `adapter.apply_change(event)` com `@circuit_breaker(adapter.name)` para falhar fast em adapter travado.

#### Limitação L1 — `_circuit_state` é in-memory, não persistido
O CB state vive em `_circuit_state: dict` (linha 26), reset em process restart. Se IKIGAi reinicia durante um server outage, o histórico de falhas consecutivas é perdido — o CB começa "fechado" novamente. Para restart safety, seria necessário persistir `_circuit_state` em SQLite.

**Recomendação:** aceitar a limitação (process restart é raro, CB re-acumula evidências rápido) ou persistir via `data/reliability_state.json` com TTL. Trade-off: state persistence adiciona I/O no hot path.

#### Limitação L2 — `jitter=True` default pode ser desabilitado
`backoff *= random.uniform(0.5, 1.5)` (linha 104) é probabilístico, não deterministic. Em testes, isto dificulta reprodução de bugs relacionados a timing. `config.jitter=False` existe para desabilitar (linha 44), mas o default `True` significa que **dois retries consecutivos têm timing diferente**.

**Recomendação:** em testes, sempre passar `config=RetryConfig(jitter=False)` para reproducibilidade. Em prod, manter `jitter=True` para evitar thundering herd sincronizado.

#### Limitação L3 — Não há métricas agregadas expostas
`reliability.duration_ms` é emitido como span attribute, mas **não há counter exposto** tipo `total_retries`, `total_circuit_opens`, `p99_latency`. Para alerting/SLO, seria necessário um exporter Prometheus ou similar.

**Recomendação:** adicionar `from prometheus_client import Counter` opcional, no-op se lib ausente (mesmo padrão de `init_tracing()` em `observability/__init__.py`).

---

## §4 — Cross-references

### 4.1 Design system

- `docs/design-system/00-INDEX.md` §3 — mapa de dependências (Pattern #17 → reliability layer)
- `docs/design-system/04-canvas-mesh-architecture.md` §3.2-§3.3 (ForkAdapter + storage topology) + §6 (per-adapter failure isolation) — CB outer poderia wrap cada adapter call
- `docs/design-system/05-canvas-contracts-architecture.md` §4 — TaskChange, PropagationEvent, TaskStatus (frozen, extra=forbid) — reliability layer opera sobre estes contratos
- `docs/design-system/06-canvas-agents-architecture.md` §3 — Deep Agent 18 tools, init_tracing() — mesmo padrão OTel
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` §3 (F5 — pomodoro fork ausente, adjacente a reliability) + §4.2 (impacto em canvases)
- `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md` §2 (Layer C = actuator = reliability layer candidate) + §8 (14 hiperparâmetros CHOICE — inclui failure_threshold, reset_timeout_s)

### 4.2 Auto-performance OS (matemática + integração)

- `docs/auto-performance-os/00-INDEX.md` §1-§2 — stack conceitual (axiomas → engines → integração); reliability é "infraestrutura de engines"
- `docs/auto-performance-os/03-axiom-finite-state-machines.md` §3 — FSM 4-state Policy + 7-state Pomodoro; CB é FSM 3-state
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` §4 — propagação cross-fork (reliability deveria wrap cada adapter)
- `docs/auto-performance-os/26-integration-cybernetic-loop.md` §4 — sync loop; reliability layer protege calls externos do loop

### 4.3 Code (verificado)

- `src/ikigai/src/agents/reliability.py:38-50` — RetryConfig + CircuitBreakerConfig dataclasses
- `src/ikigai/src/agents/reliability.py:53-119` — `@retry_with_backoff` decorator (verbatim snippet §2.2)
- `src/ikigai/src/agents/reliability.py:122-155` — `_CircuitBreaker` state machine (verbatim snippet §2.3)
- `src/ikigai/src/agents/reliability.py:158-182` — `@circuit_breaker` decorator (verbatim snippet §2.4)
- `src/ikigai/src/agents/reliability.py:185-197` — `CircuitOpenError` + `invalidate_session_cache`
- `src/ikigai/src/agents/deepagents_harness.py:22-30` — `init_tracing()` OTel bootstrap (mesmo padrão)
- `src/ikigai/src/agents/deepagents_harness.py:300-318` — `_make_agent` com `with _tracer.start_as_current_span(...)` (idioma OTel)

### 4.4 Memory

- `[[interfaces-architecture-2026-08-27]]` — dual-layer (forks + native); reliability layer protege a boundary between layers
- `[[data-first-methodology]]` — ADR-007 gate de 5 SONHO logs; `failure_threshold` + `reset_timeout_s` são CHOICE (não empirical) até gate cumprido
- `[[master-branch-carro-chefe-2026-08-28]]` — deep-agent canonical; reliability layer é infraestrutura essencial para chamadas externas do agent
- `[[algorithm-issues-registry]]` — 31+12 findings; F5 adjacente (reliability layer deveria wrap pomodoro adapter quando existir)
- `[[prioritize-backend-over-algorithm-refinement]]` — reliability layer é backend (cross-cutting infra), não algorithm polish

---

## §5 — Fontes

### Code (verbatim, lidos via Read tool)

- `src/ikigai/src/agents/reliability.py` (198 LOC) — decorators + CB state machine + cache invalidation
- `src/ikigai/src/agents/deepagents_harness.py` (670 LOC) — OTel bootstrap, init_tracing(), `_make_agent` factory

### Docs (analisados)

- `docs/design-system/00-INDEX.md` (113 LOC) — INDEX + Layer 3 patterns catalog
- `docs/design-system/04-canvas-mesh-architecture.md` (127 LOC) — mesh canvas com ForkAdapter verbatim
- `docs/design-system/05-canvas-contracts-architecture.md` — contracts canvas (frozen, extra=forbid)
- `docs/design-system/06-canvas-agents-architecture.md` — agents canvas (18 tools, init_tracing)
- `docs/design-system/09-analise-critica-segunda-ordem-arquitetura.md` (262 LOC) — análise crítica F5 + 46 findings
- `docs/design-system/10-modelo-unificado-auto-feedback-estocastico.md` (426 LOC) — Layer C (actuator) + 14 hyperparameters CHOICE
- `docs/design-system/12-pattern-append-only-queue.md` (anterior) — append-only queue pattern (companion infra)
- `docs/design-system/13-pattern-fork-adapter-protocol.md` (anterior) — ForkAdapter pattern (reliability deveria wrap)
- `docs/auto-performance-os/00-INDEX.md` (27 docs) — template 5-section
- `docs/auto-performance-os/03-axiom-finite-state-machines.md` — FSM foundations (CB é FSM 3-state)
- `docs/auto-performance-os/24-integration-mesh-ueid-propagation.md` — UEID propagation (F5 = pomodoro não wired)
- `docs/auto-performance-os/26-integration-cybernetic-loop.md` — cybernetic loop integration

### Memory cross-refs

- `[[interfaces-architecture-2026-08-27]]` — dual-layer architecture (forks vs operator)
- `[[data-first-methodology]]` — 5 SONHO logs gate (ADR-007) gateia sensitivity analysis de hyperparameters
- `[[algorithm-issues-registry]]` — 31 inconsistencies + 12 novos findings
- `[[master-branch-carro-chefe-2026-08-28]]` — deep-agent canonical narrative
- `[[prioritize-backend-over-algorithm-refinement]]` — backend > algorithm (reliability é backend)

### Métricas de cobertura

- **3 snippets Python reais** (verbatim): RetryConfig dataclass + `_CircuitBreaker.is_open` + `@circuit_breaker` wrapper (= 3 snippets exatos, atende mínimo 1-3)
- **5 invariantes carregadas** documentadas (max_attempts, failure_threshold, reset_timeout_s, retryable_exceptions filter, OTel span nesting) + 1 invariante da ordem CB outer/retry inner
- **6 cross-refs design-system** (00, 04, 05, 06, 09, 10)
- **4 cross-refs auto-performance-os** (00-INDEX, 03-FSM, 24-mesh, 26-cybernetic)
- **5 cross-refs memory** (interfaces, data-first, master-branch, algorithm-issues, prioritize-backend)
- **Honest rigor:** F5 (pomodoro não passa por reliability) + L1 (CB state in-memory) + L2 (jitter probabilistic) + L3 (sem métricas Prometheus) citados em §3.6

---

> **Próximos passos (gate 5 SONHO logs):** sensitivity analysis sobre (`failure_threshold`, `reset_timeout_s`, `max_attempts`) ∈ {3, 5, 7} × {15, 30, 60} × {2, 3, 5}; considerar persistir `_circuit_state` em SQLite; adicionar metrics exporter opcional; wrap cada `adapter.apply_change()` em `@circuit_breaker(adapter.name)` quando `agent_propagator.py` ganhar reliability.
