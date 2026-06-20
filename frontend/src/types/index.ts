// Tipos base
export interface BaseModel {
  id: number;
  created_at?: string;
  updated_at?: string;
}

// Usuario
export interface User extends BaseModel {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  nombre_completo?: string; // Nombre completo calculado (first_name + last_name)
  rol: 'ADMIN' | 'SECRETARIA' | 'MEDICO' | 'PACIENTE' | 'ENFERMERIA' | 'LABORATORIO';
  telefono?: string;
  is_active: boolean;
  is_staff?: boolean;
  is_superuser?: boolean;
  date_joined?: string;
  last_login?: string;
  medico?: {
    id: number;
    matricula: string;
    especialidad?: {
      id: number;
      nombre: string;
    };
  };
  paciente?: {
    id: number;
    dni: string;
    fecha_nacimiento?: string;
    sexo?: 'M' | 'F';
  };
}

// Pacientes
export interface Paciente extends BaseModel {
  nombre: string;
  apellido: string;
  fecha_nacimiento: string;
  dni: string;
  telefono?: string;
  email?: string;
  direccion?: string;
  sexo?: 'M' | 'F';
  obra_social?: string;
  numero_afiliado?: string;
  observaciones?: string;
  antecedentes_personales?: string;
  antecedentes_familiares?: string;
  genero?: 'M' | 'F' | 'O';
  grupo_sanguineo?: string;
  alergias?: string;
  antecedentes?: string;
}

// Médicos
export interface Medico extends BaseModel {
  nombre: string;
  apellido: string;
  matricula: string;
  especialidad: Especialidad;
  telefono?: string;
  email?: string;
  activo: boolean;
}

export interface Especialidad extends BaseModel {
  nombre: string;
  descripcion?: string;
}

// NUEVO: Centros Físicos
export interface CentroFisico extends BaseModel {
  codigo: 'CEHTA' | 'PUEBLO_DE_LUIS';
  nombre: string;
  descripcion?: string;
  direccion?: string;
  telefono?: string;
  activo: boolean;
}

// NUEVO: Tipos de Atención
export interface TipoAtencion extends BaseModel {
  codigo: 'AMBULATORIA' | 'GUARDIA_CARDIOLOGICA' | 'INTERNACION_UCO' | 'INTERNACION_UCE' | 'CIRUGIA_AMBULATORIA' | 'CIRUGIA_COMPLEJA';
  nombre: string;
  descripcion?: string;
  centro_fisico: CentroFisico;
  requiere_internacion: boolean;
  es_urgencia: boolean;
  activo: boolean;
}

// NUEVO: Áreas de Internación
export interface AreaInternacion extends BaseModel {
  codigo: 'UCO' | 'UCE' | 'PISO_GENERAL' | 'CIRUGIA';
  nombre: string;
  descripcion?: string;
  centro_fisico: CentroFisico;
  capacidad_camas: number;
  activo: boolean;
}

// NUEVO: Camas de Internación
export interface CamaInternacion extends BaseModel {
  numero: string;
  area: AreaInternacion;
  estado: 'DISPONIBLE' | 'OCUPADA' | 'MANTENIMIENTO' | 'RESERVADA';
  tipo_cama: 'ESTANDAR' | 'UCI' | 'UCE' | 'POST_QUIRURGICA';
  activa: boolean;
}

// NUEVO: Internaciones
export interface Internacion extends BaseModel {
  paciente: Paciente;
  medico_responsable?: Medico;
}

// NUEVO: Archivos Médicos
export interface ArchivoMedico extends BaseModel {
  titulo: string;
  descripcion?: string;
  tipo_archivo: 'DICOM' | 'NIFTI' | 'RAYOS_X' | 'TOMOGRAFIA' | 'RESONANCIA' | 'ULTRASONIDO' | 'FOTO_CLINICA' | 'PATOLOGIA' | 'PDF' | 'OTRO';
  archivo?: string; // solo escritura (upload); lectura usa download_url
  archivo_nombre?: string | null;
  archivo_size?: number | null;
  download_url?: string | null;
  paciente_id: number;
  paciente_nombre?: string; // Agregado para mostrar el nombre del paciente
  consulta_id?: number;
  fecha_subida: string;
  fecha_estudio?: string;
  subido_por: string;
  es_urgente: boolean;
}

