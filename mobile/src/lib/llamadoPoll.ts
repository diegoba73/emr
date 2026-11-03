import { api } from './api';
import { handleLlamadoForeground } from './notifications';

export type LlamadoActivo = {
  activo: boolean;
  llegada_id?: number;
  destino?: string;
  tipo?: string;
  /** ISO: cambia cada vez que el médico vuelve a pulsar Llamar. */
  llamado_en?: string | null;
};

/** Consulta si el médico ya llamó (LAN, sin Expo Push). */
export async function fetchLlamadoActivo(): Promise<LlamadoActivo> {
  return api<LlamadoActivo>('/llamado-activo/');
}

function claveLlamado(data: LlamadoActivo): string | null {
  if (!data.activo || !data.llegada_id) return null;
  return `${data.llegada_id}:${data.llamado_en || ''}`;
}

/**
 * Polling mientras la app esté abierta.
 * Un «Ya voy» silencia ese llamado; un nuevo Llamar del médico (nuevo llamado_en) vuelve a alertar.
 */
export function startLlamadoPolling(opts: {
  enabled: boolean;
  intervalMs?: number;
}): () => void {
  if (!opts.enabled) return () => undefined;
  const intervalMs = opts.intervalMs ?? 4000;
  let lastAlertedKey: string | null = null;
  let stopped = false;

  const tick = async () => {
    if (stopped) return;
    try {
      const data = await fetchLlamadoActivo();
      const key = claveLlamado(data);
      if (!key) return;
      if (key === lastAlertedKey) return;
      lastAlertedKey = key;
      handleLlamadoForeground(
        { tipo: data.tipo || 'llamado_medico', destino: data.destino || '' },
        data.destino ? `Te llaman. Andá a ${data.destino}.` : undefined
      );
    } catch {
      /* red / sesión: reintentar en el próximo tick */
    }
  };

  void tick();
  const id = setInterval(() => void tick(), intervalMs);
  return () => {
    stopped = true;
    clearInterval(id);
  };
}
