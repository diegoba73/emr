import type { User } from '../types';
import { normalizeRol } from './permissions';

export function isPacienteRole(user: User | null | undefined): boolean {
  return normalizeRol(user ?? null) === 'paciente';
}

/** Etiqueta del módulo home en sidebar/header. */
export function getHomeNavLabel(): string {
  return 'Inicio';
}

/** Portal clínico de análisis: paciente ve «Análisis Clínico»; resto «Laboratorio». */
export function getSolicitudesModuleLabel(user: User | null | undefined): string {
  return isPacienteRole(user) ? 'Análisis Clínico' : 'Laboratorio';
}

/** Título de página según ruta y rol (header AppLayout). */
export function getAppSegmentTitle(pathname: string, user: User | null | undefined): string {
  const p = pathname;
  if (p.startsWith('/paciente/')) return isPacienteRole(user) ? 'Mi ficha' : 'Paciente 360';
  if (p.startsWith('/dashboard')) return getHomeNavLabel();
  if (p.startsWith('/pacientes')) return 'Pacientes';
  if (p.startsWith('/turnos')) return 'Turnos';
  if (p.startsWith('/atenciones')) return isPacienteRole(user) ? 'Mis atenciones' : 'Atenciones Clínicas';
  if (p.startsWith('/archivos')) return isPacienteRole(user) ? 'Mis archivos' : 'Archivos';
  if (p.startsWith('/estudios-complementarios')) {
    return isPacienteRole(user) ? 'Mis estudios complementarios' : 'Estudios complementarios';
  }
  if (p.startsWith('/solicitudes/') && p !== '/solicitudes') {
    return isPacienteRole(user) ? 'Detalle de análisis' : 'Detalle de orden';
  }
  if (p.startsWith('/solicitudes')) return getSolicitudesModuleLabel(user);
  if (p.startsWith('/internacion')) return 'Internación';
  if (p.startsWith('/medicos')) return 'Médicos';
  if (p.startsWith('/usuarios')) return 'Usuarios';
  if (p.startsWith('/catalogos')) return 'Catálogos';
  if (p.startsWith('/auditoria')) return 'Auditoría';
  if (p.startsWith('/laboratorio')) return 'Laboratorio';
  return 'Synesis EMR';
}
