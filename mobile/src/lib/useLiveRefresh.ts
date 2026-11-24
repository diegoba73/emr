import { useEffect, useRef } from 'react';
import { AppState, type AppStateStatus } from 'react-native';

/** Fallback de refetch completo cuando no hay getRevision. */
export const TURNOS_LIVE_INTERVAL_MS = 8000;

/** Intervalo del poll de revisión (fase híbrida; alineado al web). */
export const TURNOS_REVISION_INTERVAL_MS = 1000;

/**
 * Near-realtime: polling mientras la pantalla está montada y la app en foreground.
 * Con `getRevision`, solo refresca cuando cambia el stamp (sin WebSockets).
 */
export function useLiveRefresh(
  refresh: () => void | Promise<void>,
  options?: {
    enabled?: boolean;
    intervalMs?: number;
    getRevision?: () => Promise<string | null | undefined>;
    revisionIntervalMs?: number;
  }
): void {
  const {
    enabled = true,
    intervalMs = TURNOS_LIVE_INTERVAL_MS,
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
      if (AppState.currentState !== 'active') return;
      if (inFlight.current) return;
      inFlight.current = true;
      Promise.resolve(refreshRef.current())
        .catch(() => undefined)
        .finally(() => {
          inFlight.current = false;
        });
    };

    const runRevisionCheck = () => {
      if (AppState.currentState !== 'active') return;
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
        .catch(() => undefined)
        .finally(() => {
          inFlight.current = false;
        });
    };

    const onAppState = (next: AppStateStatus) => {
      if (next !== 'active') return;
      if (getRevisionRef.current) runRevisionCheck();
      else runRefresh();
    };

    const sub = AppState.addEventListener('change', onAppState);
    const tickMs = getRevision ? revisionIntervalMs : intervalMs;
    const id = setInterval(getRevision ? runRevisionCheck : runRefresh, tickMs);
    return () => {
      sub.remove();
      clearInterval(id);
    };
  }, [enabled, intervalMs, getRevision, revisionIntervalMs]);
}
