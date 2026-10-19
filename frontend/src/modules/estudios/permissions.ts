import type { User } from '../../types';
import type { EstudioComplementario, InformeEstudioComplementario } from '../../types/estudios';
import { isOperadorLimsRole, isProfesionalEstudioRole } from '../../utils/roles';

function normalizedRol(user: User | null | undefined): string {
  return (user?.rol || '').toLowerCase();
}

function puedeOperarEstudios(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  if (isOperadorLimsRole(normalizedRol(user))) return false;
  const rol = normalizedRol(user);
  // Secretaría: operador habitual del módulo (alta/edición/doc/agenda).
  return (
    rol === 'admin' ||
    rol === 'medico' ||
    rol === 'secretaria' ||
    isProfesionalEstudioRole(rol)
  );
}

export function canAccessEstudiosModule(user: User | null | undefined): boolean {
  if (!user) return false;
  // Laboratorio/bioquímico no usan este módulo: trabajan en LIMS.
  if (user.is_superuser) return true;
  if (isOperadorLimsRole(normalizedRol(user))) return false;
  const rol = normalizedRol(user);
  return (
    rol === 'admin' ||
    rol === 'medico' ||
    rol === 'paciente' ||
    rol === 'secretaria' ||
    rol === 'enfermeria' ||
    isProfesionalEstudioRole(rol)
  );
}

export function canAsignarTurnoEstudio(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const rol = normalizedRol(user);
  return rol === 'admin' || rol === 'secretaria';
}

export function canWriteEstudio(user: User | null | undefined): boolean {
  return puedeOperarEstudios(user);
}

/** Registrar realización: roles con escritura del módulo (incluye secretaría). */
export function canMarcarRealizadoUser(user: User | null | undefined): boolean {
  return canWriteEstudio(user);
}

/** Admin, secretaría o profesional que marcó el estudio como realizado. */
export function esRealizadorOAdmin(
  user: User | null | undefined,
  estudio: EstudioComplementario
): boolean {
  if (!user) return false;
  const rol = normalizedRol(user);
  if (user.is_superuser || rol === 'admin' || rol === 'secretaria') return true;
  return Boolean(estudio.realizado_por && estudio.realizado_por === user.id);
}

/**
 * Editar archivos / informes / metadata.
 * Tras VALIDADO: realizador, admin o secretaría. ENTREGADO/ANULADO: no.
 */
export function canModificarContenidoEstudio(
  user: User | null | undefined,
  estudio: EstudioComplementario
): boolean {
  if (!canWriteEstudio(user)) return false;
  if (estudio.estado === 'ANULADO' || estudio.estado === 'ENTREGADO') return false;
  if (estudio.estado === 'VALIDADO') {
    return esRealizadorOAdmin(user, estudio);
  }
  return true;
}

export function canValidateInforme(
  user: User | null | undefined,
  estudio?: EstudioComplementario | null
): boolean {
  if (!user) return false;
  const rol = normalizedRol(user);
  if (user.is_superuser || rol === 'admin' || rol === 'secretaria') return true;
  if (!estudio) return false;
  return Boolean(estudio.realizado_por && estudio.realizado_por === user.id);
}

export function canDownloadArchivoEstudio(
  user: User | null | undefined,
  estudio: EstudioComplementario
): boolean {
  if (!user) return false;
  if (canWriteEstudio(user)) return true;
  const rol = normalizedRol(user);
  if (rol === 'paciente') {
    return estudio.estado === 'ENTREGADO';
  }
  if (rol === 'enfermeria') {
    return estudio.estado === 'VALIDADO' || estudio.estado === 'ENTREGADO';
  }
  return false;
}

export function canDownloadPdfInformeEstudio(
  user: User | null | undefined,
  estudio: EstudioComplementario,
  informe: InformeEstudioComplementario
): boolean {
  if (!user) return false;
  if (user.is_superuser || normalizedRol(user) === 'admin') return true;
  if (!informe.es_vigente || informe.estado !== 'VALIDADO') return false;
  if (canWriteEstudio(user)) {
    return estudio.estado === 'VALIDADO' || estudio.estado === 'ENTREGADO' || estudio.estado === 'INFORMADO';
  }
  const rol = normalizedRol(user);
  if (rol === 'paciente') {
    return estudio.estado === 'ENTREGADO';
  }
  if (rol === 'enfermeria') {
    return estudio.estado === 'VALIDADO' || estudio.estado === 'ENTREGADO';
  }
  return false;
}

export function canCrearInforme(
  user: User | null | undefined,
  estudio: EstudioComplementario
): boolean {
  if (!canModificarContenidoEstudio(user, estudio)) return false;
  return estudio.estado === 'REALIZADO' || estudio.estado === 'INFORMADO';
}

