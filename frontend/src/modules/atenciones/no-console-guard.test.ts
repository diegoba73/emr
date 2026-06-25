import fs from 'fs';
import path from 'path';

const MODULE_ROOT = path.join(__dirname);

function collectSourceFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...collectSourceFiles(fullPath));
      continue;
    }
    if (/\.(ts|tsx)$/.test(entry.name) && !entry.name.endsWith('.test.ts') && !entry.name.endsWith('.test.tsx')) {
      files.push(fullPath);
    }
  }
  return files;
}

describe('atenciones — sin logs clínicos en consola', () => {
  it('no contiene console.log/error/warn en el módulo', () => {
    const offenders: string[] = [];
    const pattern = /console\.(log|error|warn)\s*\(/;

    for (const file of collectSourceFiles(MODULE_ROOT)) {
      const content = fs.readFileSync(file, 'utf8');
      if (pattern.test(content)) {
        offenders.push(path.relative(MODULE_ROOT, file));
      }
    }

    expect(offenders).toEqual([]);
  });
});
