/** Tipos — Estudios complementarios EMR (C6.4.2), alineados a serializers backend. */

export type EstudioEstado =
  | 'SOLICITADO'
  | 'CONFIRMADO'
  | 'REALIZADO'
  | 'INFORMADO'
  | 'VALIDADO'
  | 'ENTREGADO'
  | 'ANULADO';

/** A2/C/D — ESTUDIO, PROCEDIMIENTO y CIRUGIA habilitados; multi off. */
export type TipoActividadEstudio = 'ESTUDIO' | 'PROCEDIMIENTO' | 'CIRUGIA';

export type ClasificacionQuirurgicaSnapshot = 'NO_QUIRURGICO' | 'QUIRURGICO';

export type InformeEstado = 'BORRADOR' | 'EMITIDO' | 'VALIDADO' | 'ANULADO';

/** Códigos legacy (IMAGEN_*) o slugs CEHTA (p.ej. ECOGRAFIA_RENAL). */
export type EstudioPractica = string;

/** @deprecated Use EstudioPractica */
export type EstudioModalidad = EstudioPractica;

export interface TipoEstudioComplementario {
  id: number;
  codigo?: string | null;
  nombre: string;
  descripcion?: string;
  practica: EstudioPractica;
  requiere_informe?: boolean;
  activo?: boolean;
}

