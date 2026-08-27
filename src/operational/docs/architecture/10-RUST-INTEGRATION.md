# Rust Integration — Headless Core + Remote TUI

> **Status:** 🟡 Draft — design doc for Phase 4 integration.
> **Parent ADR:** `ARCHITECTURAL_REFRAMING_2026-06-07.md` (the Neovim MSGpack-RPC moment).
> **Related:** `04-INTERFACE-TUI.md`, `06-VISUAL-DEBUG-PIPELINE.md`.

---

## 1. Why Rust

The Go core (`packages/core/`) is fast enough for the current workload, but three scenarios push toward Rust:

| Scenario | Go bottleneck | Rust advantage |
|---|---|---|
| **plotext charts in a live TUI** | Go + plotext (Python FFI) has ~60 fps ceiling | Native Rust renderer via `ratatui`; zero-copy shared memory |
| **LSP-style semantic search over 100k+ journal entries** | `grep` subprocess or Go `regexp` is O(n) | `ripgrep` core + Rust `rope` is O(log n) |
| **Real-time habit-engine with 1ms polling** | Go scheduler has ~1ms minimum latency | Rust async `tokio` has sub-µs latency |
| **Cross-platform binary for `life-os`** | `pyinstaller` is 40 MB; Go builds 8 MB | `cargo build --release` = 2 MB static |

Rust is **not** a rewrite of the Go core. It is a **performance plug-in** that satisfies the same `Protocol` interface Go uses — the same way `PomodoroPlugin` is a plug-in in the existing design.

---

## 2. Architecture: Neovim-pattern applied to operational

```
Current (Go-only, synchronous):
┌─────────────────────────────────────────┐
│  apps/tui/ (Textual) ──▶ packages/core/ │  ← same process, one binary
│  apps/cli/ (Typer)   ──▶ packages/core/ │    Go-only, no FFI
└─────────────────────────────────────────┘

Proposed (Go + Rust, RPC-decoupled):
┌──────────────────────────────────────────────────────────┐
│  apps/tui-rs/ (ratatui)              apps/cli-rs/ (clap) │
│         │                                    │            │
│         │ TCP Msgpack-RPC                    │            │
│         ▼                                    ▼            │
│  ┌──────────────────────────────────────────────────┐   │
│  │  operational-core (Go headless)                  │   │
│  │  packages/core/  entities/  persistence/  meta/ │   │
│  │  serves on :7891                                 │   │
│  └──────────────────────────────────────────────────┘   │
│         │                                    │            │
│         │ Unix socket / TCP                   │            │
│         ▼                                    ▼            │
│  ┌────────────────┐             ┌──────────────────────┐│
│  │ operational-rs │             │ operational-agent-rs ││
│  │ (ratatui TUI)  │             │ (LSP search engine) ││
│  │ port 7892       │             │ port 7893            ││
│  └────────────────┘             └──────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

This mirrors Neovim exactly:
- **Headless Core** = Go `operational-core` (the pure-arithmetic engine)
- **Remote UIs** = Rust `ratatui` TUI + Rust `clap` CLI
- **Plugins** = Rust LSP search agent + future Rust analytics engine
- **RPC wire** = **Cap'n Proto** (not gRPC — Cap'n Proto has no code generation tax, works in both Go and Rust natively, and is 10x faster than Msgpack)

---

## 3. Wire Protocol: Cap'n Proto over Unix socket

### Why Cap'n Proto over gRPC

| Criteria | gRPC | Cap'n Proto | msgpack-RPC |
|---|---|---|---|
| Schema evolution | .proto files | .capnp files | No schema |
| Code gen required | Yes (stubby) | Yes (capnpc) | No |
| Zero-copy reads | ❌ | ✅ | ❌ |
| Go support | `grpc/grpc-go` | `capnproto.org/go/capnp` | `msgpackrpc` |
| Rust support | `tonic` | `capnproto` crate | `msgpack` |
| Browser support | ✅ | ❌ | ✅ |
| Speed (bench) | 1x (baseline) | 10x | 0.5x |

Cap'n Proto was designed by the same Sandlab that built the original Neovim Msgpack-RPC — it's the spiritual successor.

### Schema (`.capnp`)

```capnp
@0x8f7c3a2b1e4d5f69;

