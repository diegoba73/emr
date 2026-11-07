/** Puerto SPA del kiosco en LAN (mismo default que EMR_KIOSCO_FRONTEND_PORT). */
const KIOSCO_FRONTEND_PORT = '3000';
const KIOSCO_ANUNCIO_PATH = '/kiosco-recepcion';

function normalizeUrl(raw: string): string {
  return raw.trim().replace(/\/$/, '');
}

/** Fuerza path /kiosco-recepcion; descarta .apk u otras rutas. */
function toKioscoAnuncioUrl(raw: string): string {
  const t = normalizeUrl(raw);
  if (!t) return '';
  try {
    const u = new URL(/^https?:\/\//i.test(t) ? t : `http://${t}`);
    return `${u.protocol}//${u.host}${KIOSCO_ANUNCIO_PATH}`;
  } catch {
    return t.endsWith(KIOSCO_ANUNCIO_PATH) ? t : `${t}${KIOSCO_ANUNCIO_PATH}`;
  }
}

function isPrivateLanHost(hostname: string): boolean {
  const h = (hostname || '').toLowerCase();
  if (!h) return false;
  if (h === 'localhost' || h === '127.0.0.1' || h === '::1') return true;
  if (h.startsWith('10.')) return true;
  if (h.startsWith('192.168.')) return true;
  const m = /^172\.(\d+)\./.exec(h);
  if (!m) return false;
  const n = Number(m[1]);
  return n >= 16 && n <= 31;
}

/** Deriva http(s)://host:3000/kiosco-recepcion desde la API móvil en LAN. */
export function deriveKioscoAnuncioUrlFromApi(apiBase: string): string {
  try {
    const url = new URL(apiBase);
    if (!isPrivateLanHost(url.hostname)) return '';
    const port = KIOSCO_FRONTEND_PORT;
    const origin =
      port === '80' || port === '443'
        ? `${url.protocol}//${url.hostname}`
        : `${url.protocol}//${url.hostname}:${port}`;
    return `${origin}/kiosco-recepcion`;
  } catch {
    return '';
  }
}

/**
 * URL del anuncio de llegada (/kiosco-recepcion).
 * Prioridad: EXPO_PUBLIC_KIOSCO_URL → valor del backend → derivar de API LAN.
 */
export function resolveKioscoAnuncioUrl(fromApi?: string | null, apiBase?: string): string {
  const env = normalizeUrl(process.env.EXPO_PUBLIC_KIOSCO_URL || '');
  if (env) return toKioscoAnuncioUrl(env);
  const api = normalizeUrl(fromApi || '');
  if (api) return toKioscoAnuncioUrl(api);
  return deriveKioscoAnuncioUrlFromApi(apiBase || '');
}
