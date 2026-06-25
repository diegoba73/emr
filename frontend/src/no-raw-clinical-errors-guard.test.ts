import fs from 'fs';
import path from 'path';

const FRONTEND_SRC = path.join(__dirname);

/** QA-FE-ERR-01 — flujos clínicos: sin errores backend crudos en mensajes visibles. */
const SCOPED_PATHS = [
  'components/TurnoModal.tsx',
  'pages/Solicitudes.tsx',
  'pages/Pacientes.tsx',
  'services/apiService.ts',
  'utils/csrf.ts',
];

const DANGEROUS_PATTERNS: Array<{ name: string; pattern: RegExp }> = [
  { name: 'alert(error', pattern: /alert\s*\(\s*error\b/ },
  { name: 'alert((error', pattern: /alert\s*\(\s*\(\s*error\b/ },
  { name: 'alert(error.response', pattern: /alert\s*\([^)]*error\.response/ },
  { name: 'response?.data?.error', pattern: /response\?\.data\?\.error/ },
  { name: 'response?.data?.detail', pattern: /response\?\.data\?\.detail/ },
  { name: 'response?.data?.message', pattern: /response\?\.data\?\.message/ },
  { name: 'response.data.error', pattern: /response\.data\.error/ },
  { name: 'response.data.detail', pattern: /response\.data\.detail/ },
  { name: 'response.data.message', pattern: /response\.data\.message/ },
  { name: 'err.response?.data', pattern: /err\.response\?\.data/ },
  { name: 'error.response?.data', pattern: /error\.response\?\.data/ },
  { name: 'syncError?.response', pattern: /syncError\?\.response/ },
  { name: 'error.message en alert', pattern: /alert\s*\([^)]*error\.message/ },
  { name: 'throw new Error(error.message', pattern: /throw\s+new\s+Error\s*\(\s*error\.message/ },
];

function collectInternacionFiles(): string[] {
  const dir = path.join(FRONTEND_SRC, 'components/internacion');
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((name) => name.endsWith('.tsx') && !name.endsWith('.test.tsx'))
    .map((name) => `components/internacion/${name}`);
}

describe('QA-FE-ERR-01 — sin errores backend crudos en UI clínica focal', () => {
  it('archivos del alcance no exponen response.data ni error.message en feedback visible', () => {
    const targets = [...SCOPED_PATHS, ...collectInternacionFiles()];
    const offenders: string[] = [];

    for (const relativePath of targets) {
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
