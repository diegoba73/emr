/**
 * Utilidades para formatear y mostrar información de pacientes de manera consistente
 */
import { Paciente } from '../types';

/**
 * Formatea el nombre completo de un paciente en el formato estándar del EMR
 * Formato: "Apellido, Nombre - DNI: XXXX"
 * 
 * @param paciente - Objeto Paciente o null/undefined
 * @returns String formateado o "Paciente {id}" si no hay datos
 */
export const formatPacienteLabel = (paciente: Paciente | null | undefined): string => {
  if (!paciente) {
    return '';
  }
  
  const apellido = paciente.apellido || '';
  const nombre = paciente.nombre || '';
  const dni = paciente.dni || '';
  
  // Construir el label
  let label = '';
  
  if (apellido || nombre) {
    label = `${apellido}, ${nombre}`.trim();
    // Limpiar comas duplicadas o espacios extra
    label = label.replace(/^,\s*|,\s*$/g, '').trim();
  }
  
  if (dni) {
    label = label ? `${label} - DNI: ${dni}` : `DNI: ${dni}`;
  }
  
  // Si no hay nombre ni DNI, usar el ID
  if (!label && paciente.id) {
    label = `Paciente ${paciente.id}`;
  }
  
  return label || 'Paciente sin datos';
};

/**
 * Formatea el nombre completo de un paciente (sin DNI)
 * Formato: "Apellido, Nombre"
 * 
 * @param paciente - Objeto Paciente o null/undefined
 * @returns String formateado
 */
export const formatPacienteNombre = (paciente: Paciente | null | undefined): string => {
  if (!paciente) {
    return '';
  }
  
  const apellido = paciente.apellido || '';
  const nombre = paciente.nombre || '';
  
  if (apellido || nombre) {
    const label = `${apellido}, ${nombre}`.trim();
    return label.replace(/^,\s*|,\s*$/g, '').trim() || `Paciente ${paciente.id}`;
  }
  
  return paciente.id ? `Paciente ${paciente.id}` : 'Paciente sin datos';
};



