struct EntityId     { id @0 :Text; version @1 :UInt32; }
struct Routine      { id @0 :Text; name @1 :Text; period @2 :Text; ... }
struct TimeBlock    { id @0 :Text; day @1 :Text; startTs @2 :Int64; stopTs @3 :Int64; }
struct DayContext   { id @0 :Text; date @1 :Text; regime @2 :Text; qHe @3 :Float64; ... }

interface OperationalCore {
  # ── Entity CRUD ────────────────────────────────
  createRoutine  @0 (spec :Text) -> (entity :Routine)   throws Error;
  getRoutine     @1 (id   :EntityId) -> (entity :Routine) throws Error;
  listRoutines  @2 ()               -> (entities :List(Routine));
  updateRoutine  @3 (id :EntityId, patch :Text) -> (entity :Routine) throws Error;
  deleteRoutine  @4 (id :EntityId) -> () throws Error;

  # ── Algorithm calls ─────────────────────────────
  computeH       @10 (streak :Int32, lambda :Float64) -> (score :Float64);
  computeQHe    @11 (r :Float64, h :Float64) -> (q :Float64);
  classifyBudget @12 (used :Float64, capacity :Float64) -> (budgetClass :Text);
  nextStep       @13 (state :Text, historyJson :Text) -> (step :Text);

  # ── Batch ─────────────────────────────────────
  consolidateDay @20 (day :Text) -> (ctx :DayContext);
}

struct Error { code @0 :UInt32; message @1 :Text; }
```

### Go side: `capnpc-go`

```bash
# Generate Go stubs
capnpc-go -go-out=generated ./schema/opcore.capnp
```

Result: `generated/opcore.capnp.go` with `Client` interface + server boilerplate.

### Rust side: `capnproto` crate

```toml
# Cargo.toml
[dependencies]
capnproto = "0.20"
tokio = { version = "1", features = ["net-unix", "io-util"] }
```

---

## 4. Go → Rust binding strategy

There are three integration points, each with a different strategy:

### 4.1 RPC (primary) — `operational-core` as network service

```
Go headless binary  ──unix socket──▶  Rust TUI
     `opcore serve --sock /tmp/op.sock`
```

The Go binary is a **single-file binary** (`go build -ldflags="-s -w"` = ~12 MB). It runs as `opcore`, the Rust TUI runs as `op-tui`. They communicate over a Unix domain socket using Cap'n Proto messages.

**Upside:** Cleanest possible boundary. Rust TUI crashes cannot corrupt Go state. Independent version upgrades. Each side can be replaced without recompiling the other.

**Downside:** ~0.5ms round-trip latency for a call. Acceptable for TUI (human-scale latency).

### 4.2 FFI (optional) — Rust compiled as C-compatible `.so`

For the `computeH` / `computeQHe` hot path (called 60x/second during live chart rendering):

```rust
// src/ffi.rs — exposed as C ABI
#[no_mangle]
pub extern "C" fn compute_H(streak: f64, lambda: f64) -> f64 {
    1.0_f64 - (-lambda * streak).exp()
}

#[no_mangle]
pub extern "C" fn compute_QHe(r: f64, h: f64) -> f64 {
    r * (1.0 - h)
}
```

```go
// packages/core/_rust.go
//go:build rust_ffi
// +build rust_ffi

/*
#cgo LDFLAGS: -L${SRCDIR}/../../../target/release -lopcore_ffi
#include "opcore_ffi.h"
*/
import "C"

func ComputeHRust(streak, lambda float64) float64 {
    return float64(C.compute_H(C.double(streak), C.double(lambda)))
}
```

The `//go:build rust_ffi` tag means Go code still works without Rust installed (falls back to pure-Go implementation). Rust FFI is an **optional accelerator**, not a required dep.

### 4.3 Shared memory (extreme low-latency) — for chart rendering only

The plotext chart in the TUI renders at ~30 fps. At that rate, even Unix socket overhead matters. For the chart data specifically:

```
Go core process                      Rust ratatui process
      │                                     │
      │  mmap /tmp/opchart.dat  (read-only) │
      │◀────────────────────────────────────│
      │  write最新的 DayContext as msgpack  │
      │  to shared ring buffer             │
      │                                     │
```

