import { dateKey } from './calendar';

/** Ventana: desde 1 h antes del inicio hasta el inicio (no después). */
export const VENTANA_ESTOY_EN_SALA_MS = 60 * 60 * 1000;

/**
 * True si el turno es hoy (fecha local) y `now` está en [inicio-1h, inicio).
 */
export function enVentanaEstoyEnSala(inicioIso: string, nowMs = Date.now()): boolean {
  const inicio = new Date(inicioIso).getTime();
  if (Number.isNaN(inicio)) return false;
  if (dateKey(new Date(inicio)) !== dateKey(new Date(nowMs))) return false;
  return inicio - VENTANA_ESTOY_EN_SALA_MS <= nowMs && nowMs < inicio;
}

export function esTurnoHoy(inicioIso: string, nowMs = Date.now()): boolean {
  const inicio = new Date(inicioIso).getTime();
  if (Number.isNaN(inicio)) return false;
  return dateKey(new Date(inicio)) === dateKey(new Date(nowMs));
}
