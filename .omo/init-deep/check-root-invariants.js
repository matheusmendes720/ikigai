const fs = require('node:fs/promises');

const ROOT = 'C:/Users/mathe/code_space/life-oss/life';

const MUST_CONTAIN = [
  ['vault append-only', /append-only/i],
  ['sole vault writer / ADR-012', /ADR-012|sole writer|only writer to `?vault/i],
  ['refactor protocol', /Action Plan|refactor protocol/i],
  ['pydantic strict', /frozen=True/],
  ['extra forbid', /extra="forbid"/],
  ['contracts single source', /src\/contracts/],
  ['ueid 4-part regex', /\^\[a-z\]\{2,5\}:/],
  ['ueid canonical wins', /ADR-023/],
  ['adr-014', /ADR-014/i],
  ['dual-tree identity', /sys_ikigai/],
  ['monkeypatch both', /both/i],
  ['tooling split', /Poetry/],
  ['uv', /\buv\b/i],
  ['drift net', /test_drift_invariants\.py|drift/i],
  ['canonical scope test', /test_canonical_scope\.py/i],
  ['adr-036 paperclip', /ADR-036/],
  ['drift extended', /test_drift_extended_invariants\.py/],
  ['mesh create only', /create.{0,20}only|only.{0,20}create/i],
  ['planner-only ADR-013', /ADR-013|planner-only/i],
  ['vibe kernel path', /vibe-ops\/src\/pipeline\/policy_engine\.py/],
  ['vibe orchestration path', /vibe-ops\/src\/pipeline\/contracts\.py/],
  ['policy state enum', /PolicyState/],
  ['policy state enum location', /vibe-ops\/src\/schemas\/pydantic_v2\.py/],
  ['mcp gateway', /MCP/i],
  ['zero llm in pipeline', /zero llm|arithmetic/i],
  ['--json', /--json/],
  ['fully local', /SQLite|fully local/i],
  ['python 3.11', /3\.11/],
  ['future annotations', /from __future__ import annotations/],
  ['windows stdin fix', /buffer\.readline/i],
  ['pytest tmpdir', /pytest-tmp|PermissionError/i],
  ['make test broken', /make test/i],
  ['planning-with-files vendored', /planning-with-files/i],
  ['zero-byte artifacts', /zero.?byte/i],
  ['data-first mode', /data-first|paused/i],
  ['sonho log template', /sonho-log/i],
  ['repo url', /matheusmendes720\/ikigai/],
  ['kill switch', /kill.switch/i],
  ['kill switch path', /sys_ikigai\/security\/kill_switch\.py/],
  ['paperclip', /paperclip/i],
  ['mypy', /mypy/i],
  ['ruff', /ruff/i],
  ['console scripts', /life\.cli:_main_console|taskdog_cli/],
];

(async () => {
  const text = await fs.readFile(`${ROOT}/AGENTS.md`, 'utf8');
  const lines = text.split('\n').length;
  const headers = [...text.matchAll(/^##\s+(.+)$/gm)].map((m) => m[1].trim());
  const missing = MUST_CONTAIN.filter(([, re]) => !re.test(text)).map(([name]) => name);
  console.log(JSON.stringify({
    lines,
    inRange: lines >= 50 && lines <= 150,
    headers,
    missing,
    missingCount: missing.length,
  }, null, 1));
})();
