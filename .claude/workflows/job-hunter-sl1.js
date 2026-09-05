export const meta = {
  name: 'job-hunter-sl1-cli',
  description: 'Build SL1: minimal job_hunter CLI (add/list/status) with UEID + JSONL store + tests, following life/ contracts',
  phases: [
    { title: 'Discover' },
    { title: 'Design' },
    { title: 'Implement' },
    { title: 'Verify' },
  ],
};

const REPO_INVENTORY = {
  type: 'object',
  required: ['structure', 'conventions', 'entry_points', 'existing_modules', 'test_pattern'],
  properties: {
    structure: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, type: { type: 'string' }, lines: { type: 'integer' } } } },
    conventions: { type: 'array', items: { type: 'string' } },
    entry_points: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, target: { type: 'string' } } } },
    existing_modules: { type: 'array', items: { type: 'string' } },
    test_pattern: { type: 'string' },
    pdr_scope: { type: 'string' },
    issues_to_avoid: { type: 'array', items: { type: 'string' } },
  },
};

const CONTRACT_SPEC = {
  type: 'object',
  required: ['ueid_regex', 'ueid_parts', 'job_fields', 'pydantic_strict'],
  properties: {
    ueid_regex: { type: 'string' },
    ueid_parts: { type: 'array', items: { type: 'string' } },
    job_fields: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, type: { type: 'string' }, required: { type: 'boolean' }, default: { type: 'string' } } } },
    idempotency_key: { type: 'string' },
    pydantic_version: { type: 'string' },
    pydantic_strict: { type: 'object', properties: { frozen: { type: 'boolean' }, extra: { type: 'string' } } },
    cross_repo_contract: { type: 'string' },
  },
};

const PATTERN_SPEC = {
  type: 'object',
  required: ['typer_app_style', 'jsonl_store_pattern', 'atomic_write', 'cli_runner', 'json_flag'],
  properties: {
    typer_app_style: { type: 'string' },
    jsonl_store_pattern: { type: 'string' },
    atomic_write: { type: 'string' },
    cli_runner: { type: 'string' },
    json_flag: { type: 'string' },
    upsert_pattern: { type: 'string' },
    ruff_config: { type: 'string' },
  },
};

const DESIGN = {
  type: 'object',
  required: ['files', 'ueid_format', 'job_model_fields', 'cli_commands', 'test_cases', 'reversibility_strategy'],
  properties: {
    files: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, purpose: { type: 'string' }, key_classes: { type: 'array', items: { type: 'string' } } } } },
    ueid_format: { type: 'string' },
    job_model_fields: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, type: { type: 'string' }, validation: { type: 'string' }, default: { type: 'string' } } } },
    store_path: { type: 'string' },
    cli_commands: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, args: { type: 'array', items: { type: 'string' } }, json_output_shape: { type: 'string' } } } },
    test_cases: { type: 'array', items: { type: 'string' } },
    reversibility_strategy: { type: 'string' },
    telemetry_hooks: { type: 'array', items: { type: 'string' } },
    out_of_scope_v1: { type: 'array', items: { type: 'string' } },
  },
};

const CRITIQUE = {
  type: 'object',
  required: ['verdict', 'yagni_issues', 'reversibility_risks', 'telemetry_gaps', 'contract_conflicts'],
  properties: {
    verdict: { type: 'string', enum: ['ship', 'iterate', 'kill'] },
    yagni_issues: { type: 'array', items: { type: 'string' } },
    reversibility_risks: { type: 'array', items: { type: 'string' } },
    telemetry_gaps: { type: 'array', items: { type: 'string' } },
    contract_conflicts: { type: 'array', items: { type: 'string' } },
    suggested_changes: { type: 'array', items: { type: 'string' } },
    blockers: { type: 'array', items: { type: 'string' } },
  },
};

const IMPL = {
  type: 'object',
  required: ['files_created', 'files_modified', 'key_functions', 'test_results'],
  properties: {
    files_created: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, lines: { type: 'integer' }, purpose: { type: 'string' } } } },
    files_modified: { type: 'array', items: { type: 'object', properties: { path: { type: 'string' }, changes: { type: 'string' } } } },
    test_results: { type: 'object', properties: { passed: { type: 'integer' }, failed: { type: 'integer' }, output: { type: 'string' } } },
    key_functions: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, signature: { type: 'string' }, purpose: { type: 'string' } } } },
    known_gaps: { type: 'array', items: { type: 'string' } },
    next_steps: { type: 'array', items: { type: 'string' } },
  },
};

const REVIEW = {
  type: 'object',
  required: ['verdict', 'quality_issues', 'reversibility_issues', 'telemetry_issues', 'test_coverage_gaps'],
  properties: {
    verdict: { type: 'string', enum: ['pass', 'iterate', 'kill'] },
    quality_issues: { type: 'array', items: { type: 'string' } },
    reversibility_issues: { type: 'array', items: { type: 'string' } },
    telemetry_issues: { type: 'array', items: { type: 'string' } },
    test_coverage_gaps: { type: 'array', items: { type: 'string' } },
    suggested_fixes: { type: 'array', items: { type: 'string' } },
  },
};

