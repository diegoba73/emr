export type RolMovil =
  | 'paciente'
  | 'medico'
  | 'secretaria'
  | 'laboratorio'
  | 'bioquimico';

export type ContextoLab = 'GUARDIA' | 'AMBULATORIO' | 'INTERNACION';

export interface Perfil {
  id: number;
  nombre: string;
  rol: RolMovil;
  medico_id: number | null;
  paciente_id: number | null;
  ambito_atencion?: 'COMPLETO' | 'AMBULATORIO' | null;
  contextos_lab_permitidos?: ContextoLab[];
  contextos_lab?: Array<{ id: ContextoLab; label: string }>;
  puede_turnos?: boolean;
  puede_informes?: boolean;
  puede_validar_informes?: boolean;
  puede_pedir_lab?: boolean;
  puede_guardia?: boolean;
  puede_internacion?: boolean;
}

export interface Turno {
  id: number;
  medico_id: number;
  medico_nombre: string;
  paciente_nombre: string;
  fecha_hora_inicio: string;
  fecha_hora_fin: string;
  estado: string;
  asistencia_confirmada_en: string | null;
  tipo: 'CONSULTA' | 'ESTUDIO';
}

export interface Medico {
  id: number;
  nombre: string;
  apellido: string;
  nombre_completo?: string;
  especialidad_nombre?: string;
}

export interface Slot {
  horario_id: number;
  inicio: string;
  fin: string;
  duracion_min: number;
  tipo: 'CONSULTA' | 'ESTUDIO';
}

export interface InformeResumen {
  id: number;
  numero: string | null;
  paciente_nombre: string;
  estado: string;
  estado_display: string;
  es_parcial: boolean;
  fecha_solicitud: string | null;
  puede_descargar_pdf: boolean;
  puede_validar: boolean;
  puede_desvalidar?: boolean;
  puede_informar_parcial: boolean;
}

export interface ResultadoMovil {
  id: number;
  tipo_examen: number;
  tipo_examen_nombre?: string;
  tipo_examen_codigo?: string;
  tipo_examen_muestra_codigo?: string | null;
  valor_obtenido?: string | null;
  valor_numerico?: number | null;
  unidad?: string | null;
  tipo_examen_rango_referencia?: string | null;
  rango_referencia_snapshot?: string | null;
  fuera_de_rango?: boolean;
  critico?: boolean;
  es_patologico?: boolean;
  es_critico?: boolean;
}

export interface PanelResumenOrdenMovil {
  id: number;
  codigo?: string | null;
  nombre: string;
  tipos_examen_ids: number[];
}

export interface OrdenInformeMovil {
  resultados?: ResultadoMovil[];
  estado?: string;
  paneles_resumen?: PanelResumenOrdenMovil[];
  orden_grupos_informe?: string[];
}

export interface PacienteLabMovil {
  id: number;
  dni: string;
  nombre: string;
  apellido: string;
  nombre_completo: string;
  internacion_activa: boolean;
  sector_internacion?: string | null;
  contexto_sugerido: ContextoLab;
}

export interface LabCatalogItem {
  kind: 'examen' | 'panel';
  id: number;
  codigo: string;
  nombre: string;
  favorito?: boolean;
  examenes_ids?: number[];
}

export interface PaqueteLabMovil {
  id: number;
  codigo: string;
  nombre: string;
  contexto: ContextoLab;
  descripcion: string;
  paneles: LabCatalogItem[];
  examenes: LabCatalogItem[];
}

export interface OrdenLabMovilResumen {
  id: number;
  numero: string | null;
  estado: string;
  origen_solicitud: string;
  origen_display: string;
  paciente_nombre: string;
  paciente_dni: string;
  fecha_programada_toma: string | null;
}
