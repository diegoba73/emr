/**
 * Tipos LIMS nativo (/api/lab/...). No mezclar con solicitudes EMR (solicitudes.Solicitud).
 */

export type EstadoSolicitudLims = 'PENDIENTE' | 'EN_PROCESO' | 'INFORMADO_PARCIAL' | 'FINALIZADO';

export type OrigenSolicitudLims =
  | 'INTERNACION_UCO'
  | 'INTERNACION_UCE'
  | 'GUARDIA'
  | 'AMBULATORIO_CEHTA'
  | 'AMBULATORIO_ICPL'
  | 'EXTERNO_CEHTA'
  | 'EXTERNO_ICPL';

export type EstadoMuestraLims =
  | 'PENDIENTE_TOMA'
  | 'TOMADA'
  | 'RECIBIDA'
  | 'EN_PROCESO'
  | 'RECHAZADA'
  | 'CONSERVADA'
  | 'DESCARTADA'
  | 'CANCELADA';

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** Catálogo tipo muestra (GET /lab/muestras/) */
export interface LimsTipoMuestra {
  id: number;
  codigo: string;
  nombre: string;
  color_tubo?: string;
  activo?: boolean;
}

/** Catálogo tipo examen (GET /lab/examenes/) */
export interface LimsTipoExamen {
  id: number;
  codigo: string;
  nombre: string;
  abreviatura?: string;
  tipo_muestra_requerida: number;
  tipo_muestra_nombre?: string;
  tipo_muestra_codigo?: string;
  /** B2-B: obligatoriedad progresiva en carga de resultados (lectura API catálogo). */
  requiere_muestra?: boolean;
  metodo?: string;
  unidad_default?: string;
  tipo_resultado?: 'TEXTO' | 'NUMERICO' | 'CUALITATIVO';
  modo_entrada?: 'ESTANDAR' | 'TICKET_ENTERO' | 'FORMULA_PORCENTAJE';
  ticket_decimales?: number;
  multiplicador_clinico?: string | number;
  formato_informe_entrada?: 'decimal1' | 'integer' | 'absolute_int' | 'absolute_millions' | '';
  precio?: string;
  rango_referencia_texto?: string;
  rango_min?: string | null;
  rango_max?: string | null;
  activo?: boolean;
}

/** Body POST/PATCH catálogo exámenes LIMS */
export type TipoExamenLimsWriteBody = {
  codigo?: string;
  nombre?: string;
  abreviatura?: string;
  tipo_muestra_requerida?: number;
  tipo_resultado?: 'TEXTO' | 'NUMERICO' | 'CUALITATIVO';
  metodo?: string;
  unidad_default?: string;
  modo_entrada?: 'ESTANDAR' | 'TICKET_ENTERO' | 'FORMULA_PORCENTAJE';
  ticket_decimales?: number;
  multiplicador_clinico?: string | number;
  formato_informe_entrada?: LimsTipoExamen['formato_informe_entrada'];
  rango_referencia_texto?: string;
  rango_min?: string | number | null;
  rango_max?: string | number | null;
  requiere_muestra?: boolean;
  activo?: boolean;
};

/** Resumen de panel en lectura de orden (agrupación de resultados). */
export interface LimsPanelResumen {
  id: number;
  codigo: string;
  nombre: string;
  tipos_examen_ids: number[];
}

export type ProcedenciaOrdenLims = 'RECURSO' | 'INTERNACION' | null;
export interface LimsPanelExamen {
  id: number;
  codigo: string;
  nombre: string;
  tipos_examen?: number[];
  tipos_examen_nombres?: string[];
  activo?: boolean;
}

/** Catálogo contenedor (GET /lab/contenedores/) */
export interface LimsTipoContenedor {
  id: number;
  codigo: string;
  nombre: string;
  descripcion?: string;
  color?: string;
  volumen_ml?: number | null;
  aditivo?: string;
  activo?: boolean;
}

