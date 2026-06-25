import fs from 'fs';
import path from 'path';

const FRONTEND_SRC = path.join(__dirname);

/** QA-FE-LOGS-02 — vistas con datos clínicos fuera del módulo Atenciones. */
const CLINICAL_VIEW_FILES = [
  'components/PatientIntegratedView.tsx',
  'pages/Turnos.tsx',
];

const CONSOLE_PATTERN = /console\.(log|error|warn|info|debug|trace)\s*\(/;

describe('QA-FE-LOGS-02 — sin console.* clínico en vistas', () => {
  it('PatientIntegratedView y Turnos no usan console.*', () => {
    const offenders: string[] = [];

    for (const relativePath of CLINICAL_VIEW_FILES) {
      const fullPath = path.join(FRONTEND_SRC, relativePath);
      const content = fs.readFileSync(fullPath, 'utf8');
      if (CONSOLE_PATTERN.test(content)) {
        offenders.push(relativePath);
      }
    }

    expect(offenders).toEqual([]);
  });
});
