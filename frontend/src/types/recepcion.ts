export type PuestoModo = 'TODO' | 'REGLAS';

export type TipoActividadRecepcion =
  | 'CONSULTA'
  | 'ESTUDIO'
  | 'PROCEDIMIENTO'
  | 'CIRUGIA'
  | 'EXTRACCION'
  | 'SIN_TURNO'
  | '';

export type EstadoFlujoRecepcion =
  | 'PROGRAMADO'
  | 'EN_ESPERA_RECEPCION'
  | 'EN_ESPERA'
  | 'LLAMADO'
  | 'EN_ATENCION'
  | 'ATENDIDO'
  | 'NO_ASISTIO'
  | 'CANCELADO';

export interface PuestoRecepcion {
  id: number;
  codigo: string;
  nombre: string;
  etiqueta_paciente?: string;
  label_publico?: string;
  activo: boolean;
  modo: PuestoModo;
  es_fallback: boolean;
  orden: number;
  ubicacion?: string | null;
}

export interface ReglaRuteoRecepcion {
  id: number;
  puesto: number;
  puesto_nombre?: string;
  nombre?: string;
  prioridad: number;
  activo: boolean;
  tipo_actividad: TipoActividadRecepcion;
  tipo_recurso?: string;
  recurso?: number | null;
  medico?: number | null;
}

export interface CoberturaRecepcion {
  id: number;
  usuario: number;
  usuario_nombre?: string;
  fecha: string;
  puesto: number;
  puesto_nombre?: string;
  puesto_label?: string;
  tipos: string[];
  sede?: string | null;
}

export interface CoberturaHoyPayload {
  fecha: string;
  cobertura: CoberturaRecepcion | null;
  puestos_disponibles: PuestoRecepcion[];
  tipos_disponibles: string[];
}

export interface PrioridadHorarioRecepcion {
  codigo: 'EN_HORARIO' | 'ANTICIPADO' | 'TARDE' | 'SIN_TURNO' | string;
  label: string;
  detalle: string;
  es_prioridad: boolean;
  hora_turno?: string | null;
  minutos?: number | null;
}

export interface LlegadaRecepcion {
  id: number;
  paciente: number;
  paciente_nombre?: string;
  paciente_nombre_publico?: string;
  paciente_dni?: string;
  puesto: number;
  puesto_nombre?: string;
  puesto_label?: string;
  turno?: number | null;
  turno_inicio?: string | null;
  tipo_actividad: TipoActividadRecepcion;
  estado_flujo: EstadoFlujoRecepcion;
  fecha: string;
  checkin_en?: string | null;
  llamado_en?: string | null;
  destino_recurso?: number | null;
  destino_label?: string;
  destino?: string;
  medico_nombre?: string;
  notas?: string;
  numero_orden_dia?: number | null;
  prefijo_llamado?: string;
  codigo_llamado?: string;
  zona_llamado?: string;
  mensaje_paciente?: string | null;
  prioridad?: PrioridadHorarioRecepcion;
}

export interface TurnoPendienteCheckin {
  turno_id: number;
  paciente_id: number;
  paciente_nombre: string;
  paciente_dni?: string;
  medico_nombre?: string;
  recurso_nombre?: string;
  tipo_actividad: string;
  inicio: string;
  estado: string;
  puesto_sugerido_id: number;
  puesto_sugerido_label: string;
  mensaje: string;
}

export interface TableroRecepcion {
  fecha: string;
  llegadas: LlegadaRecepcion[];
  turnos_pendientes_checkin: TurnoPendienteCheckin[];
}

export interface PantallaLlamadoItem {
  id: number;
  paciente_nombre_publico: string;
  tipo_actividad: string;
  destino: string;
  numero_orden_dia?: number | null;
  codigo_llamado?: string;
  prefijo_llamado?: string;
  zona_llamado?: string;
  estado_flujo?: string;
  llamado_en?: string | null;
  puesto_id?: number;
  puesto_label?: string;
}

export interface PantallaMitad {
  /** Paciente en LLAMADO más reciente (bloque grande). */
  actual: PantallaLlamadoItem | null;
  /** Todos los que siguen en LLAMADO (más reciente primero). */
  llamando?: PantallaLlamadoItem[];
  /** Otros LLAMADO además del grande. */
  otros_llamando?: PantallaLlamadoItem[];
  /** Siguiente en cola (debajo del grande). */
  proximo?: PantallaLlamadoItem | null;
  /** Recién atendidos (arriba, chicos). */
  historial: PantallaLlamadoItem[];
  pendientes: PantallaLlamadoItem[];
}

export interface PantallaSalaPayload {
  mitad_recepcion: PantallaMitad;
  mitad_medico: PantallaMitad;
  llamados: PantallaLlamadoItem[];
}

export type KioscoPrioridad = PrioridadHorarioRecepcion;

export interface KioscoCheckinResult {
  ok: boolean;
  modo: 'turno' | 'walkin';
  mensaje: string;
  puesto: string;
  destino?: string;
  numero_orden_dia?: number | null;
  codigo_llamado?: string;
  prefijo_llamado?: string;
  tipo_actividad?: string;
  llegada_id?: number;
  prioridad?: PrioridadHorarioRecepcion;
  token_espera?: string;
  espera_path?: string;
  /** Origen LAN preferido para el QR (sin depender de Internet/dominio público). */
  espera_origin?: string;
  espera_url?: string;
  espera_origen_fuente?: string;
  espera_es_lan?: boolean;
}

export interface KioscoConfig {
  ok: boolean;
  espera_origin: string;
  /** Canónica: siempre `{origin}/kiosco-recepcion` (nunca APK). */
  anuncio_url?: string;
  espera_origins?: string[];
  lan_ips?: string[];
  fuente: string;
  es_lan: boolean;
}

export interface EsperaPacienteEstado {
  ok: boolean;
  estado_flujo: string;
  llamado: boolean;
  finalizado: boolean;
  titulo: string;
  detalle: string;
  puesto: string;
  destino?: string;
  numero_orden_dia?: number | null;
  codigo_llamado?: string;
  prefijo_llamado?: string;
  prioridad?: PrioridadHorarioRecepcion;
  llamado_en?: string | null;
  paciente_nombre_publico?: string;
}