export interface ResultadoExamenLims {
  id: number;
  solicitud: number;
  tipo_examen: number;
  tipo_examen_nombre?: string;
  tipo_examen_codigo?: string;
  tipo_examen_rango_referencia?: string;
  valor_obtenido: string;
  valor_numerico?: string | number | null;
  unidad?: string;
  rango_referencia_snapshot?: string;
  rango_min_snapshot?: string | number | null;
  rango_max_snapshot?: string | number | null;
  es_patologico?: boolean;
  es_critico?: boolean;
  valor_critico_min_snapshot?: string | number | null;
  valor_critico_max_snapshot?: string | number | null;
  validado_por?: number | null;
  validado_por_nombre?: string | null;
  fecha_validacion?: string | null;
  observaciones?: string;
  muestra_id?: number | null;
  muestra_estado?: string | null;
  tipo_muestra_nombre?: string | null;
  /** Código del tipo de muestra requerida por el examen (catálogo). */
  tipo_examen_muestra_codigo?: string | null;
}

export interface SolicitudExamenLims {
  id: number;
  numero: string | null;
  paciente: number;
  paciente_nombre?: string;
  paciente_dni?: string;
  paciente_email?: string | null;
  paciente_telefono?: string | null;
  medico_interno: number | null;
  medico_interno_nombre?: string | null;
  medico_externo_nombre?: string | null;
  medico_display?: string;
  origen_solicitud: OrigenSolicitudLims;
  origen_solicitud_display?: string;
  tipos_examen?: number[];
  tipos_examen_nombres?: string[];
  paneles?: number[];
  paneles_nombres?: string[];
  paneles_resumen?: LimsPanelResumen[];
  /** Claves panel-{id} / resultado-{id} para orden en informe PDF. */
  orden_grupos_informe?: string[];
  procedencia_tipo?: ProcedenciaOrdenLims;
  procedencia_display?: string | null;
  estado: EstadoSolicitudLims;
  fecha_solicitud: string;
  /** Última fecha de toma física (anotación en listado). */
  fecha_toma_muestra?: string | null;
  fecha_entrega_prometida?: string | null;
  observaciones?: string;
  fecha_informe_enviado?: string | null;
  informe_enviado_email?: boolean;
  informe_enviado_whatsapp?: boolean;
  resultados?: ResultadoExamenLims[];
}

export interface EnvioInformeLimsResultado {
  email_enviado: boolean;
  email_destino?: string | null;
  email_adjunto_pdf?: boolean;
  whatsapp_enviado: boolean;
  whatsapp_telefono?: string | null;
  whatsapp_enlace?: string | null;
  whatsapp_pdf_adjunto?: boolean;
  informe_enlace_descarga?: string | null;
  advertencias?: string[];
}

export interface EnviarInformeOrdenResponse extends SolicitudExamenLims {
  envio?: EnvioInformeLimsResultado;
}

export interface MuestraEventoLims {
  id: number;
  accion: string;
  estado_anterior?: string;
  estado_nuevo?: string;
  actor?: number | null;
  fecha?: string;
  observaciones?: string;
}

export interface MuestraTransaccional {
  id: number;
  codigo_barra: string | null;
  solicitud: number;
  paciente: number;
  tipo_muestra: number;
  tipo_contenedor?: number | null;
  estado: EstadoMuestraLims;
  fecha_toma?: string | null;
  fecha_recepcion?: string | null;
  fecha_rechazo?: string | null;
  motivo_rechazo?: string;
  ubicacion_actual?: string;
  observaciones?: string;
  created_at?: string;
  updated_at?: string;
  eventos?: MuestraEventoLims[];
}

/** Payload por ítem en POST cargar-resultados (retrocompatible con UI-1). */
export interface CargarResultadoPayload {
  id: number;
  valor: string;
  /** Entero del ticket Sysmex (sin decimal); el backend convierte a valor clínico. */
  valor_sysmex?: string;
  muestra_id?: number | null;
  valor_numerico?: number | string | null;
  unidad?: string;
  es_patologico?: boolean;
  es_critico?: boolean;
  observaciones?: string;
}

