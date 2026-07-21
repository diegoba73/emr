import { createSolicitudExamenLims, formatDrfError } from '../../services/limsApi';
import { createEstudioComplementario } from '../../services/estudiosComplementariosApi';
import { parseEstudiosApiError } from '../estudios/apiErrors';
import type { EstudioModalidad } from '../../types/estudios';

export interface DraftSolicitudLab {
  id: string;
  examenes_ids: number[];
  paneles_ids: number[];
  examenes_labels: string[];
  paneles_labels: string[];
  observaciones?: string;
}

export interface DraftEstudioComplementario {
  id: string;
  tipo_estudio_id?: number;
  modalidad: EstudioModalidad;
  tipo_label: string;
  descripcion_clinica?: string;
}

export interface ConsultaPedidosDraft {
  solicitudesLab: DraftSolicitudLab[];
  estudios: DraftEstudioComplementario[];
}

const emptyDraft = (): ConsultaPedidosDraft => ({
  solicitudesLab: [],
  estudios: [],
});

const GUARDIA_PENDING_KEY = 'guardia-pedidos-pending';

function draftKey(consultaHcId: number): string {
  return `consulta-pedidos-borrador-${consultaHcId}`;
}

export function loadGuardiaPendingDraft(): ConsultaPedidosDraft {
  try {
    const raw = sessionStorage.getItem(GUARDIA_PENDING_KEY);
    if (!raw) return emptyDraft();
    const parsed = JSON.parse(raw) as ConsultaPedidosDraft;
    return {
      solicitudesLab: Array.isArray(parsed.solicitudesLab) ? parsed.solicitudesLab : [],
      estudios: Array.isArray(parsed.estudios) ? parsed.estudios : [],
    };
  } catch {
    return emptyDraft();
  }
}

export function saveGuardiaPendingDraft(draft: ConsultaPedidosDraft): void {
  try {
    sessionStorage.setItem(GUARDIA_PENDING_KEY, JSON.stringify(draft));
  } catch {
    /* storage lleno o privado */
  }
}

export function clearGuardiaPendingDraft(): void {
  try {
    sessionStorage.removeItem(GUARDIA_PENDING_KEY);
  } catch {
    /* nada */
  }
}

/** Traslada el borrador de guardia al consulta HC recién creado. */
export function migrateGuardiaPendingDraftToConsulta(consultaHcId: number): void {
  const pending = loadGuardiaPendingDraft();
  if (pending.solicitudesLab.length === 0 && pending.estudios.length === 0) {
    return;
  }
  saveConsultaPedidosDraft(consultaHcId, pending);
  clearGuardiaPendingDraft();
}

export function countGuardiaPendingDraftItems(): number {
  const pending = loadGuardiaPendingDraft();
  return pending.solicitudesLab.length + pending.estudios.length;
}

export function loadConsultaPedidosDraft(consultaHcId: number): ConsultaPedidosDraft {
  try {
    const raw = sessionStorage.getItem(draftKey(consultaHcId));
    if (!raw) return emptyDraft();
    const parsed = JSON.parse(raw) as ConsultaPedidosDraft;
    return {
      solicitudesLab: Array.isArray(parsed.solicitudesLab) ? parsed.solicitudesLab : [],
      estudios: Array.isArray(parsed.estudios) ? parsed.estudios : [],
    };
  } catch {
    return emptyDraft();
  }
}

export function saveConsultaPedidosDraft(consultaHcId: number, draft: ConsultaPedidosDraft): void {
  try {
    sessionStorage.setItem(draftKey(consultaHcId), JSON.stringify(draft));
  } catch {
    /* storage lleno o privado */
  }
}

export function clearConsultaPedidosDraft(consultaHcId: number): void {
  try {
    sessionStorage.removeItem(draftKey(consultaHcId));
  } catch {
    /* nada */
  }
}

export function newDraftId(): string {
  return `draft-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export interface FlushConsultaPedidosParams {
  consultaHcId: number;
  pacienteId: number;
  medicoId?: number | null;
  /** Origen clínico explícito (p. ej. guardia walk-in en ICPL). */
  origenSolicitud?: 'GUARDIA';
}

/** Persiste borradores en LIMS / estudios complementarios. Lanza si alguna creación falla. */
export async function flushConsultaPedidosDrafts(
  params: FlushConsultaPedidosParams,
  draftOverride?: ConsultaPedidosDraft
): Promise<void> {
  const { consultaHcId, pacienteId, medicoId, origenSolicitud } = params;
  const draft = draftOverride ?? loadConsultaPedidosDraft(consultaHcId);
  if (draft.solicitudesLab.length === 0 && draft.estudios.length === 0) {
    return;
  }

  const errors: string[] = [];

  for (const sol of draft.solicitudesLab) {
    try {
      await createSolicitudExamenLims({
        paciente_id: pacienteId,
        medico_id: medicoId ?? undefined,
        consulta_hc_id: consultaHcId,
        examenes_ids: sol.examenes_ids,
        paneles_ids: sol.paneles_ids,
        observaciones: sol.observaciones,
        origen_solicitud: origenSolicitud,
      });
    } catch (e) {
      errors.push(formatDrfError(e));
    }
  }

  for (const est of draft.estudios) {
    try {
      await createEstudioComplementario({
        paciente_id: pacienteId,
        modalidad: est.modalidad,
        tipo_estudio: est.tipo_estudio_id,
        consulta_hc: consultaHcId,
        medico_solicitante: medicoId ?? undefined,
        descripcion_clinica: est.descripcion_clinica ?? '',
        origen: 'INTERNO',
      });
    } catch (e) {
      errors.push(parseEstudiosApiError(e, 'No se pudo registrar un estudio complementario.'));
    }
  }

  if (errors.length > 0) {
    throw new Error(errors.join(' · '));
  }

  clearConsultaPedidosDraft(consultaHcId);
}