const TEST_RUN = {
  type: 'object',
  required: ['pytest', 'ruff', 'cli_smoke', 'overall'],
  properties: {
    pytest: { type: 'object', properties: { passed: { type: 'integer' }, failed: { type: 'integer' }, output: { type: 'string' } } },
    ruff: { type: 'object', properties: { passed: { type: 'boolean' }, output: { type: 'string' } } },
    cli_smoke: { type: 'object', properties: { passed: { type: 'boolean' }, output: { type: 'string' } } },
    overall: { type: 'string', enum: ['pass', 'fail'] },
    issues: { type: 'array', items: { type: 'string' } },
  },
};

// PHASE 1: Discover
phase('Discover');

const discovery = await parallel([
  () => agent('Explore C:/Users/mathe/code_space/job_hunter repo for SL1 implementation. Read these files and report: (1) CLAUDE.md (project conventions, structure, goals); (2) pyproject.toml (deps, entry points, ruff config); (3) src/ tree (existing modules, focus on anything CLI/JSONL/Pydantic related); (4) tests/ tree (existing test conventions); (5) data/ (current state of data files); (7) PDR.md (full content if present, especially section 5 data model). Report as JSON matching REPO_INVENTORY schema. Focus on existing code patterns to mirror (not invent new), conventions to follow (Typer style, Pydantic strict, --json everywhere, append-only), existing CLI scripts to learn from, test framework + runner, anything to avoid. Do NOT modify files. Do NOT propose design. Just inventory.', {
    label: 'repo-inventory',
    phase: 'Discover',
    schema: REPO_INVENTORY,
  }),
  () => agent('Read UEID + contracts from BOTH repos to spec the Job model. Files: (1) C:/Users/mathe/code_space/life-oss/life/src/contracts/common.py (UEID regex, validators); (2) C:/Users/mathe/code_space/life-oss/life/src/contracts/task.py (Task model fields); (3) C:/Users/mathe/code_space/job_hunter/PDR.md section 5 (UEID format for jobs + discoveries); (4) C:/Users/mathe/code_space/life-oss/life/src/mesh/adapters/taskdog.py (UPSERT pattern). Report as JSON matching CONTRACT_SPEC schema. Focus on exact UEID regex (5-part format with prefix), required vs optional fields for a job application, idempotency key (likely UEID itself), Pydantic v2 strict config (frozen=True, extra="forbid"), cross-repo contract. Do NOT modify files. Do NOT invent fields. Just extract from existing code.', {
    label: 'contract-spec',
    phase: 'Discover',
    schema: CONTRACT_SPEC,
  }),
  () => agent('Read reference CLI + JSONL patterns from life/ to MIRROR. Files: (1) C:/Users/mathe/code_space/life-oss/life/src/mesh/adapters/cli.py (CliAdapter, JSONL read/write); (2) C:/Users/mathe/code_space/life-oss/life/src/mesh/adapters/base.py (ForkAdapter Protocol); (3) C:/Users/mathe/code_space/life-oss/life/src/mesh/queue.py (atomic filesystem queue); (4) C:/Users/mathe/code_space/life-oss/life/interfaces/cli/ (Typer app conventions, --json flag pattern); (5) C:/Users/mathe/code_space/life-oss/life/pyproject.toml (ruff + mypy config). Report as JSON matching PATTERN_SPEC schema. Focus on Typer app construction, --json flag handling, JSONL append with atomic os.replace, Pydantic v2 instantiation + serialization, test runner (pytest + typer.testing.CliRunner), ruff config. Do NOT modify files. Just extract patterns.', {
    label: 'pattern-spec',
    phase: 'Discover',
    schema: PATTERN_SPEC,
  }),
]);

// PHASE 2: Design + adversarial verify
phase('Design');

const design = await agent('Synthesize SL1 design from discovery inputs. Inputs: repo inventory=' + JSON.stringify(discovery[0]) + '; contract spec=' + JSON.stringify(discovery[1]) + '; pattern spec=' + JSON.stringify(discovery[2]) + '. SL1 scope (from user PDR section 1-3): 3 CLI commands minimum (jh add, jh list, jh status); --json everywhere; UEID 5-part format job:empresa:slug:uuid:hash and disc:source:slug:uuid:hash; JSONL append-only store (idempotent UPSERT on UEID); Pydantic v2 frozen=True extra=forbid; ZERO LLM in pipelines; reversible (easy schema migration, no destructive ops in v1); telemetry-first (every action produces observable artifact). Report as JSON matching DESIGN schema. Design MUST include: file structure (src/job_hunter/{cli,models,store,__init__}.py + tests/test_cli.py); UEID format with exact regex; JobApplication fields (8-10 minimum: company, role, url, applied_at, status, source, ikigai_vector, priority, notes); JSONL store path (./data/jobs.jsonl); CLI command signatures (Typer decorators); test cases (10 minimum: happy path, idempotency, --json, error cases); reversibility strategy (schema version field); telemetry hooks; out-of-scope for v1 (no auto-apply, no scraping, no LLM scoring). Do NOT write code yet. Just design.', {
    label: 'design-synth',
    phase: 'Design',
    schema: DESIGN,
});

