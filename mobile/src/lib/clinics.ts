export interface Clinic { code: string; name: string; apiUrl: string; logoUrl?: string }
export function parseClinics(raw: string, allowLocal = false): Clinic[] {
  const entries: unknown = JSON.parse(raw || '[]');
  if (!Array.isArray(entries)) throw new Error('Catálogo de instituciones inválido.');
  const codes = new Set<string>();
  return entries.map(entry => {
    if (!entry || typeof entry !== 'object') throw new Error('Institución inválida.');
    const c = entry as Clinic;
    if (!/^[A-Z0-9_-]{2,40}$/.test(c.code) || codes.has(c.code) || !c.name?.trim()) throw new Error('Código de institución inválido o repetido.');
    const url = new URL(c.apiUrl);
    const privateHost = /^(10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)$/.test(url.hostname);
    if ((url.protocol !== 'https:' && !(allowLocal && url.protocol === 'http:' && privateHost)) || url.username || url.password || url.search || url.hash) throw new Error('Dirección de institución inválida.');
    if (c.logoUrl && new URL(c.logoUrl).protocol !== 'https:') throw new Error('El logo debe usar HTTPS.');
    codes.add(c.code);
    return { code:c.code, name:c.name.trim(), apiUrl:c.apiUrl.replace(/\/$/, ''), logoUrl:c.logoUrl };
  });
}
export function findClinic(clinics: Clinic[], code: string) {
  return clinics.find(c => c.code === code.trim().toUpperCase()) || null;
}
