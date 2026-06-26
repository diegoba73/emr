import fs from 'fs';
import path from 'path';

const FRONTEND_SRC = path.join(__dirname);

/** QA-FE-ERR-02 — sin PHI/PII en alerts visibles ni errores crudos en callers de MotivoDialog. */

const SOLICITUDES_PATH = 'pages/Solicitudes.tsx';

const PHI_ALERT_PATTERNS: Array<{ name: string; pattern: RegExp }> = [
  { name: 'alert con solicitud.id', pattern: /alert\s*\([^)]*\$\{[^}]*solicitud\.id/ },
  { name: 'alert con paciente.nombre', pattern: /alert\s*\([^)]*\$\{[^}]*paciente\.(nombre|apellido)/ },
  { name: 'alert con paciente interpolado', pattern: /alert\s*\([^)]*\$\{[^}]*paciente[^}]*\}/ },
  { name: 'alert con solicitud.estado', pattern: /alert\s*\([^)]*\$\{[^}]*solicitud\.estado/ },
  { name: 'alert con solicitud.descripcion', pattern: /alert\s*\([^)]*\$\{[^}]*solicitud\.descripcion/ },
  { name: 'alert con descripcion', pattern: /alert\s*\([^)]*\$\{[^}]*descripcion/ },
  { name: 'alert con response.data', pattern: /alert\s*\([^)]*response\.data/ },
  { name: 'alert con error.message', pattern: /alert\s*\([^)]*error\.message/ },
  { name: 'toast con solicitud.id', pattern: /toast\.(error|success|info)\([^)]*\$\{[^}]*solicitud\.id/ },
  { name: 'setError con solicitud.id', pattern: /setError\s*\([^)]*\$\{[^}]*solicitud\.id/ },
  { name: 'setSuccess con paciente', pattern: /setSuccess\s*\([^)]*\$\{[^}]*paciente/ },
  { name: 'JSON.stringify en alert', pattern: /alert\s*\([^)]*JSON\.stringify/ },
];

const MOTIVO_DIALOG_CALLER_PATHS = [
  'components/TurnoModal.tsx',
  'components/lims/micro/AisladosIdentificacionPanel.tsx',
  'components/lims/micro/InformesMicrobiologiaPanel.tsx',
  'components/lims/micro/AntibiogramaPanel.tsx',
  'pages/laboratorio/MicrobiologiaEstudioDetalle.tsx',
];

const RAW_MOTIVO_ERROR_PATTERNS: Array<{ name: string; pattern: RegExp }> = [
  { name: 'throw new Error(formatDrfError', pattern: /throw\s+new\s+Error\s*\(\s*formatDrfError/ },
  { name: 'throw new Error(error.message', pattern: /throw\s+new\s+Error\s*\(\s*error\.message/ },
  { name: 'throw new Error(err.message', pattern: /throw\s+new\s+Error\s*\(\s*err\.message/ },
  { name: 'throw new Error(error.response', pattern: /throw\s+new\s+Error\s*\(\s*error\.response/ },
  { name: 'throw new Error(err.response', pattern: /throw\s+new\s+Error\s*\(\s*err\.response/ },
  { name: 'throw new Error(response.data', pattern: /throw\s+new\s+Error\s*\(\s*response\.data/ },
  { name: 'throw new Error(JSON.stringify', pattern: /throw\s+new\s+Error\s*\(\s*JSON\.stringify/ },
  {
    name: 'formatDrfError propagado a MotivoDialog',
    pattern: /formatDrfError\s*\([^)]+\)[\s\S]{0,120}throw\s+new\s+Error\s*\(\s*msg\s*\)/,
  },
];

describe('QA-FE-ERR-02 — sin PHI/PII en alerts de Solicitudes ni errores crudos en MotivoDialog callers', () => {
  it('Solicitudes.tsx no interpola datos clínicos en mensajes visibles', () => {
    const fullPath = path.join(FRONTEND_SRC, SOLICITUDES_PATH);
    const content = fs.readFileSync(fullPath, 'utf8');
    const offenders: string[] = [];

    for (const { name, pattern } of PHI_ALERT_PATTERNS) {
      if (pattern.test(content)) {
        offenders.push(`${SOLICITUDES_PATH} → ${name}`);
      }
    }

    expect(offenders).toEqual([]);
  });

  it('callers de MotivoDialog no propagan mensajes backend crudos', () => {
    const offenders: string[] = [];

    for (const relativePath of MOTIVO_DIALOG_CALLER_PATHS) {
      const fullPath = path.join(FRONTEND_SRC, relativePath);
      const content = fs.readFileSync(fullPath, 'utf8');

      for (const { name, pattern } of RAW_MOTIVO_ERROR_PATTERNS) {
        if (pattern.test(content)) {
          offenders.push(`${relativePath} → ${name}`);
        }
      }
    }

    expect(offenders).toEqual([]);
  });
});
