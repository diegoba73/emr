import type { Turno } from '../types';

export type TurnoOrigen = NonNullable<Turno['origen']>;

export const TURNO_ORIGEN_OPTIONS: Array<{ value: TurnoOrigen; label: string }> = [
  { value: 'SISTEMA', label: 'Sistema / online' },
  { value: 'TELEFONO', label: 'Teléfono' },
  { value: 'PRESENCIAL', label: 'Presencial' },
];

export function labelTurnoOrigen(origen?: string | null): string {
  const found = TURNO_ORIGEN_OPTIONS.find((o) => o.value === origen);
  return found?.label || origen || 'Sistema / online';
}
