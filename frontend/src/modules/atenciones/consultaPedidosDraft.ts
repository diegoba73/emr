import toast from 'react-hot-toast';
import {
  createPedidoCompletoLims,
  formatDrfError,
  type ItemImpresionOrden,
} from '../../services/limsApi';
import { createEstudioComplementario } from '../../services/estudiosComplementariosApi';
import { parseEstudiosApiError } from '../estudios/apiErrors';
import type { EstudioPractica } from '../../types/estudios';

export interface DraftSolicitudLab {
  id: string;
  examenes_ids: number[];
  paneles_ids: number[];
  examenes_labels: string[];
  paneles_labels: string[];
  observaciones?: string;
  /** YYYY-MM-DD */
  fecha_programada_toma: string;
  /** Código material (SANGRE, ORINA…). Vacío si ambulatorio unificado. */
  material_pedido: string;
  /** Ambulatorio: materiales del bucket unidos en un solo pedido. */
  materiales_unificados?: string[];
}

export interface DraftPedidoMicroItem {
  tipo_cultivo_id: number;
  tipo_muestra_micro_id: number;
  cultivo_nombre: string;
  muestra_nombre: string;
  /** Material de pedido del bloque UI (anti-dup ASPIRADO). */
  material_pedido?: string;
}

export interface DraftPedidoMicro {
  id: string;
  items: DraftPedidoMicroItem[];
  observaciones?: string;
  /** YYYY-MM-DD */
  fecha_programada_toma: string;
  material_pedido?: string;
}

