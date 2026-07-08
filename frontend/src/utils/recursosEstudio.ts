/**
 * Recursos agendables para estudios complementarios (salas de procedimiento / hemodinamia).
 */
import type { AxiosResponse } from 'axios';
import type { ApiResponse, Recurso } from '../types';
import { apiClient as api, API_BASE_URL } from '../services/apiClient';

const TIPOS_RECURSO_ESTUDIO = ['SALA_PROCEDIMIENTO', 'SALA_HEMODINAMIA'] as const;

type RecursosApiPayload = Recurso[] | ApiResponse<Recurso>;

function normalizeApiPath(url: string): string {
  if (!url) return '';
  if (url.startsWith('/') && !url.startsWith('/api/')) return url;
  if (url.startsWith(`${API_BASE_URL}/`)) {
    return url.replace(API_BASE_URL, '') || '/';
  }
  if (url.startsWith('/api/')) return url.replace(/^\/api/, '') || '/';
  return url;
}

function parseRecursosPage(data: RecursosApiPayload): { items: Recurso[]; next: string | null } {
  if (Array.isArray(data)) {
    return { items: data, next: null };
  }
  return {
    items: data.results ?? [],
    next: data.next ? normalizeApiPath(data.next) : null,
  };
}

async function fetchRecursosByTipo(tipo: string): Promise<Recurso[]> {
  const items: Recurso[] = [];
  let path: string | null = `/recursos/?tipo_recurso=${encodeURIComponent(tipo)}&page_size=200`;

  while (path) {
    const currentPath = path;
    const response: AxiosResponse<RecursosApiPayload> = await api.get(currentPath);
    const page = parseRecursosPage(response.data);
    items.push(...page.items);
    path = page.next;
  }

  return items;
}

/** Salas activas aptas para turnos de estudios complementarios. */
export async function listRecursosEstudioAgenda(): Promise<Recurso[]> {
  const batches = await Promise.all(TIPOS_RECURSO_ESTUDIO.map((t) => fetchRecursosByTipo(t)));
  const byId = new Map<number, Recurso>();
  for (const batch of batches) {
    for (const r of batch) {
      if (r.activo !== false) {
        byId.set(r.id, r);
      }
    }
  }
  return Array.from(byId.values()).sort((a, b) =>
    a.nombre.localeCompare(b.nombre, 'es', { sensitivity: 'base' })
  );
}

export { TIPOS_RECURSO_ESTUDIO };

export function isRecursoEstudioAgenda(tipo: string | undefined | null): boolean {
  return tipo != null && (TIPOS_RECURSO_ESTUDIO as readonly string[]).includes(tipo);
}

export function isTurnoEstudio(turno: {
  estudio_complementario?: { id?: number } | null;
  recurso?: { tipo_recurso?: string } | null;
  motivo_reserva?: string;
}): boolean {
  if (turno.estudio_complementario?.id) return true;
  return (
    isRecursoEstudioAgenda(turno.recurso?.tipo_recurso) &&
    Boolean(turno.motivo_reserva?.startsWith('Estudio:'))
  );
}
