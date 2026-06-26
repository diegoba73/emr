import fs from 'fs';
import path from 'path';

const FRONTEND_SRC = path.join(__dirname);

/** QA-FE-ERR-03 — sin errores DRF/backend crudos en UI visible LIMS/micro. */

function collectTsxFiles(baseRelative: string): string[] {
  const root = path.join(FRONTEND_SRC, baseRelative);
  if (!fs.existsSync(root)) return [];

  const results: string[] = [];
  const walk = (dir: string, prefix: string) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const rel = `${prefix}/${entry.name}`;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(full, rel);
      } else if (entry.name.endsWith('.tsx') && !entry.name.endsWith('.test.tsx')) {
        results.push(rel);
      }
    }
  };
  walk(root, baseRelative);
  return results;
}

const SCOPED_PATHS = [
  ...collectTsxFiles('components/lims'),
  ...collectTsxFiles('pages/laboratorio'),
];

const DANGEROUS_PATTERNS: Array<{ name: string; pattern: RegExp }> = [
  { name: 'toast.error(formatDrfError', pattern: /toast\.error\s*\(\s*formatDrfError\s*\(/ },
  { name: 'toast.error(formatLimsHttpError', pattern: /toast\.error\s*\(\s*formatLimsHttpError\s*\(/ },
  { name: 'setError(formatDrfError', pattern: /setError\s*\(\s*formatDrfError\s*\(/ },
  { name: 'enqueueSnackbar(formatDrfError', pattern: /enqueueSnackbar\s*\(\s*formatDrfError\s*\(/ },
  { name: 'throw new Error(formatDrfError', pattern: /throw\s+new\s+Error\s*\(\s*formatDrfError\s*\(/ },
  {
    name: 'formatDrfError propagado a toast.error(msg)',
    pattern: /formatDrfError\s*\([^)]+\)[\s\S]{0,120}toast\.error\s*\(\s*msg\s*\)/,
  },
  {
    name: 'setError con response?.data?.detail',
    pattern: /setError\s*\([^)]*response\?\.data\?\.detail/,
  },
  {
    name: 'toast.error con error.message',
    pattern: /toast\.error\s*\([^)]*error\.message/,
  },
  {
    name: 'toast.error con err.message',
    pattern: /toast\.error\s*\([^)]*err\.message/,
  },
];

describe('QA-FE-ERR-03 — sin errores DRF crudos en UI LIMS/micro', () => {
  it('archivos LIMS/laboratorio no exponen formatDrfError ni response.data en feedback visible', () => {
    const offenders: string[] = [];

    for (const relativePath of SCOPED_PATHS) {
      const fullPath = path.join(FRONTEND_SRC, relativePath);
      const content = fs.readFileSync(fullPath, 'utf8');

      for (const { name, pattern } of DANGEROUS_PATTERNS) {
        if (pattern.test(content)) {
          offenders.push(`${relativePath} → ${name}`);
        }
      }
    }

    expect(offenders).toEqual([]);
  });
});
