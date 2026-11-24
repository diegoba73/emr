import { useEffect, useRef } from 'react';

export const TURNOS_LIVE_EVENT = 'synesis:turnos-changed';
export const TURNOS_LIVE_CHANNEL = 'synesis-turnos';

/** Fallback de refetch completo cuando no hay getRevision (legado / vistas sin stamp). */
export const TURNOS_LIVE_INTERVAL_MS = 8000;

/** Intervalo del poll de revisión (fase híbrida multi-secretaría). */
export const TURNOS_REVISION_INTERVAL_MS = 1000;

/**
 * Refresco periódico + al volver a la pestaña/ventana + evento local/BroadcastChannel.
 * Solo dispara si `document.visibilityState === 'visible'` (salvo el callback inicial opcional).
 *
 * Fase híbrida: si se pasa `getRevision`, el intervalo corto solo consulta el stamp
 * y ejecuta `refresh` cuando cambia (evita refetch completo cada tick). Sin WebSockets.
 */
export function useLiveRefresh(
  refresh: () => void | Promise<void>,
  options?: {
    enabled?: boolean;
    intervalMs?: number;
    /** Escuchar mutaciones locales / otras pestañas del mismo browser. */
    listenTurnosEvents?: boolean;
    /** Ejecutar un refresh al montar (default false; las pantallas suelen cargar solas). */
    refreshOnMount?: boolean;
    /**
     * Stamp liviano (p. ej. GET /api/turnos/revision/).
     * Si está definido, el poll usa revisionIntervalMs y solo refresca al cambiar.
     */
    getRevision?: () => Promise<string | null | undefined>;
    revisionIntervalMs?: number;
  }
): void {
  const {
    enabled = true,
    intervalMs = TURNOS_LIVE_INTERVAL_MS,
    listenTurnosEvents = true,
    refreshOnMount = false,
    getRevision,
    revisionIntervalMs = TURNOS_REVISION_INTERVAL_MS,
  } = options || {};

  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  const getRevisionRef = useRef(getRevision);
  getRevisionRef.current = getRevision;
  const inFlight = useRef(false);
  const lastRevision = useRef<string | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const runRefresh = () => {
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') {
        return;
      }
      if (inFlight.current) return;
      inFlight.current = true;
      Promise.resolve(refreshRef.current())
        .catch(() => {
          /* el caller ya maneja errores de UI */
        })
        .finally(() => {
          inFlight.current = false;
        });
    };

    const runRevisionCheck = () => {
      if (typeof document !== 'undefined' && document.visibilityState !== 'visible') {
        return;
      }
      const getter = getRevisionRef.current;
      if (!getter) {
        runRefresh();
        return;
      }
      if (inFlight.current) return;
      inFlight.current = true;
      Promise.resolve(getter())
        .then((rev) => {
          const next = rev == null ? null : String(rev);
          if (lastRevision.current === null) {
            lastRevision.current = next;
            return;
          }
          if (next !== lastRevision.current) {
            lastRevision.current = next;
            return Promise.resolve(refreshRef.current());
          }
        })
        .catch(() => {
          /* silencioso: el próximo tick reintenta */
        })
        .finally(() => {
          inFlight.current = false;
        });
    };

    const onVisibleOrFocus = () => {
      if (document.visibilityState !== 'visible') return;
      if (getRevisionRef.current) {
        runRevisionCheck();
      } else {
        runRefresh();
      }
    };

    if (refreshOnMount) {
      if (getRevision) {
        runRevisionCheck();
      } else {
        runRefresh();
      }
    }

    document.addEventListener('visibilitychange', onVisibleOrFocus);
    window.addEventListener('focus', onVisibleOrFocus);
    const tickMs = getRevision ? revisionIntervalMs : intervalMs;
    const id = window.setInterval(getRevision ? runRevisionCheck : runRefresh, tickMs);

    let channel: BroadcastChannel | null = null;
    const onLocalEvent = () => runRefresh();
    if (listenTurnosEvents) {
      window.addEventListener(TURNOS_LIVE_EVENT, onLocalEvent);
      try {
        channel = new BroadcastChannel(TURNOS_LIVE_CHANNEL);
        channel.onmessage = () => runRefresh();
      } catch {
        channel = null;
      }
    }

    return () => {
      document.removeEventListener('visibilitychange', onVisibleOrFocus);
      window.removeEventListener('focus', onVisibleOrFocus);
      window.clearInterval(id);
      if (listenTurnosEvents) {
        window.removeEventListener(TURNOS_LIVE_EVENT, onLocalEvent);
      }
      channel?.close();
    };
  }, [enabled, intervalMs, listenTurnosEvents, refreshOnMount, getRevision, revisionIntervalMs]);
}

/** Avisar a otras vistas/pestañas tras crear/editar/cancelar un turno en este cliente. */
export function notifyTurnosChanged(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(TURNOS_LIVE_EVENT));
  try {
    const channel = new BroadcastChannel(TURNOS_LIVE_CHANNEL);
    channel.postMessage({ type: 'invalidate', at: Date.now() });
    channel.close();
  } catch {
    /* BroadcastChannel no disponible */
  }
}