const critique = await agent('Adversarial review of SL1 design. Design=' + JSON.stringify(design) + '. Try to BREAK the design with these lenses: (1) YAGNI: Is anything unnecessary for the user goal? (2) Reversibility: If user changes UEID format next week, can we migrate? (3) Telemetry gaps: Does this produce data to answer "is the user actually using job_hunter?"? (4) Contract conflicts: Does UEID match PDR section 5.1? Pydantic strict match life/contracts? JSONL pattern match life/src/mesh/adapters/cli.py? (5) Day-to-day usability: Can user run jh add --url X --company Y quickly? Report as JSON matching CRITIQUE schema. Verdict MUST be ship/iterate/kill. Be specific. List exactly whats wrong if anything.', {
    label: 'design-critique',
    phase: 'Design',
    schema: CRITIQUE,
});

// PHASE 3: Implement
phase('Implement');

const impl = await agent('Implement SL1 per approved design. Design=' + JSON.stringify(design) + '. Critique (apply suggested_changes if any)=' + JSON.stringify(critique) + '. Working directory: C:/Users/mathe/code_space/job_hunter. Create these files: (1) src/job_hunter/__init__.py (version + __all__); (2) src/job_hunter/models.py (JobApplication + Discovery Pydantic v2 models, frozen=True, extra=forbid); (3) src/job_hunter/store.py (JSONL append-only with atomic os.replace, idempotent UPSERT on UEID); (4) src/job_hunter/cli.py (Typer app with jh add, jh list, jh status, --json everywhere); (5) tests/test_cli.py (10+ test cases using typer.testing.CliRunner + tmp_path fixtures); (6) Update pyproject.toml: add jh entry point = job_hunter.cli:app. Constraints CRITICAL: NO LLM dependencies (no openai, anthropic, langchain); Mirror life/ contracts (Pydantic v2 frozen=True, extra=forbid, field validators); Atomic writes via os.replace (no in-place overwrites); Idempotent: jh add --url X --company Y --role Z called twice = single row (UPSERT on UEID); --json flag on every command (use typer.Option with default=False); Errors: exit code 1 + structured JSON error on --json mode; Test fixtures: use tmp_path for JSONL store; ruff: line length 100, target py311. After implementing, run tests and report: files created (path, line count); files modified; key functions; pytest output; known gaps + next steps. Report as JSON matching IMPL schema.', {
    label: 'implement-sl1',
    phase: 'Implement',
    schema: IMPL,
});

// PHASE 4: Verify
phase('Verify');

const verify = await parallel([
  () => agent('Code review of SL1 implementation. Implementation=' + JSON.stringify(impl) + '. Original design=' + JSON.stringify(design) + '. Review lenses: (1) Quality: Is code idiomatic Python? Matches patterns from life/? (2) Reversibility: Can we add/rename fields without breaking old JSONL? Schema version? (3) Telemetry: Does every CLI invocation produce observable state? (4) Test coverage: 10+ tests present? Happy path + idempotency + error cases covered? (5) Match to design: feature creep? Missing features? (6) Codebase conventions: ruff clean? line length respected? Report as JSON matching REVIEW schema. Verdict MUST be pass/iterate/kill. Be specific. List exact files + line numbers if issues found.', {
    label: 'code-review',
    phase: 'Verify',
    schema: REVIEW,
  }),
  () => agent('Execute SL1 test suite + smoke tests. Working directory: C:/Users/mathe/code_space/job_hunter. Steps: (1) cd to job_hunter; (2) uv run pytest tests/test_cli.py -v (capture output); (3) uv run ruff check src/job_hunter/ (capture output); (4) uv run jh --help (capture output); (5) uv run jh add --company TestCo --role Engineer --url https://example.com/job/1 --json (capture output); (6) cat data/jobs.jsonl (verify UEID format + idempotency). Report as JSON matching TEST_RUN schema. If any step fails, include the failure in issues array and set overall=fail. Do NOT silently retry. Do NOT skip tests. Do NOT mark pass if any check failed.', {
    label: 'test-execution',
    phase: 'Verify',
    schema: TEST_RUN,
  }),
]);

log('SL1 workflow complete.');

return {
  discovery_count: discovery.length,
  design_verdict: critique.verdict,
  impl_files: impl.files_created.length,
  test_results: verify[1].overall,
  review_verdict: verify[0].verdict,
  ship_ready: verify[0].verdict === 'pass' && verify[1].overall === 'pass' && critique.verdict !== 'kill',
  blockers: [
    ...(critique.blockers || []),
    ...(verify[0].verdict === 'kill' ? ['code-review: kill verdict'] : []),
    ...(verify[1].overall === 'fail' ? ['tests: failed'] : []),
  ],
};