export interface DraftEstudioComplementario {
  id: string;
  tipo_estudio_id?: number;
  practica: EstudioPractica;
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
  const hoy = new Date();
  const yyyy = hoy.getFullYear();
  const mm = String(hoy.getMonth() + 1).padStart(2, '0');
  const dd = String(hoy.getDate()).padStart(2, '0');
  const fallbackFecha = `${yyyy}-${mm}-${dd}`;
  return {
    solicitudesLab: (Array.isArray(parsed.solicitudesLab) ? parsed.solicitudesLab : []).map(
      (s) => ({
        ...s,
        fecha_programada_toma: s.fecha_programada_toma || fallbackFecha,
        material_pedido: (s.material_pedido || '').toUpperCase(),
        materiales_unificados: Array.isArray(s.materiales_unificados)
          ? s.materiales_unificados.map((m) => (m || '').toUpperCase()).filter(Boolean)
          : undefined,
      })
    ),
    solicitudesMicro: (Array.isArray(parsed.solicitudesMicro) ? parsed.solicitudesMicro : []).map(
      (s) => ({
        ...s,
        fecha_programada_toma: s.fecha_programada_toma || fallbackFecha,
        material_pedido: (s.material_pedido || '').toUpperCase() || undefined,
      })
    ),
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

export function countConsultaPedidosDraftItems(draft: ConsultaPedidosDraft): number {
  return (
    draft.solicitudesLab.length +
    (draft.solicitudesMicro?.length || 0) +
    draft.estudios.length
  );
}

/** Traslada el borrador de guardia al consulta HC recién creado. */
export function migrateGuardiaPendingDraftToConsulta(
  consultaHcId: number,
  draftOverride?: ConsultaPedidosDraft
): void {
  const pending = draftOverride ?? loadGuardiaPendingDraft();
  if (countConsultaPedidosDraftItems(pending) === 0) {
    return;
  }
  saveConsultaPedidosDraft(consultaHcId, pending);
  clearGuardiaPendingDraft();
}

export function countGuardiaPendingDraftItems(): number {
  return countConsultaPedidosDraftItems(loadGuardiaPendingDraft());
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

export interface FlushConsultaPedidosResult {
  /** Órdenes lab/micro creadas — para impresión papel institucional. */
  pedidosPapel: ItemImpresionOrden[];
}

function pushPedidoUnique(
  dest: ItemImpresionOrden[],
  item: ItemImpresionOrden
): void {
  if (dest.some((x) => x.tipo === item.tipo && x.id === item.id)) return;
  dest.push(item);
}

/**
 * Persiste borradores LIMS/micro de forma atómica (pedidos-completos).
 * Estudios complementarios siguen por su API. Lanza si falla; borrador intacto.
 */
export async function flushConsultaPedidosDrafts(
  params: FlushConsultaPedidosParams,
  draftOverride?: ConsultaPedidosDraft
): Promise<FlushConsultaPedidosResult> {
  const { consultaHcId, pacienteId, medicoId, origenSolicitud } = params;
  const draft = draftOverride ?? loadConsultaPedidosDraft(consultaHcId);
  const pedidosPapel: ItemImpresionOrden[] = [];
  if (
    draft.solicitudesLab.length === 0 &&
    draft.solicitudesMicro.length === 0 &&
    draft.estudios.length === 0
  ) {
    return { pedidosPapel };
  }

  const hasLims =
    draft.solicitudesLab.length > 0 || draft.solicitudesMicro.length > 0;

  if (hasLims) {
    const fechas = new Set(
      [
        ...draft.solicitudesLab.map((s) => s.fecha_programada_toma),
        ...draft.solicitudesMicro.map((s) => s.fecha_programada_toma),
      ].filter(Boolean)
    );
    if (fechas.size > 1) {
      throw new Error(
        'El borrador mezcla fechas de extracción distintas. Separá los pedidos por día.'
      );
    }
    const fecha =
      draft.solicitudesLab[0]?.fecha_programada_toma ||
      draft.solicitudesMicro[0]?.fecha_programada_toma;
    if (!fecha) {
      throw new Error('Indicá el día de la extracción en el pedido.');
    }

    const solicitudes_lab = draft.solicitudesLab.map((sol) => {
      const mat = (sol.material_pedido || '').toUpperCase();
      const uni = (sol.materiales_unificados || [])
        .map((m) => (m || '').toUpperCase())
        .filter(Boolean);
      if (!mat && uni.length < 2) {
        throw new Error('Cada pedido clínico debe tener material_pedido.');
      }
      return {
        material_pedido: mat,
        examenes_ids: sol.examenes_ids,
        paneles_ids: sol.paneles_ids,
        observaciones: sol.observaciones,
        ...(uni.length >= 2 ? { materiales_unificados: uni } : {}),
      };
    });

    const estudios_micro: Array<{
      material_pedido: string;
      tipo_cultivo_id: number;
      tipo_muestra_micro_id: number;
      observaciones?: string;
    }> = [];
    for (const micro of draft.solicitudesMicro) {
      const items = (micro.items || []).filter(
        (i) => i.tipo_cultivo_id && i.tipo_muestra_micro_id
      );
      if (items.length === 0) {
        throw new Error('Pedido de microbiología sin cultivos/muestras válidos.');
      }
      for (const i of items) {
        const mat = (
          i.material_pedido ||
          micro.material_pedido ||
          ''
        ).toUpperCase();
        if (!mat) {
          throw new Error(
            'Cada estudio de microbiología debe tener material_pedido.'
          );
        }
        estudios_micro.push({
          material_pedido: mat,
          tipo_cultivo_id: i.tipo_cultivo_id,
          tipo_muestra_micro_id: i.tipo_muestra_micro_id,
          observaciones: micro.observaciones,
        });
      }
    }

    const idempotencyKey =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? `consulta-${consultaHcId}-${crypto.randomUUID()}`
        : `consulta-${consultaHcId}-${Date.now()}-${Math.random().toString(36).slice(2)}`;

    try {
      const result = await createPedidoCompletoLims(
        {
          paciente_id: pacienteId,
          medico_id: medicoId ?? undefined,
          consulta_hc_id: consultaHcId,
          origen_solicitud: origenSolicitud,
          fecha_programada_toma: fecha,
          solicitudes_lab,
          estudios_micro,
        },
        { idempotencyKey }
      );
      for (const p of result.pedidos || []) {
        pushPedidoUnique(pedidosPapel, { tipo: p.tipo, id: p.id });
      }
      const nLab = result.solicitudes_ids?.length || 0;
      const nMicro = result.estudios_micro_ids?.length || 0;
      if (nLab || nMicro) {
        toast.success(
          [
            nLab ? `${nLab} orden(es) lab.` : null,
            nMicro ? `${nMicro} estudio(s) micro` : null,
          ]
            .filter(Boolean)
            .join(' · ') + ' creados.'
        );
      }
    } catch (e) {
      // Conservar borrador íntegro (sin flush parcial).
      throw new Error(`Laboratorio: ${formatDrfError(e)}`);
    }
  }

  const errors: string[] = [];
  const remainingEstudios: DraftEstudioComplementario[] = [];

  for (const est of draft.estudios) {
    try {
      await createEstudioComplementario({
        paciente_id: pacienteId,
        practica: est.practica,
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
      remainingEstudios.push(est);
    }
  }

  if (errors.length > 0) {
    // LIMS ya persistió: conservar solo estudios fallidos.
    saveConsultaPedidosDraft(consultaHcId, {
      solicitudesLab: [],
      solicitudesMicro: [],
      estudios: remainingEstudios,
    });
    throw new Error(errors.join(' · '));
  }

  clearConsultaPedidosDraft(consultaHcId);
  return { pedidosPapel };
}
