import fs from 'fs';
import path from 'path';

const FRONTEND_SRC = path.join(__dirname);

/** QA-FE-LOGS-03 — módulos frontend con datos clínicos/LIMS sensibles. */
const SCOPED_PATHS = [
  'services/apiService.ts',
  'components/TurnoModal.tsx',
  'pages/Solicitudes.tsx',
  'pages/Pacientes.tsx',
  'utils/csrf.ts',
];

const CONSOLE_PATTERN = /console\.(log|error|warn|info|debug|trace)\s*\(/;

function collectInternacionFiles(): string[] {
  const dir = path.join(FRONTEND_SRC, 'components/internacion');
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((name) => name.endsWith('.tsx') && !name.endsWith('.test.tsx'))
    .map((name) => `components/internacion/${name}`);
}

describe('QA-FE-LOGS-03 — sin console.* en módulos focales', () => {
  it('archivos sensibles no usan console.*', () => {
    const targets = [...SCOPED_PATHS, ...collectInternacionFiles()];
    const offenders: string[] = [];

    for (const relativePath of targets) {
      const fullPath = path.join(FRONTEND_SRC, relativePath);
      const content = fs.readFileSync(fullPath, 'utf8');
      if (CONSOLE_PATTERN.test(content)) {
        offenders.push(relativePath);
      }
    }

    expect(offenders).toEqual([]);
  });
});
