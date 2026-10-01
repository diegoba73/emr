export type RolMovil =
  | 'paciente'
  | 'medico'
  | 'secretaria'
  | 'laboratorio'
  | 'bioquimico';

export interface Perfil {
  id: number;
  nombre: string;
  rol: RolMovil;
  medico_id: number | null;
  paciente_id: number | null;
  puede_turnos?: boolean;
  puede_informes?: boolean;
  puede_validar_informes?: boolean;
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
  puede_informar_parcial: boolean;
}

export interface ResultadoMovil {
  id: number;
  tipo_examen: number;
  tipo_examen_nombre?: string;
  tipo_examen_codigo?: string;
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