/** @deprecated Alias — usar CargarResultadoPayload */
export type CargaResultadoItemPayload = CargarResultadoPayload;

// --- Microbiología LIMS (B3.x) ---

export type EstadoEstudioMicrobiologia =
  | 'PENDIENTE'
  | 'RECIBIDO'
  | 'SEMBRADO'
  | 'LECTURA_PRELIMINAR'
  | 'IDENTIFICACION'
  | 'ANTIBIOGRAMA'
  | 'LISTO_PARA_VALIDAR'
  | 'VALIDADO'
  | 'INFORMADO'
  | 'CANCELADO';

/** Estados que bloquean mutaciones técnicas (B3-frontend-validación-A). */
export const ESTADOS_MICRO_CERRADOS_OPERACION: readonly EstadoEstudioMicrobiologia[] = [
  'CANCELADO',
  'VALIDADO',
  'INFORMADO',
];

export type TipoEstudioMicrobiologia =
  | 'CULTIVO_RUTINA'
  | 'UROCULTIVO'
  | 'HEMOCULTIVO'
  | 'COPROCULTIVO'
  | 'CULTIVO_HERIDA'
  | 'OTRO';

export type EstadoAisladoMicrobiologico = 'SOSPECHADO' | 'IDENTIFICADO' | 'DESCARTADO';

export type SignificanciaAislado =
  | 'NO_DEFINIDA'
  | 'CONTAMINANTE'
  | 'FLORA_HABITUAL'
  | 'SIGNIFICATIVO'
  | 'CRITICO';

export type CrecimientoLectura =
  | 'PENDIENTE'
  | 'SIN_DESARROLLO'
  | 'ESCASO'
  | 'MODERADO'
  | 'ABUNDANTE'
  | 'MIXTO';

export type EstadoAntibiograma = 'PENDIENTE' | 'EN_PROCESO' | 'COMPLETO' | 'CANCELADO';

export type InterpretacionAntibiotico = 'S' | 'I' | 'R' | 'SDD' | 'NO_APLICA';

export type TipoInformeMicrobiologia = 'PRELIMINAR' | 'FINAL';

export type EstadoInformeMicrobiologia = 'BORRADOR' | 'EMITIDO' | 'VALIDADO' | 'ANULADO';

