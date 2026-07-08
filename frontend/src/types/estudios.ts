/** Tipos — Estudios complementarios EMR (C6.4.2), alineados a serializers backend. */

export type EstudioEstado =
  | 'SOLICITADO'
  | 'CONFIRMADO'
  | 'REALIZADO'
  | 'INFORMADO'
  | 'VALIDADO'
  | 'ENTREGADO'
  | 'ANULADO';

export type InformeEstado = 'BORRADOR' | 'EMITIDO' | 'VALIDADO' | 'ANULADO';

export type EstudioModalidad =
  | 'IMAGEN_RX'
  | 'IMAGEN_TC'
  | 'IMAGEN_RM'
  | 'IMAGEN_US'
  | 'PDF_INFORME_EXTERNO'
  | 'OTRO';

export interface TipoEstudioComplementario {
  id: number;
  codigo?: string | null;
  nombre: string;
  descripcion?: string;
  modalidad: EstudioModalidad;
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
  modalidad: EstudioModalidad;
  estado: EstudioEstado;
  medico_solicitante?: number | null;
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
  turno_recurso_nombre?: string | null;
  turno_estado?: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface ArchivoEstudioComplementario {
  id: number;
  archivo_medico_id: number;
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
  modalidad: EstudioModalidad;
  tipo_estudio?: number | null;
  estudio_diagnostico?: number | null;
  origen?: string;
  descripcion_clinica?: string;
  fecha_solicitud?: string | null;
  fecha_realizacion?: string | null;
  centro_realizador?: string;
  medico_solicitante?: number | null;
  atencion?: number | null;
  consulta_hc?: number | null;
  solicitud_emr?: number | null;
}

/**
 * PATCH metadata — alineado a EstudioComplementarioDetailSerializer (C6.4.2-A).
 * Sin paciente_id, paciente, estado ni campos de auditoría/archivos/informes.
 */
export interface UpdateEstudioComplementarioPayload {
  modalidad?: EstudioModalidad;
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
  modalidad?: EstudioModalidad;
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

export interface AgregarArchivoEstudioPayload {
  archivo_medico_id: number;
  tipo_rol?: string;
  descripcion?: string;
  orden?: number;
  es_principal?: boolean;
}
