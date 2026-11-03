/**
 * Base URL del API según dónde se abrió el SPA.
 * En LAN (tablet/secretaría/celular) usa la misma IP del host + puerto API.
 */

function isPrivateLanHost(hostname: string): boolean {
  const h = (hostname || '').toLowerCase();
  if (!h || h === 'localhost' || h === '127.0.0.1') return false;
  if (h.startsWith('10.') || h.startsWith('192.168.')) return true;
  const m = /^172\.(\d+)\./.exec(h);
  if (m) {
    const n = Number(m[1]);
    return n >= 16 && n <= 31 && n !== 17;
  }
  return false;
}

export function resolveApiBaseUrl(): string {
  const env = (process.env.REACT_APP_API_URL || '').replace(/\/$/, '');
  if (env && (env.startsWith('/') || env.startsWith('http'))) {
    // Ruta relativa (/api) o URL absoluta no-localhost: respetar
    if (env.startsWith('/')) return env;
    try {
      const u = new URL(env);
      if (!isPrivateLanHost(u.hostname) && u.hostname !== 'localhost' && u.hostname !== '127.0.0.1') {
        return env;
      }
      // env apunta a localhost: si estamos en LAN, preferir host actual
    } catch {
      return env || 'http://localhost:8000/api';
    }
  }

  if (typeof window !== 'undefined' && window.location?.hostname) {
    const { protocol, hostname } = window.location;
    if (isPrivateLanHost(hostname)) {
      const apiPort = process.env.REACT_APP_API_PORT || '8000';
      return `${protocol}//${hostname}:${apiPort}/api`;
    }
  }

  return env || 'http://localhost:8000/api';
}