export interface EstudioComplementario {
  id: number;
  paciente_id: number;
  paciente_nombre?: string | null;
  tipo_estudio?: number | null;
  tipo_estudio_nombre?: string | null;
  estudio_diagnostico?: number | null;
  practica?: EstudioPractica | null;
  /** A2/C/D: ESTUDIO | PROCEDIMIENTO | CIRUGIA. */
  tipo_actividad?: TipoActividadEstudio;
  procedimiento_catalogo?: number | null;
  procedimiento_catalogo_nombre?: string | null;
  cirugia_especialidad?: number | null;
  cirugia_especialidad_nombre?: string | null;
  cirugia_especialidad_snapshot?: string | null;
  cirugia_procedimiento?: number | null;
  cirugia_procedimiento_nombre?: string | null;
  cirugia_procedimiento_snapshot?: string | null;
  cirugia_abordaje?: number | null;
  cirugia_abordaje_nombre?: string | null;
  cirugia_abordaje_snapshot?: string | null;
  clasificacion_quirurgica_snapshot?: ClasificacionQuirurgicaSnapshot | null;
  /** A2: siempre false hasta A3/A4. */
  permite_multi_sesion?: boolean;
  estado: EstudioEstado;
  medico_solicitante?: number | null;
  medico_solicitante_nombre?: string | null;
  anestesista_previsto?: number | null;
  anestesista_previsto_nombre?: string | null;
  realizado_por?: number | null;
  realizado_por_nombre?: string | null;
  cerrado_por?: number | null;
  fecha_cierre?: string | null;
  protocolo_cierre_informe?: number | null;
  atencion?: number | null;
  consulta_hc?: number | null;
  solicitud_emr?: number | null;
  fecha_solicitud?: string | null;
  fecha_realizacion?: string | null;
  centro_realizador?: string | null;
  origen?: string;
  descripcion_clinica?: string;
  accession_number?: string | null;
  study_instance_uid?: string | null;
  pacs_metadata?: Record<string, unknown>;
  motivo_anulacion?: string;
  turno_id?: number | null;
  turno_fecha_hora_inicio?: string | null;
  turno_fecha_hora_fin?: string | null;
  turno_recurso_id?: number | null;
  turno_recurso_nombre?: string | null;
  turno_estado?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ArchivoEstudioComplementario {
  id: number;
  archivo_medico_id: number;
  titulo?: string | null;
  tipo_archivo?: string | null;
  archivo_nombre?: string | null;
  tipo_rol: string;
  descripcion?: string;
  orden?: number;
  es_principal?: boolean;
  download_url?: string;
  created_at?: string;
}

export interface InformeEstudioComplementario {
  id: number;
  version: number;
  estado: InformeEstado;
  tipo?: 'PRELIMINAR' | 'FINAL';
  texto?: string;
  es_vigente: boolean;
  informado_por?: number | null;
  fecha_informe?: string | null;
  validado_por?: number | null;
  fecha_validacion?: string | null;
  reemplaza_a?: number | null;
  motivo_rectificacion?: string;
  created_at?: string;
  updated_at?: string;
}

/** POST create — incluye paciente; sin estado (lo fija el backend). */
export interface CreateEstudioComplementarioPayload {
  paciente_id: number;
  practica?: EstudioPractica;
  tipo_estudio?: number | null;
  estudio_diagnostico?: number | null;
  tipo_actividad?: TipoActividadEstudio;
  procedimiento_catalogo?: number | null;
  cirugia_especialidad?: number | null;
  cirugia_procedimiento?: number | null;
  cirugia_abordaje?: number | null;
  medico_solicitante?: number | null;
  anestesista_previsto?: number | null;
  origen?: string;
  descripcion_clinica?: string;
  fecha_solicitud?: string | null;
  fecha_realizacion?: string | null;
  centro_realizador?: string;
  atencion?: number | null;
  consulta_hc?: number | null;
  solicitud_emr?: number | null;
}

export interface CirugiaEspecialidadCatalogo {
  id: number;
  nombre: string;
  activo?: boolean;
  orden?: number;
}

export interface CirugiaProcedimientoCatalogo {
  id: number;
  especialidad: number;
  especialidad_nombre?: string;
  nombre: string;
  activo?: boolean;
}

export interface CirugiaAbordajeCatalogo {
  id: number;
  procedimiento: number;
  procedimiento_nombre?: string;
  nombre: string;
  activo?: boolean;
}

export interface MarcarRealizadoEstudioPayload {
  profesional_id?: number | null;
  anestesista_id?: number | null;
  diagnostico_preoperatorio?: string | null;
  recurso_id?: number | null;
  fecha_realizacion?: string | null;
}

/**
 * PATCH metadata — alineado a EstudioComplementarioDetailSerializer (C6.4.2-A).
 * Sin paciente_id, paciente, estado ni campos de auditoría/archivos/informes.
 */
export interface UpdateEstudioComplementarioPayload {
  practica?: EstudioPractica;
  tipo_estudio?: number | null;
  estudio_diagnostico?: number | null;
  medico_solicitante?: number | null;
  atencion?: number | null;
  consulta_hc?: number | null;
  solicitud_emr?: number | null;
  fecha_solicitud?: string | null;
  fecha_realizacion?: string | null;
  centro_realizador?: string;
  origen?: string;
  descripcion_clinica?: string;
  accession_number?: string | null;
  study_instance_uid?: string | null;
  pacs_metadata?: Record<string, unknown>;
}

export interface AgendarTurnoEstudioDesdeAgendaPayload {
  paciente_id: number;
  recurso_id: number;
  fecha_hora_inicio: string;
  fecha_hora_fin: string;
  estudio_id?: number | null;
  tipo_estudio?: number | null;
  practica?: EstudioPractica;
  origen?: string;
  descripcion_clinica?: string;
  medico_id?: number | null;
}

export interface AsignarTurnoEstudioPayload {
  recurso_id: number;
  fecha_hora_inicio: string;
  fecha_hora_fin: string;
  medico_id?: number | null;
}

export interface ReprogramarTurnoEstudioPayload {
  recurso_id: number;
  fecha_hora_inicio: string;
  fecha_hora_fin: string;
  motivo: string;
  medico_id?: number | null;
}

export interface AgregarArchivoEstudioPayload {
  archivo_medico_id: number;
  tipo_rol?: string;
  descripcion?: string;
  orden?: number;
  es_principal?: boolean;
}

export interface SubirArchivoEstudioPayload {
  archivo: File;
  titulo?: string;
  tipo_archivo?: string;
  tipo_rol?: string;
  descripcion?: string;
  orden?: number;
  es_principal?: boolean;
}
