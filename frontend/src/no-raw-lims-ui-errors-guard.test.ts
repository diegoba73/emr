import fs from 'fs';
import path from 'path';

const FRONTEND_SRC = path.join(__dirname);

/** QA-FE-ERR-03 / QA-FE-ERR-03A — sin errores DRF/backend crudos en UI visible LIMS/micro. */

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

const UTILS_LIMS_PATHS = ['utils/limsDownload.ts'];

const DANGEROUS_PATTERNS: Array<{ name: string; pattern: RegExp }> = [
  { name: 'toast.error(formatDrfError', pattern: /toast\.error\s*\(\s*formatDrfError\s*\(/ },
  { name: 'toast.error(formatLimsHttpError', pattern: /toast\.error\s*\(\s*formatLimsHttpError\s*\(/ },
  { name: 'snackbar(formatDrfError', pattern: /snackbar\s*\(\s*formatDrfError\s*\(/ },
  { name: 'snackbar(formatLimsHttpError', pattern: /snackbar\s*\(\s*formatLimsHttpError\s*\(/ },
  { name: 'enqueueSnackbar(formatDrfError', pattern: /enqueueSnackbar\s*\(\s*formatDrfError\s*\(/ },
  { name: 'enqueueSnackbar(formatLimsHttpError', pattern: /enqueueSnackbar\s*\(\s*formatLimsHttpError\s*\(/ },
  { name: 'setError(formatDrfError', pattern: /setError\s*\(\s*formatDrfError\s*\(/ },
  { name: 'throw new Error(formatDrfError', pattern: /throw\s+new\s+Error\s*\(\s*formatDrfError\s*\(/ },
  { name: 'throw new Error(formatLimsHttpError', pattern: /throw\s+new\s+Error\s*\(\s*formatLimsHttpError\s*\(/ },
  {
    name: 'formatDrfError propagado a toast.error(msg)',
    pattern: /formatDrfError\s*\([^)]+\)[\s\S]{0,120}toast\.error\s*\(\s*msg\s*\)/,
  },
  {
    name: 'formatLimsHttpError propagado a toast.error(msg)',
    pattern: /formatLimsHttpError\s*\([^)]+\)[\s\S]{0,120}toast\.error\s*\(\s*msg\s*\)/,
  },
  {
    name: 'formatLimsHttpError propagado a setError(msg)',
    pattern: /formatLimsHttpError\s*\([^)]+\)[\s\S]{0,120}setError\s*\(\s*msg\s*\)/,
  },
  {
    name: 'setError con response?.data?.detail',
    pattern: /setError\s*\([^)]*response\?\.data\?\.detail/,
  },
  {
    name: 'setError con response.data.detail',
    pattern: /setError\s*\([^)]*response\.data\.detail/,
  },
  {
    name: 'setError con response?.data?.error',
    pattern: /setError\s*\([^)]*response\?\.data\?\.error/,
  },
  {
    name: 'setError con response.data.error',
    pattern: /setError\s*\([^)]*response\.data\.error/,
  },
  {
    name: 'setError con response?.data?.message',
    pattern: /setError\s*\([^)]*response\?\.data\?\.message/,
  },
  {
    name: 'setError con response.data.message',
    pattern: /setError\s*\([^)]*response\.data\.message/,
  },
  {
    name: 'toast.error con error.message',
    pattern: /toast\.error\s*\([^)]*error\.message/,
  },
  {
    name: 'toast.error con err.message',
    pattern: /toast\.error\s*\([^)]*err\.message/,
  },
  {
    name: 'alert con error.message',
    pattern: /alert\s*\([^)]*error\.message/,
  },
  {
    name: 'alert con err.message',
    pattern: /alert\s*\([^)]*err\.message/,
  },
];

const LIMS_DOWNLOAD_UNSAFE_PATTERNS: Array<{ name: string; pattern: RegExp }> = [
  { name: 'safeDrfDetail o parseo detail', pattern: /safeDrfDetail|data\.detail/ },
  { name: 'retorno ax.message', pattern: /return\s+ax\.message/ },
  { name: 'retorno error.message backend', pattern: /return\s+error\.message/ },
];

function scanFiles(paths: string[], patterns: Array<{ name: string; pattern: RegExp }>): string[] {
  const offenders: string[] = [];
  for (const relativePath of paths) {
    const fullPath = path.join(FRONTEND_SRC, relativePath);
    const content = fs.readFileSync(fullPath, 'utf8');
    for (const { name, pattern } of patterns) {
      if (pattern.test(content)) {
        offenders.push(`${relativePath} → ${name}`);
      }
    }
  }
  return offenders;
}

describe('QA-FE-ERR-03 — sin errores DRF crudos en UI LIMS/micro', () => {
  it('archivos LIMS/laboratorio no exponen formatDrfError ni response.data en feedback visible', () => {
    expect(scanFiles(SCOPED_PATHS, DANGEROUS_PATTERNS)).toEqual([]);
  });

  it('formatLimsPdfDownloadError no parsea response.data ni ax.message', () => {
    expect(scanFiles(UTILS_LIMS_PATHS, LIMS_DOWNLOAD_UNSAFE_PATTERNS)).toEqual([]);
  });
});
