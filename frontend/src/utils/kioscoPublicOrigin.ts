const STORAGE_KEY = 'synesis_kiosco_public_origin';
export const KIOSCO_ANUNCIO_PATH = '/kiosco-recepcion';

function normalizeOrigin(raw: string): string {
  const t = raw.trim().replace(/\/$/, '');
  if (!t) return '';
  const withScheme = /^https?:\/\//i.test(t) ? t : `http://${t}`;
  try {
    const u = new URL(withScheme);
    // Solo origen (scheme+host+port). Evita pegar .../synesis-movil.apk u otras rutas.
    return `${u.protocol}//${u.host}`;
  } catch {
    return withScheme.replace(/\/$/, '');
  }
}

/** URL canónica del anuncio QR: siempre termina en /kiosco-recepcion. */
export function buildKioscoAnuncioUrl(originOrUrl?: string): string {
  const origin = normalizeOrigin(originOrUrl || '');
  if (!origin) return '';
  return `${origin}${KIOSCO_ANUNCIO_PATH}`;
}

export function isLocalHostName(hostname: string): boolean {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1';
}

/** IP privada típica de Wi‑Fi/LAN (dev); no localhost. */
export function isPrivateLanHost(hostname: string): boolean {
  const h = (hostname || '').toLowerCase();
  if (!h || isLocalHostName(h)) return false;
  if (h.startsWith('10.')) return true;
  if (h.startsWith('192.168.')) return true;
  const m = /^172\.(\d+)\./.exec(h);
  if (m) {
    const n = Number(m[1]);
    return n >= 16 && n <= 31 && n !== 17;
  }
  return false;
}

function isUsableKioscoOrigin(origin: string): boolean {
  try {
    const host = new URL(origin).hostname;
    return Boolean(host) && !isLocalHostName(host);
  } catch {
    return false;
  }
}

/** Origen guardado por el operador (override manual del QR). */
export function getStoredKioscoPublicOrigin(): string {
  try {
    return normalizeOrigin(localStorage.getItem(STORAGE_KEY) || '');
  } catch {
    return '';
  }
}

export function setStoredKioscoPublicOrigin(origin: string): void {
  const n = normalizeOrigin(origin);
  try {
    if (n) localStorage.setItem(STORAGE_KEY, n);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

/**
 * Origen para el QR de anuncio.
 * Prioridad: localStorage → origen del API (público o LAN) → location (no localhost) → env.
 * En CEHTA/prod el API debe devolver https://emr.icpueblodeluis.com.ar:8080
 */
export function resolveKioscoPublicOrigin(apiOrigin?: string): string {
  const stored = getStoredKioscoPublicOrigin();
  if (stored && isUsableKioscoOrigin(stored)) return stored;

  const fromApi = normalizeOrigin(apiOrigin || '');
  if (fromApi && isUsableKioscoOrigin(fromApi)) return fromApi;

  if (typeof window !== 'undefined' && window.location?.origin) {
    try {
      if (!isLocalHostName(window.location.hostname)) {
        return window.location.origin;
      }
    } catch {
      /* ignore */
    }
  }

  const env = normalizeOrigin(process.env.REACT_APP_PUBLIC_ORIGIN || '');
  if (env && isUsableKioscoOrigin(env)) return env;

  return stored || fromApi || '';
}

/** True si aún no hay un origen usable (falta config o quedó en localhost). */
export function kioscoOriginNeedsLanFix(origin: string = resolveKioscoPublicOrigin()): boolean {
  if (!origin) return true;
  try {
    return isLocalHostName(new URL(origin).hostname);
  } catch {
    return true;
  }
}
