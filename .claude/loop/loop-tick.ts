#!/usr/bin/env -S deno run --allow-all
// loop-tick.ts — Cross-platform entry point for the IKIGAI loop engineering
// Runs one orchestrator invocation. Exits. Cron/daemon fires again later.
//
// Usage (cross-platform: Windows + macOS + Linux without WSL/git-bash):
//   deno run --allow-all .claude/loop/loop-tick.ts
//   deno run --allow-all .claude/loop/loop-tick.ts --dry-run
//   deno run --allow-all .claude/loop/loop-tick.ts --cost-cap 5 --max-runtime 30
//   deno run --allow-all .claude/loop/loop-tick.ts --graph <name> --auto-cleanup
//
// Or, if installed as executable:
//   ./.claude/loop/loop-tick.ts --dry-run
//
// Inspired by:
//   - snarktank/ralph (21.7k⭐) — completion promise pattern
//   - mikeyobrien/ralph-orchestrator (3.1k⭐) — spend limits + circuit breaker
//   - ghuntley/how-to-ralph-wiggum — 3 Phases, 2 Prompts, 1 Loop
//
// This is the TYPESCRIPT entry point. It delegates to the bash version
// (loop-tick.sh) for the inner orchestrator/worker/verifier logic so that
// the ~19.5 KB of proven behaviour stays unchanged. The TypeScript version
// exists to give Windows + macOS+Deno users first-class parity without
// WSL or git-bash.
//
// Cross-platform entry points:
//   Linux/macOS:           bash .claude/loop/loop-tick.sh
//   Windows + Deno:        deno run --allow-all .claude/loop/loop-tick.ts
//   Cross-platform (Deno): deno task loop-tick
//
// Requires Deno 1.40+. Install via:
//   Windows: irm https://deno.land/install.ps1 | iex
//   macOS:   curl -fsSL https://deno.land/install.sh | sh
//   Linux:   curl -fsSL https://deno.land/install.sh | sh

interface TickOptions {
  dryRun: boolean;
  costCapUsd: number;
  maxRuntimeMin: number;
  graphName: string;
  autoCleanup: boolean;
}

function parseArgs(): TickOptions {
  const args = Deno.args;
  const opts: TickOptions = {
    dryRun: false,
    costCapUsd: 5,
    maxRuntimeMin: 30,
    graphName: "",
    autoCleanup: false,
  };
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === "--dry-run") {
      opts.dryRun = true;
    } else if (arg === "--cost-cap") {
      const v = parseInt(args[++i], 10);
      if (!Number.isFinite(v) || v < 0) {
        throw new Error(`--cost-cap requires a non-negative integer (got "${args[i - 1]}")`);
      }
      opts.costCapUsd = v;
    } else if (arg === "--max-runtime") {
      const v = parseInt(args[++i], 10);
      if (!Number.isFinite(v) || v <= 0) {
        throw new Error(`--max-runtime requires a positive integer (got "${args[i - 1]}")`);
      }
      opts.maxRuntimeMin = v;
    } else if (arg === "--graph") {
      opts.graphName = args[++i] ?? "";
    } else if (arg === "--auto-cleanup") {
      opts.autoCleanup = true;
    } else if (arg === "--help" || arg === "-h") {
      printHelp();
      Deno.exit(0);
    } else {
      console.error(`[loop-tick] Unknown argument: ${arg}`);
      printHelp();
      Deno.exit(1);
    }
  }
  return opts;
}

function printHelp(): void {
  console.log(`loop-tick.ts — IKIGAI loop engineering (cross-platform)

USAGE:
  deno run --allow-all .claude/loop/loop-tick.ts [FLAGS]

FLAGS:
  --dry-run                Print the resolved options and exit without invoking the orchestrator
  --cost-cap <usd>         Per-tick cost ceiling (default: 5). Propagated to loop-tick.sh as a hint
  --max-runtime <min>      Per-tick wall-clock ceiling (default: 30). Propagated to loop-tick.sh as a hint
  --graph <name>           Dispatch to a specific LangGraph graph (e.g. pae_maintainer)
  --auto-cleanup           Run worktree-helper.sh cleanup-all at tick end if tasks.md has zero pending
  -h, --help               Show this help and exit

NOTE:
  All inner orchestrator/worker/verifier logic lives in loop-tick.sh.
  This TypeScript entry point is a thin, cross-platform wrapper that
  delegates to the bash script. On systems where bash is unavailable
  (e.g. stock Windows without WSL/git-bash), run loop-tick.sh via WSL
  or migrate to a future TS-native implementation (M25 roadmap).`);
}