export interface MedioCultivo {
  id: number;
  codigo: string;
  nombre: string;
  tipo?: string;
  descripcion?: string;
  activo?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface EstudioMicrobiologia {
  id: number;
  numero?: string | null;
  solicitud: number;
  muestra: number;
  paciente: number;
  tipo_estudio: TipoEstudioMicrobiologia | string;
  estado: EstadoEstudioMicrobiologia;
  observaciones?: string;
  fecha_inicio?: string | null;
  fecha_cierre?: string | null;
  responsable?: number | null;
  cancelado_por?: number | null;
  fecha_cancelacion?: string | null;
  motivo_cancelacion?: string;
  created_at?: string;
  updated_at?: string;
}

export interface SiembraMicrobiologia {
  id: number;
  estudio: number;
  muestra: number;
  medio: number;
  fecha_siembra?: string;
  sembrado_por?: number | null;
  condicion_incubacion?: string;
  temperatura_c?: string | number | null;
  atmosfera?: string;
  observaciones?: string;
  estado?: string;
  created_at?: string;
  updated_at?: string;
}

export interface LecturaCultivo {
  id: number;
  siembra: number;
  estudio: number;
  fecha_lectura?: string;
  leido_por?: number | null;
  horas_incubacion?: number | null;
  crecimiento?: CrecimientoLectura | string;
  descripcion_colonias?: string;
  tincion_gram?: string;
  observaciones?: string;
  es_preliminar?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Microorganismo {
  id: number;
  codigo: string;
  nombre: string;
  genero?: string;
  especie?: string;
  grupo?: string;
  descripcion?: string;
  activo?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface AisladoMicrobiologico {
  id: number;
  estudio: number;
  lectura_origen: number;
  microorganismo?: number | null;
  estado: EstadoAisladoMicrobiologico;
  descripcion?: string;
  cantidad?: string;
  significancia?: SignificanciaAislado | string;
  requiere_antibiograma?: boolean;
  observaciones?: string;
  creado_por?: number | null;
  descartado_por?: number | null;
  fecha_descarte?: string | null;
  motivo_descarte?: string;
  created_at?: string;
  updated_at?: string;
}

export interface IdentificacionMicroorganismo {
  id: number;
  aislado: number;
  microorganismo: number;
  metodo?: string;
  resultado?: string;
  confianza?: string | number | null;
  fecha?: string | null;
  realizado_por?: number | null;
  observaciones?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Antibiotico {
  id: number;
  codigo: string;
  nombre: string;
  familia?: string;
  descripcion?: string;
  activo?: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Antibiograma {
  id: number;
  aislado: number;
  estado: EstadoAntibiograma;
  metodo?: string;
  fecha_inicio?: string;
  fecha_resultado?: string | null;
  realizado_por?: number | null;
  cancelado_por?: number | null;
  fecha_cancelacion?: string | null;
  motivo_cancelacion?: string;
  observaciones?: string;
  created_at?: string;
  updated_at?: string;
}

export interface ResultadoAntibiotico {
  id: number;
  antibiograma: number;
  antibiotico: number;
  halo_mm?: string | number | null;
  mic?: string;
  interpretacion: InterpretacionAntibiotico | string;
  observaciones?: string;
  created_at?: string;
  updated_at?: string;
}

export interface InformeMicrobiologia {
  id: number;
  estudio: number;
  tipo: TipoInformeMicrobiologia;
  estado: EstadoInformeMicrobiologia;
  texto?: string;
  version?: number;
  emitido_por?: number | null;
  fecha_emision?: string | null;
  validado_por?: number | null;
  fecha_validacion?: string | null;
  reemplaza_a?: number | null;
  observaciones?: string;
  motivo_anulacion?: string;
  anulado_por?: number | null;
  fecha_anulacion?: string | null;
  created_at?: string;
  updated_at?: string;
}

/** Análisis longitudinal Fase 1 — referencia + historial del paciente (sin IA). */
export type VariacionHistorialLims =
  | 'sin_historial'
  | 'estable'
  | 'moderada'
  | 'significativa'
  | 'brusca'
  | 'cambio_cualitativo'
  | 'cambio_valor'
  | 'sin_comparacion_numerica';

export interface AnalisisReferenciaLims {
  tiene_rango: boolean;
  en_rango: boolean | null;
  es_patologico: boolean;
  es_critico: boolean;
  desviacion: 'bajo' | 'alto' | 'normal' | null;
  rango_texto: string;
  rango_min: string | null;
  rango_max: string | null;
}

export interface AnalisisHistorialLims {
  tiene_historial: boolean;
  valor_anterior: string | null;
  valor_numerico_anterior: string | null;
  unidad_anterior: string | null;
  fecha_anterior: string | null;
  solicitud_anterior_id: number | null;
  solicitud_anterior_numero: string | null;
  dias_desde_anterior: number | null;
  delta_absoluto: string | null;
  delta_porcentual: string | null;
  cambio_cualitativo: boolean | null;
  variacion: VariacionHistorialLims;
}

export interface AnalisisResultadoLongitudinalLims {
  resultado_id: number;
  tipo_examen_id: number;
  tipo_examen_codigo: string;
  tipo_examen_nombre: string;
  tipo_resultado: string | null;
  valor_actual: string;
  valor_numerico_actual: string | null;
  unidad: string | null;
  referencia: AnalisisReferenciaLims;
  historial: AnalisisHistorialLims;
  alertas: string[];
}

export interface AnalisisLongitudinalOrden {
  solicitud_id: number;
  solicitud_numero: string | null;
  paciente_id: number;
  fecha_solicitud: string | null;
  estado_solicitud: EstadoSolicitudLims;
  resultados: AnalisisResultadoLongitudinalLims[];
  resumen_alertas: string[];
  total_analizados: number;
  total_con_historial: number;
  total_cambios_significativos: number;
}
