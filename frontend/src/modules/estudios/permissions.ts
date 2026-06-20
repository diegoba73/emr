import type { User } from '../../types';
import type { EstudioComplementario, InformeEstudioComplementario } from '../../types/estudios';

function normalizedRol(user: User | null | undefined): string {
  return (user?.rol || '').toLowerCase();
}

export function canAccessEstudiosModule(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const rol = normalizedRol(user);
  return rol === 'admin' || rol === 'medico' || rol === 'paciente';
}

export function canWriteEstudio(user: User | null | undefined): boolean {
  if (!user) return false;
  if (user.is_superuser) return true;
  const rol = normalizedRol(user);
  return rol === 'admin' || rol === 'medico';
}

export function canValidateInforme(user: User | null | undefined): boolean {
  if (!user) return false;
  return user.is_superuser || normalizedRol(user) === 'admin';
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
  return false;
}

export function canCrearInforme(estudio: EstudioComplementario): boolean {
  return estudio.estado === 'REALIZADO' || estudio.estado === 'INFORMADO';
}

export function canEmitirInforme(
  estudio: EstudioComplementario,
  informe: InformeEstudioComplementario
): boolean {
  if (informe.estado !== 'BORRADOR') return false;
  if (informe.reemplaza_a) {
    return estudio.estado === 'VALIDADO' || estudio.estado === 'ENTREGADO';
  }
  return estudio.estado === 'REALIZADO' || estudio.estado === 'INFORMADO';
}

export function canValidarInformeUi(
  user: User | null | undefined,
  estudio: EstudioComplementario,
  informe: InformeEstudioComplementario
): boolean {
  return (
    canValidateInforme(user) &&
    estudio.estado === 'INFORMADO' &&
    informe.estado === 'EMITIDO'
  );
}

export function canRectificarInforme(
  estudio: EstudioComplementario,
  informe: InformeEstudioComplementario
): boolean {
  return (
    (estudio.estado === 'VALIDADO' || estudio.estado === 'ENTREGADO') &&
    informe.estado === 'VALIDADO' &&
    informe.es_vigente
  );
}

export function canMarcarRealizado(estudio: EstudioComplementario): boolean {
  return estudio.estado === 'SOLICITADO';
}

export function canAnularEstudio(estudio: EstudioComplementario): boolean {
  return ['SOLICITADO', 'REALIZADO', 'INFORMADO'].includes(estudio.estado);
}

export function canEntregarEstudio(estudio: EstudioComplementario): boolean {
  return estudio.estado === 'VALIDADO';
}

export function canAsociarArchivo(estudio: EstudioComplementario): boolean {
  return !['ANULADO', 'ENTREGADO'].includes(estudio.estado);
}