The shared memory region is a **ring buffer** of 60 `DayContext` snapshots (one per second, last 60 seconds). Rust maps it read-only; Go writes it. This gives the chart a **0-syscall** data path — no socket, no context switch, just memory read.

---

## 5. Rust TUI scaffold — `apps/tui-rs/`

```
apps/tui-rs/
├── Cargo.toml              name = "op-tui", edition = "2021"
├── src/
│   ├── main.rs             clap entry, connects to opcore socket
│   ├── ui/
│   │   ├── app.rs          ratatui App struct
│   │   ├── screens/
│   │   │   ├── dashboard.rs
│   │   │   ├── habits.rs
│   │   │   ├── metrics.rs
│   │   │   └── pomodoro.rs
│   │   └── widgets/
│   │       ├── kpi_card.rs
│   │       ├── regime_bar.rs
│   │       ├── habit_streak.rs
│   │       └── sparkline.rs   ← reads /tmp/opchart.dat ring buffer
│   ├── rpc/
│   │   ├── client.rs        Cap'n Proto client (tokio async)
│   │   └── codec.rs         message framing
│   └── theme.rs             ratatui color palette
└── build.rs                 capnpc build script
```

**Key design rules:**
- `src/ui/` never calls `src/rpc/` directly — it holds a `Rc<RefCell<dyn OperationalCore>>`. This mirrors the Go `Repository[T]` Protocol pattern and allows mock injection in tests.
- All ratatui widgets are `From<(EntityId, &DayContext)>` — they consume the Go entity, not raw strings.
- The `sparkline.rs` widget maps the shared ring buffer directly to `ratatui::widgets::Sparkline`.

---

## 6. Rust CLI scaffold — `apps/cli-rs/`

```
apps/cli-rs/
├── Cargo.toml
├── src/
│   ├── main.rs             clap, 12 subcommands
│   ├── commands/
│   │   ├── routine.rs
│   │   ├── block.rs
│   │   ├── habit.rs
│   │   └── report.rs
│   └── format/
│       ├── json.rs
│       └── table.rs         similar to Go Rich table output
└── build.rs
```

The Rust CLI reuses the **same Cap'n Proto schema** (`schema/opcore.capnp`) as the Go core. The CLI is a thin wrapper over `rpc::client()`. It should be 200-400 KB statically linked.

---

## 7. Phased rollout

```
Phase 1 (now → +3 months): Go headless + Rust TUI over Unix socket
  - Build `opcore serve` wrapper around existing packages/core
  - Implement Cap'n Proto schema from scratch
  - Write `apps/tui-rs/` scaffold, mirror 7 Textual screens → ratatui
  - Smoke test: Rust TUI ←→ Go core, all 12 CLI commands round-trip
  → Deliverable: `opcore` binary + `op-tui` binary, user can choose either

Phase 2 (+3 → +6 months): FFI hot path
  - Extract `compute_H`, `compute_QHe`, `classify_budget` as C-ABI
  - Rust `libopcore_ffi.so` + Go FFI wrapper with build tag
  - sparkline ring buffer shared memory
  → Deliverable: chart renders at 60fps with zero syscall

Phase 3 (+6 → +12 months): Rust CLI + LSP search agent
  - `apps/cli-rs/` — 200 KB clap binary vs 12 MB Python
  - `apps/search-agent-rs/` — ripgrep-core journal search, port 7893
  → Deliverable: full Rust replacement of Python CLI stack
```

---

## 8. Anti-patterns explicitly avoided

| Don't | Why | Instead |
|---|---|---|
| Rewrite Go core in Rust | 18 months of lost work | Add Rust as a *plugin*, not a replacement |
| Expose Go structs directly over FFI | Different GC, different memory model | Cap'n Proto messages are plain structs, copy on wire |
| Use `unsafe` Rust for shared memory | TUI crashes are catastrophic | Ring buffer with `mmap` + `MSync`; Rust side is read-only |
| Bind plotext directly | Python GIL | Rust chart library (`ratatui` sparkline, `egui` for complex) |
| Hardcode socket path | Breaks on Windows | Configurable via env var `OPCORE_SOCKET`; default `/tmp/op.sock` (Unix) or `\\.\pipe\opcore` (Windows) |