// NUEVO: Internaciones (sistema antiguo)
export interface Internacion extends BaseModel {
  paciente: Paciente;
  medico_responsable?: Medico;
  cama: CamaInternacion;
  turno_origen?: Turno;
  fecha_ingreso: string;
  fecha_alta?: string;
  fecha_estimada_alta?: string;
  motivo_ingreso: string;
  diagnostico_ingreso?: string;
  plan_tratamiento?: string;
  estado: 'ACTIVA' | 'ALTA_MEDICA' | 'ALTA_VOLUNTARIA' | 'TRANSFERENCIA' | 'FALLECIMIENTO';
  observaciones?: string;
  numero_internacion: string;
  es_urgencia: boolean;
  duracion_dias?: number;
  centro_fisico?: CentroFisico;
  area_internacion?: AreaInternacion;
}

// NUEVO: Módulo de Gestión de Camas (Internación)
export interface Sector extends BaseModel {
  id: number;
  nombre: string;
}

export interface Cama extends BaseModel {
  id: number;
  nombre: string;
  sector: Sector | number; // Puede ser objeto o ID
  sector_nombre?: string; // Nombre del sector (solo lectura desde backend)
  estado: 'DISPONIBLE' | 'OCUPADA' | 'LIMPIEZA' | 'MANTENIMIENTO';
  aislada: boolean;
  internacion_actual?: {
    id_internacion: number;
    nombre_paciente: string;
    nombre_medico: string | null;
    diagnostico: string;
    fecha_ingreso: string;
    dias_internacion: number;
  };
}

export interface InternacionCama extends BaseModel {
  paciente: number;
  cama: number;
  medico: number | null;
  fecha_ingreso: string;
  fecha_alta: string | null;
  diagnostico_ingreso: string;
  diagnostico_cie?: DiagnosticoCIE10 | null;
  activo: boolean;
  nombre_paciente?: string;
  nombre_medico?: string | null;
  dias_internacion?: number;
}

// Recurso físico agendable
export interface Recurso extends BaseModel {
  nombre: string;
  ubicacion: 'CEHTA' | 'ICPL';
  ubicacion_display?: string;
  tipo_recurso: 'CONSULTORIO' | 'SALA_PROCEDIMIENTO' | 'SALA_HEMODINAMIA' | 'QUIROFANO';
  tipo_recurso_display?: string;
  activo: boolean;
}

export type TipoIntervencion = 'CONSULTA' | 'ESTUDIO' | 'PROCEDIMIENTO' | 'CIRUGIA';
export type EstadoClinico = 'ABIERTA' | 'FINALIZADA' | 'EN_REVISION';

export interface EstudioDiagnostico extends BaseModel {
  nombre: string;
  descripcion?: string;
  activo: boolean;
}

export interface ProcedimientoCatalogo extends BaseModel {
  nombre: string;
  descripcion?: string;
  activo: boolean;
}

export type TipoDocumento = 'INFORME' | 'ESTUDIO' | 'ANALISIS' | 'DIAGNOSTICO' | 'IMAGEN' | 'CONSENTIMIENTO' | 'OTRO';

export interface Documento extends BaseModel {
  atencion_id: number;
  tipo_documento: TipoDocumento;
  archivo?: string; // solo escritura
  archivo_nombre?: string | null;
  archivo_size?: number | null;
  download_url?: string | null;
  descripcion?: string | null;
  fecha_subida: string;
  usuario_cargador_id?: number | null;
  usuario_cargador_nombre?: string | null;
}

export interface ConsultaAmbulatoriaRecord extends BaseModel {
  atencion_id: number;
  anamnesis?: string | null;
  examen_fisico?: string | null;
  diagnostico_presuntivo?: string | null;
  plan_manejo?: string | null;
  antecedentes_relevantes?: string | null;
  alergias?: string | null;
  medicacion_actual?: string | null;
  diagnostico_definitivo?: string | null;
  observaciones_medicas?: string | null;
}

export interface RegistroProcedimientoRecord extends BaseModel {
  atencion_id: number;
  estudio?: EstudioDiagnostico | null;
  estudio_id?: number | null;
  procedimiento?: ProcedimientoCatalogo | null;
  procedimiento_id?: number | null;
  descripcion_procedimiento?: string | null;
  tipo_procedimiento?: 'DIAGNOSTICO' | 'TERAPEUTICO' | null;
  informe_medico?: string | null;
  hallazgos?: string | null;
  profesional_asistente?: Medico | null;
  profesional_asistente_id?: number | null;
  complicaciones?: string | null;
  adjunto_resultado?: string | null;
}

