const fs = require('node:fs/promises');
const { spawnSync } = require('node:child_process');

const ROOT = 'C:/Users/mathe/code_space/life-oss/life';
const MODE = process.argv[2];
const EXCLUDE_BEGIN = '# >>> init-deep managed block >>>';
const EXCLUDE_END = '# <<< init-deep managed block <<<';

function git(args) {
  return spawnSync('git', args, { cwd: ROOT, maxBuffer: 1 << 28 }).stdout.toString();
}

async function main() {
  const commitSha = git(['rev-parse', 'HEAD']).trim();
  const files = git(['ls-files', '-z']).split('\0').filter(Boolean);
  let loc = 0;
  const textExt = /\.(py|ts|tsx|js|jsx|rs|toml|yaml|yml|json|md|bat|sh|cfg|ini)$/i;
  for (const f of files) {
    if (!textExt.test(f)) continue;
    try {
      const s = await fs.readFile(`${ROOT}/${f}`, 'utf8');
      loc += s.split('\n').length;
    } catch {}
  }
  const snapshot = { commitSha, fileCount: files.length, loc, timestamp: Date.now(), mode: MODE };
  await fs.writeFile(`${ROOT}/.omo/init-deep.json`, JSON.stringify(snapshot, null, 2) + '\n');

  const excludePath = `${ROOT}/.git/info/exclude`;
  let exclude = '';
  try { exclude = await fs.readFile(excludePath, 'utf8'); } catch {}
  const managed = [
    EXCLUDE_BEGIN,
    '# Managed by init-deep. Local-mode generated guidance is not committed.',
    '.omo/init-deep/',
    '.omo-initdeep-*.json',
    EXCLUDE_END,
  ].join('\n');
  const stripped = exclude.includes(EXCLUDE_BEGIN)
    ? exclude.replace(new RegExp(`${EXCLUDE_BEGIN}[\\s\\S]*?${EXCLUDE_END}\\n?`), '')
    : exclude;
  const next = MODE === 'local'
    ? stripped.replace(/\s*$/, '\n\n') + managed + '\n'
    : stripped.replace(/\s*$/, '\n');
  await fs.writeFile(excludePath, next);

  const nested = [];
  async function walk(dir, depth) {
    let entries = [];
    try { entries = await fs.readdir(dir, { withFileTypes: true }); } catch { return; }
    for (const e of entries) {
      if (!e.isDirectory()) continue;
      if (e.name === '.git' || e.name === 'node_modules' || e.name === 'worktrees') continue;
      const p = `${dir}/${e.name}`;
      const rel = p.slice(ROOT.length + 1).replace(/\\/g, '/');
      try {
        const st = await fs.stat(`${p}/AGENTS.md`);
        if (st.isFile()) nested.push(rel + '/AGENTS.md');
      } catch {}
      if (depth < 6) await walk(p, depth + 1);
    }
  }
  await walk(ROOT, 0);

  console.log(JSON.stringify({ snapshot, mode: MODE, nestedCount: nested.length, nested }, null, 1));
}

main();
