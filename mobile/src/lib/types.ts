export interface Perfil { id: number; nombre: string; rol: 'paciente' | 'medico'; medico_id: number | null; paciente_id: number | null }
export interface Turno { id: number; medico_id: number; medico_nombre: string; paciente_nombre: string; fecha_hora_inicio: string; fecha_hora_fin: string; estado: string; asistencia_confirmada_en: string | null; tipo: 'CONSULTA' | 'ESTUDIO' }
export interface Medico { id: number; nombre: string; apellido: string; nombre_completo?: string; especialidad_nombre?: string }
export interface Slot { horario_id: number; inicio: string; fin: string; duracion_min: number; tipo: 'CONSULTA' | 'ESTUDIO' }