export function canEmitirInforme(
  user: User | null | undefined,
  estudio: EstudioComplementario,
  informe: InformeEstudioComplementario
): boolean {
  if (informe.estado !== 'BORRADOR') return false;
  if (informe.reemplaza_a) {
    if (!esRealizadorOAdmin(user, estudio)) return false;
    return estudio.estado === 'VALIDADO' || estudio.estado === 'ENTREGADO';
  }
  if (!canModificarContenidoEstudio(user, estudio)) return false;
  return estudio.estado === 'REALIZADO' || estudio.estado === 'INFORMADO';
}

export function canValidarInformeUi(
  user: User | null | undefined,
  estudio: EstudioComplementario,
  informe: InformeEstudioComplementario
): boolean {
  return (
    canValidateInforme(user, estudio) &&
    estudio.estado === 'INFORMADO' &&
    informe.estado === 'EMITIDO'
  );
}

export function canRectificarInforme(
  user: User | null | undefined,
  estudio: EstudioComplementario,
  informe: InformeEstudioComplementario
): boolean {
  if (!esRealizadorOAdmin(user, estudio)) return false;
  return (
    (estudio.estado === 'VALIDADO' || estudio.estado === 'ENTREGADO') &&
    informe.estado === 'VALIDADO' &&
    informe.es_vigente
  );
}

export function canMarcarRealizado(estudio: EstudioComplementario): boolean {
  return estudio.estado === 'SOLICITADO' || estudio.estado === 'CONFIRMADO';
}

export function canAnularEstudio(estudio: EstudioComplementario): boolean {
  // B: anulación administrativa solo previa a realización.
  return estudio.estado === 'SOLICITADO' || estudio.estado === 'CONFIRMADO';
}

export function canReprogramarTurnoEstudio(estudio: EstudioComplementario): boolean {
  return (
    estudio.estado === 'CONFIRMADO' &&
    Boolean(estudio.turno_id) &&
    (estudio.turno_estado === 'CONFIRMADO' || estudio.turno_estado === 'RESERVADO')
  );
}

export function canEntregarEstudio(
  user: User | null | undefined,
  estudio: EstudioComplementario
): boolean {
  if (estudio.estado !== 'VALIDADO') return false;
  if (estudio.tipo_actividad === 'CIRUGIA' && !estudio.fecha_cierre) return false;
  if (canModificarContenidoEstudio(user, estudio)) return true;
  const rol = normalizedRol(user);
  return rol === 'secretaria' || rol === 'admin';
}

/** D: cierre administrativo — secretaría o escritura clínica; gate de protocolo en backend. */
export function canCerrarCirugia(
  user: User | null | undefined,
  estudio: EstudioComplementario
): boolean {
  if (estudio.tipo_actividad !== 'CIRUGIA') return false;
  if (estudio.estado !== 'VALIDADO') return false;
  if (estudio.fecha_cierre) return false;
  const rol = normalizedRol(user);
  if (rol === 'admin' || rol === 'secretaria') return true;
  return canModificarContenidoEstudio(user, estudio);
}

export function canAsociarArchivo(
  user: User | null | undefined,
  estudio: EstudioComplementario
): boolean {
  if (!canModificarContenidoEstudio(user, estudio)) return false;
  const origen = estudio.origen || 'INTERNO';
  return origen === 'EXTERNO' || origen === 'IMPORTADO_HISTORICO';
}

/** Subida directa de resultado (estudios hechos en la clínica). */
export function canSubirArchivoEstudio(
  user: User | null | undefined,
  estudio: EstudioComplementario
): boolean {
  if (!canModificarContenidoEstudio(user, estudio)) return false;
  const origen = estudio.origen || 'INTERNO';
  return origen === 'INTERNO';
}

/** Quitar archivo vinculado (subido o asociado) mientras el estudio no esté cerrado. */
export function canQuitarArchivoEstudio(
  user: User | null | undefined,
  estudio: EstudioComplementario
): boolean {
  return canModificarContenidoEstudio(user, estudio);
}


export function canEnviarInformeEstudio(
  user: User | null | undefined, estudio: EstudioComplementario, informe: InformeEstudioComplementario
): boolean {
  return Boolean(user && (user.is_superuser || normalizedRol(user) === 'secretaria' || canWriteEstudio(user)) &&
    ['VALIDADO', 'ENTREGADO'].includes(estudio.estado) && informe.es_vigente && informe.estado === 'VALIDADO' &&
    canDownloadPdfInformeEstudio(user, estudio, informe));
}