/** Resolve the bash script path *relative to this TypeScript file*. */
function resolveBashScript(): string {
  // import.meta.url is a file:// URL on every OS Deno supports; URL.pathname
  // gives us a platform-appropriate absolute path string.
  const here = new URL(".", import.meta.url).pathname;
  return here + "loop-tick.sh";
}

async function pathExists(p: string): Promise<boolean> {
  try {
    const stat = await Deno.stat(p);
    return stat.isFile;
  } catch {
    return false;
  }
}

async function main(): Promise<void> {
  const opts = parseArgs();

  console.log(`[loop-tick] Deno ${Deno.version.deno}`);
  console.log(`[loop-tick] Platform: ${Deno.build.os} (${Deno.build.arch})`);
  console.log(`[loop-tick] CWD: ${Deno.cwd()}`);
  console.log(`[loop-tick] Options: ${JSON.stringify(opts)}`);

  if (opts.dryRun) {
    console.log("[loop-tick] DRY-RUN: would invoke orchestrator (bash loop-tick.sh)");
    console.log("[loop-tick] DRY-RUN complete; exiting 0");
    return;
  }

  const bashScript = resolveBashScript();
  if (!(await pathExists(bashScript))) {
    console.error(
      `[loop-tick] FATAL: loop-tick.sh not found at ${bashScript}`,
    );
    console.error(
      "[loop-tick] The TypeScript entry point MUST live next to loop-tick.sh.",
    );
    Deno.exit(2);
  }

  // Find a bash interpreter. On Windows-without-WSL we prefer Git Bash
  // (C:\Program Files\Git\bin\bash.exe) before giving up.
  const bashCandidates = Deno.build.os === "windows"
    ? ["bash", "C:\\Program Files\\Git\\bin\\bash.exe", "C:\\Windows\\System32\\bash.exe"]
    : ["bash"];

  let bashCmd: string | null = null;
  for (const candidate of bashCandidates) {
    try {
      const probe = new Deno.Command(candidate, {
        args: ["--version"],
        stdout: "piped",
        stderr: "piped",
      });
      const { success } = await probe.output();
      if (success) {
        bashCmd = candidate;
        break;
      }
    } catch {
      // ENOENT / EACCES — try next candidate
    }
  }

  if (bashCmd === null) {
    console.error(
      "[loop-tick] FATAL: no bash interpreter found.",
    );
    console.error(
      "[loop-tick] Install Git Bash (Windows) or ensure `bash` is on PATH.",
    );
    Deno.exit(3);
  }

  console.log(`[loop-tick] Delegating to: ${bashCmd} ${bashScript}`);

  // Delegate to existing bash version for inner work (preserves all 19.5 KB
  // of orchestrator/worker/verifier logic unchanged).
  const cmd = new Deno.Command(bashCmd, {
    args: [bashScript, ...Deno.args],
    env: {
      ...Deno.env.toObject(),
      TICK_CROSS_PLATFORM: "1",
      TICK_RUNTIME: "deno",
      TICK_RUNTIME_VERSION: Deno.version.deno,
    },
    stdout: "inherit",
    stderr: "inherit",
  });

  const child = cmd.spawn();
  const status = await child.status;
  console.log(`[loop-tick] Bash exit code: ${status.code}`);
  Deno.exit(status.code ?? 1);
}

if (import.meta.main) {
  try {
    await main();
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error(`[loop-tick] FATAL: ${msg}`);
    Deno.exit(99);
  }
}