export interface RegistroQuirurgicoRecord extends BaseModel {
  atencion_id: number;
  anestesista: Medico;
  anestesista_id: number;
  procedimiento?: ProcedimientoCatalogo | null;
  procedimiento_id?: number | null;
  diagnostico_preoperatorio: string;
  diagnostico_postoperatorio?: string | null;
  protocolo_quirurgico: string;
  hallazgos_operatorios?: string | null;
  complicaciones?: string | null;
  recuento_instrumental_ok: boolean;
  equipo_quirurgico?: Array<{ nombre: string; rol: string }> | null;
  consentimiento_informado?: string | null;
  documentos_adjuntos?: Documento[];
}

export interface AtencionSummary {
  id: number;
  fecha_admision: string;
  tipo_atencion: 'CONSULTORIO' | 'SALA_PROCEDIMIENTO' | 'SALA_HEMODINAMIA' | 'QUIROFANO';
  tipo_intervencion?: TipoIntervencion;
  estado_clinico?: EstadoClinico;
  /** True si la consulta ambulatoria tiene al menos un campo de texto con contenido (API turnos) */
  consulta_cargada?: boolean;
  consulta_ambulatoria?: { id: number } | null;
  registro_procedimiento?: { id: number } | null;
  registro_quirurgico?: { id: number } | null;
}

export interface Atencion extends BaseModel {
  turno?: Turno | null;
  turno_id?: number | null;
  paciente: Paciente;
  paciente_id?: number | null;
  medico_principal: Medico;
  medico_principal_id?: number | null;
  fecha_admision: string;
  fecha_cierre?: string | null;
  tipo_atencion: 'CONSULTORIO' | 'SALA_PROCEDIMIENTO' | 'SALA_HEMODINAMIA' | 'QUIROFANO';
  tipo_intervencion: TipoIntervencion;
  estado_clinico: EstadoClinico;
  observaciones_generales?: string | null;
  consulta_ambulatoria?: ConsultaAmbulatoriaRecord | null;
  registro_procedimiento?: RegistroProcedimientoRecord | null;
  registro_quirurgico?: RegistroQuirurgicoRecord | null;
  documentos: Documento[];
}

// Tipo para crear una atención
// El backend resuelve automáticamente paciente, medico_principal, tipo_atencion
// y tipo_intervencion desde el turno. Solo se requiere turno.
export interface CreateAtencionPayload {
  turno: number;  // ID del turno - el backend obtiene todo desde aquí
  // Campos opcionales (el backend los ignora si están presentes)
  observaciones_generales?: string | null;
}

// Turnos - ACTUALIZADO con recurso
export interface Turno extends BaseModel {
  paciente?: Paciente;
  paciente_id?: number;
  medico?: Medico;
  medico_id?: number;
  recurso?: Recurso;
  recurso_id?: number;
  fecha_hora?: string;
  fecha_hora_inicio: string;
  fecha_hora_fin?: string;
  motivo_reserva?: string;
  motivo_consulta?: string; // Mantener para compatibilidad
  estado: 'DISPONIBLE' | 'RESERVADO' | 'CONFIRMADO' | 'REALIZADO' | 'CANCELADO' | 'REAGENDADO';
  prioridad?: 'NORMAL' | 'ALTA' | 'URGENTE';
  notas_administrativas?: string;
  fecha_creacion?: string;
  ultima_modificacion?: string;
  atencion?: AtencionSummary | null;
}

// Historias Clínicas
export interface HistoriaClinica extends BaseModel {
  paciente: Paciente;
  numero_historia: string;
  fecha_apertura: string;
  activa: boolean;
}

export interface Consulta extends BaseModel {
  historia_clinica: HistoriaClinica;
  medico: Medico;
  turno?: Turno;
  fecha_hora_consulta: string;
  motivo_consulta_detalle: string;
  anamnesis?: string;
  examen_fisico?: string;
  diagnostico_presuntivo?: string;
  plan_manejo?: string;
  notas_medicas?: string;
  fecha_registro?: string;
  ultima_actualizacion?: string;
  // Campos optimizados del serializer (para evitar N+1 queries)
  paciente_nombre?: string;
  paciente_apellido?: string;
  paciente_dni?: string;
  paciente_id?: number;
}

