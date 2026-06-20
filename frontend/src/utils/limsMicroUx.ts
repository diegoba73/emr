/**
 * UX microbiología LIMS — helpers puros (sin PHI en logs).
 */
import type { LimsTipoContenedor, LimsTipoMuestra, MuestraTransaccional, SolicitudExamenLims } from '../types/lims';
import {
  MUESTRA_ESTADOS_PROCESABLES,
  filterMuestrasProcesables,
  isMuestraProcesable,
} from './limsCargaMuestra';

/** Muestras vinculables a EstudioMicrobiologia (misma regla que carga resultados B2-C). */
export const MUESTRAS_ESTADOS_PROCESABLES_MICRO = MUESTRA_ESTADOS_PROCESABLES;

export function filterMuestrasProcesablesMicro(muestras: MuestraTransaccional[]): MuestraTransaccional[] {
  return filterMuestrasProcesables(muestras);
}

export function isMuestraProcesableMicro(estado: string): boolean {
  return isMuestraProcesable(estado);
}

export function formatSolicitudMicroLabel(s: SolicitudExamenLims): string {
  const num = s.numero ? ` · ${s.numero}` : '';
  const pac = s.paciente_nombre ? ` · ${s.paciente_nombre}` : '';
  return `#${s.id}${num}${pac} · ${s.estado}`;
}

export function formatMuestraTransaccionalMicroLabel(
  m: MuestraTransaccional,
  tipos: Map<number, LimsTipoMuestra>,
  contenedores: Map<number, LimsTipoContenedor>
): string {
  const tipo = tipos.get(m.tipo_muestra);
  const tipoLabel = tipo ? tipo.nombre || tipo.codigo : `tipo#${m.tipo_muestra}`;
  const cont =
    m.tipo_contenedor != null
      ? contenedores.get(m.tipo_contenedor)?.nombre || contenedores.get(m.tipo_contenedor)?.codigo || `cont#${m.tipo_contenedor}`
      : '—';
  return `#${m.id} · ${tipoLabel} · ${cont} · ${m.estado}`;
}

export function validateCrearEstudioMicroSelection(
  solicitudId: number | '',
  muestraId: number | ''
): string | null {
  if (solicitudId === '' || !solicitudId) return 'Seleccione una solicitud LIMS.';
  if (muestraId === '' || !muestraId) return 'Seleccione una muestra transaccional procesable.';
  return null;
}
