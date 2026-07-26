/**
 * UX microbiología — helpers (sin PHI en logs).
 */
import type {
  LimsTipoContenedor,
  LimsTipoMuestra,
  MuestraTransaccional,
  SolicitudExamenLims,
  TipoMuestraMicrobiologia,
} from '../types/lims';
import {
  MUESTRA_ESTADOS_PROCESABLES,
  filterMuestrasProcesables,
  isMuestraProcesable,
} from './limsCargaMuestra';

/** Muestras vinculables (misma regla que carga resultados B2-C). */
export const MUESTRAS_ESTADOS_PROCESABLES_MICRO = MUESTRA_ESTADOS_PROCESABLES;

/** Estados que el backend acepta al iniciar micro con muestra LIMS legado. */
export const MUESTRA_ESTADOS_VALIDOS_INICIAR_MICRO = [
  'RECIBIDA',
  'CONSERVADA',
  'EN_PROCESO',
] as const;

export function filterMuestrasProcesablesMicro(
  muestras: MuestraTransaccional[]
): MuestraTransaccional[] {
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
      ? contenedores.get(m.tipo_contenedor)?.nombre ||
        contenedores.get(m.tipo_contenedor)?.codigo ||
        `cont#${m.tipo_contenedor}`
      : '—';
  return `#${m.id} · ${tipoLabel} · ${cont} · ${m.estado}`;
}

/** @deprecated Preferir validateCrearEstudioMicroPedido. */
export function validateCrearEstudioMicroSelection(
  solicitudId: number | '',
  muestraId: number | ''
): string | null {
  if (solicitudId === '' || !solicitudId) return 'Seleccione una solicitud LIMS.';
  if (muestraId === '' || !muestraId) return 'Seleccione una muestra procesable.';
  return null;
}

/** Sugerencias de muestra según código de cultivo. */
const SUGERENCIA_MUESTRA_POR_CULTIVO: Record<string, string[]> = {
  HEMOCULTIVO: ['sangre'],
  CATETER: ['cateter'],
  PUNTA_CATETER: ['cateter'],
  UROCULTIVO: ['orina'],
  COPROCULTIVO: ['materia', 'fecal'],
  LCR: ['lcr'],
  NASOFARINGEO: ['nasal', 'vigilancia', 'hisop'],
  ESPUTO: ['esputo'],
  ASPIRADO_TRAQUEAL_BRONQUIAL: ['aspirado'],
  MINI_BAL: ['bal'],
  VAGINAL: ['genital'],
  URETRAL: ['genital'],
  SGB: ['genital', 'vigilancia'],
  PIEL_PARTES_BLANDAS: ['tejido', 'hisop', 'exudado'],
  HERIDA_ABSCESO: ['pus', 'tejido'],
  MATERIAL_QUIRURGICO: ['tejido', 'dispositivo'],
  BIOPSIA: ['biopsia'],
  TEJIDO: ['tejido'],
  OSEO: ['hueso'],
  LIQUIDO_PERITONEAL: ['liquido'],
  LIQUIDO_PLEURAL: ['liquido'],
  LIQUIDO_SINOVIAL: ['liquido'],
  LIQUIDO_PERICARDICO: ['liquido'],
  VIGILANCIA_EPIDEMIOLOGICA: ['vigilancia', 'hisop'],
  AMBIENTAL: ['hisop', 'dispositivo'],
};

export function sugerirMuestraPorCultivo(
  codigoCultivo: string,
  tipos: TipoMuestraMicrobiologia[]
): TipoMuestraMicrobiologia | null {
  const keys = SUGERENCIA_MUESTRA_POR_CULTIVO[codigoCultivo] || [];
  if (!keys.length) return tipos[0] || null;
  const found = tipos.find((t) => {
    const blob = `${t.codigo || ''} ${t.nombre || ''}`.toLowerCase();
    return keys.some((k) => blob.includes(k.toLowerCase()));
  });
  return found || tipos[0] || null;
}

export function validateCrearEstudioMicroPedido(input: {
  pacienteId?: number | null;
  tipoCultivoId: number | '';
  tipoMuestraId: number | '';
  medicoInternoId?: number | null;
  medicoExterno?: string;
  requiereMedicoExterno?: boolean;
}): string | null {
  if (!input.pacienteId) return 'Seleccioná el paciente.';
  if (input.tipoCultivoId === '' || !input.tipoCultivoId) {
    return 'Seleccioná el tipo de cultivo.';
  }
  if (input.tipoMuestraId === '' || !input.tipoMuestraId) {
    return 'Seleccioná el tipo de muestra.';
  }
  if (input.requiereMedicoExterno && !(input.medicoExterno || '').trim()) {
    return 'Indicá el médico solicitante externo.';
  }
  return null;
}
