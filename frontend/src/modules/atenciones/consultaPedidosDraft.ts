import toast from 'react-hot-toast';
import { createSolicitudExamenLims, formatDrfError, getOrdenAbiertaPaciente } from '../../services/limsApi';
import { createEstudiosMicrobiologiaBatch } from '../../services/limsMicroApi';
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

export interface DraftPedidoMicroItem {
  tipo_cultivo_id: number;
  tipo_muestra_micro_id: number;
  cultivo_nombre: string;
  muestra_nombre: string;
}

export interface DraftPedidoMicro {
  id: string;
  items: DraftPedidoMicroItem[];
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
  solicitudesMicro: DraftPedidoMicro[];
  estudios: DraftEstudioComplementario[];
}

const emptyDraft = (): ConsultaPedidosDraft => ({
  solicitudesLab: [],
  solicitudesMicro: [],
  estudios: [],
});

function normalizeDraft(parsed: Partial<ConsultaPedidosDraft>): ConsultaPedidosDraft {
  return {
    solicitudesLab: Array.isArray(parsed.solicitudesLab) ? parsed.solicitudesLab : [],
    solicitudesMicro: Array.isArray(parsed.solicitudesMicro) ? parsed.solicitudesMicro : [],
    estudios: Array.isArray(parsed.estudios) ? parsed.estudios : [],
  };
}

const GUARDIA_PENDING_KEY = 'guardia-pedidos-pending';

function draftKey(consultaHcId: number): string {
  return `consulta-pedidos-borrador-${consultaHcId}`;
}

export function loadGuardiaPendingDraft(): ConsultaPedidosDraft {
  try {
    const raw = sessionStorage.getItem(GUARDIA_PENDING_KEY);
    if (!raw) return emptyDraft();
    return normalizeDraft(JSON.parse(raw) as ConsultaPedidosDraft);
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
  if (
    pending.solicitudesLab.length === 0 &&
    pending.solicitudesMicro.length === 0 &&
    pending.estudios.length === 0
  ) {
    return;
  }
  saveConsultaPedidosDraft(consultaHcId, pending);
  clearGuardiaPendingDraft();
}

export function countGuardiaPendingDraftItems(): number {
  const pending = loadGuardiaPendingDraft();
  return (
    pending.solicitudesLab.length +
    pending.solicitudesMicro.length +
    pending.estudios.length
  );
}

export function loadConsultaPedidosDraft(consultaHcId: number): ConsultaPedidosDraft {
  try {
    const raw = sessionStorage.getItem(draftKey(consultaHcId));
    if (!raw) return emptyDraft();
    return normalizeDraft(JSON.parse(raw) as ConsultaPedidosDraft);
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

/** Persiste borradores en LIMS / micro / estudios complementarios. Lanza si alguna creación falla. */
export async function flushConsultaPedidosDrafts(
  params: FlushConsultaPedidosParams,
  draftOverride?: ConsultaPedidosDraft
): Promise<void> {
  const { consultaHcId, pacienteId, medicoId, origenSolicitud } = params;
  const draft = draftOverride ?? loadConsultaPedidosDraft(consultaHcId);
  if (
    draft.solicitudesLab.length === 0 &&
    draft.solicitudesMicro.length === 0 &&
    draft.estudios.length === 0
  ) {
    return;
  }

  if (draft.solicitudesLab.length > 0) {
    try {
      const abierta = await getOrdenAbiertaPaciente(pacienteId);
      if (abierta) {
        const ok = window.confirm(
          `Ya hay una orden solicitada (${abierta.numero || `#${abierta.id}`}) pendiente de toma. ` +
            'Los exámenes de laboratorio se agregarán a esa orden. ¿Continuar?'
        );
        if (!ok) {
          throw new Error('Pedido de laboratorio cancelado: ya existe una orden abierta.');
        }
      }
    } catch (e) {
      if (e instanceof Error && e.message.startsWith('Pedido de laboratorio cancelado')) {
        throw e;
      }
      /* si falla el check, seguimos */
    }
  }

  const errors: string[] = [];
  const remaining: ConsultaPedidosDraft = {
    solicitudesLab: [],
    solicitudesMicro: [],
    estudios: [],
  };

  for (const sol of draft.solicitudesLab) {
    try {
      const orden = await createSolicitudExamenLims({
        paciente_id: pacienteId,
        medico_id: medicoId ?? undefined,
        consulta_hc_id: consultaHcId,
        examenes_ids: sol.examenes_ids,
        paneles_ids: sol.paneles_ids,
        observaciones: sol.observaciones,
        origen_solicitud: origenSolicitud,
      });
      if (orden.merged) {
        toast.success(
          `Exámenes agregados a la orden ${orden.numero || `#${orden.id}`} (aún pendiente de toma).`
        );
      }
    } catch (e) {
      errors.push(`Lab. clínico: ${formatDrfError(e)}`);
      remaining.solicitudesLab.push(sol);
    }
  }

  for (const micro of draft.solicitudesMicro) {
    try {
      const items = (micro.items || []).filter(
        (i) => i.tipo_cultivo_id && i.tipo_muestra_micro_id
      );
      if (items.length === 0) {
        throw new Error('Pedido de microbiología sin cultivos/muestras válidos.');
      }
      const estudios = await createEstudiosMicrobiologiaBatch({
        paciente_id: pacienteId,
        medico_id: medicoId ?? null,
        consulta_hc_id: consultaHcId,
        origen_solicitud: origenSolicitud,
        observaciones: micro.observaciones,
        items: items.map((i) => ({
          tipo_cultivo_id: i.tipo_cultivo_id,
          tipo_muestra_micro_id: i.tipo_muestra_micro_id,
        })),
      });
      toast.success(
        estudios.length === 1
          ? `Pedido micro ${estudios[0].numero || `#${estudios[0].id}`} creado.`
          : `${estudios.length} pedidos de microbiología creados.`
      );
    } catch (e) {
      errors.push(`Microbiología: ${formatDrfError(e)}`);
      remaining.solicitudesMicro.push(micro);
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
      errors.push(
        `Estudio: ${parseEstudiosApiError(e, 'No se pudo registrar un estudio complementario.')}`
      );
      remaining.estudios.push(est);
    }
  }

  if (errors.length > 0) {
    // Conservar solo lo que falló para poder reintentar al guardar de nuevo.
    saveConsultaPedidosDraft(consultaHcId, remaining);
    throw new Error(errors.join(' · '));
  }

  clearConsultaPedidosDraft(consultaHcId);
}