export interface DiagnosticoCIE10 extends BaseModel {
  codigo: string;
  descripcion: string;
  categoria?: string;
  capitulo?: string;
  enfermedad?: string;
  tipo_enfermedad?: string;
  activo?: boolean;
}

// Solicitudes
export interface Solicitud extends BaseModel {
  paciente: number;
  paciente_info?: {
    id: number;
    nombre: string;
    apellido: string;
    dni: string;
    nombre_completo: string;
  };
  medico_solicitante?: number;
  medico_solicitante_info?: {
    id: number;
    nombre: string;
    apellido: string;
    especialidad: string;
    nombre_completo: string;
  };
  medicos_asignados: number[];
  medicos_asignados_info?: {
    id: number;
    nombre: string;
    apellido: string;
    especialidad: string;
    nombre_completo: string;
  }[];
  tipo_solicitud: 'EXAMEN_LABORATORIO' | 'ESTUDIO_IMAGEN' | 'CONSULTA_ESPECIALISTA' | 'PROCEDIMIENTO' | 'OTRO';
  descripcion?: string;
  observaciones?: string;
  fecha_solicitud: string;
  fecha_limite?: string;
  fecha_completada?: string;
  estado: 'PENDIENTE' | 'EN_PROCESO' | 'COMPLETADA' | 'CANCELADA' | 'ERROR';
  prioridad: 'BAJA' | 'NORMAL' | 'ALTA' | 'URGENTE';
  lims_id?: string;
  sincronizado_lims: boolean;
  ultima_sincronizacion?: string;
  dias_pendiente?: number;
  esta_vencida?: boolean;
  medicos_asignados_display?: string;
  creado_por?: string;
  modificado_por?: string;
  fecha_creacion?: string;
  fecha_modificacion?: string;
}



export interface Medicamento extends BaseModel {
  nombre: string;
  principio_activo?: string;
  codigo_atc?: string;
  descripcion?: string;
  presentacion?: string;
  concentracion?: string;
  via_administracion?: string;
  activo: boolean;
}

// Laboratorio
export interface TipoExamen extends BaseModel {
  id: number;
  codigo: string;
  nombre: string;
  precio: string; // String para mantener compatibilidad con formato del backend
  unidad_medida?: string;
  activo: boolean;
  // Campos adicionales del backend (opcionales)
  abreviatura?: string;
  tipo_muestra_requerida?: number;
  tipo_muestra_nombre?: string;
  tipo_muestra_codigo?: string;
  rango_referencia_texto?: string;
}

export interface PanelExamen extends BaseModel {
  nombre: string;
  codigo: string;
  descripcion?: string;
  precio: number;
  examenes_componentes: TipoExamen[];
  activo: boolean;
}

export interface SolicitudExamen extends BaseModel {
  paciente: Paciente;
  medico: Medico;
  fecha_solicitud: string;
  fecha_programada?: string;
  numero_solicitud: string;
  examenes: TipoExamen[];
  paneles: PanelExamen[];
  total: number;
  estado: 'PENDIENTE' | 'EN_PROGRESO' | 'COMPLETADO' | 'CANCELADO';
  observaciones?: string;
  urgencia: boolean;
}

export interface ResultadoExamen extends BaseModel {
  solicitud_examen: SolicitudExamen;
  tipo_examen: TipoExamen;
  valor_numerico?: number;
  valor_texto?: string;
  valor_normal_min?: number;
  valor_normal_max?: number;
  valor_normal_texto?: string;
  unidad?: string;
  es_normal?: boolean;
  interpretacion_ia?: string;
  validado_por?: Medico;
  fecha_resultado: string;
  observaciones?: string;
}

// Panel
export interface DashboardStats {
  total_pacientes: number;
  total_medicos: number;
  turnos_hoy: number;
  consultas_hoy: number;
  solicitudes_pendientes: number;
  resultados_pendientes: number;
}

// API Responses
export interface ApiResponse<T> {
  count: number;
  next?: string;
  previous?: string;
  results: T[];
}

export interface ApiError {
  detail: string;
  code?: string;
}

export * from './estudios'; 