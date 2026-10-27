/** Bandejas A5 — claves alineadas al API `bandeja=` / `bandejas-resumen`. */

export type BandejaEstudioKey =
  | 'todos'
  | 'pendiente_programar'
  | 'programados'
  | 'documentacion_pendiente'
  | 'pendiente_entrega'
  | 'finalizados'
  | 'anulados';

export const BANDEJA_OPTIONS: { key: BandejaEstudioKey; label: string }[] = [
  { key: 'todos', label: 'Todos' },
  { key: 'pendiente_programar', label: 'Pendiente de programar' },
  { key: 'programados', label: 'Programados' },
  { key: 'documentacion_pendiente', label: 'Documentación pendiente' },
  { key: 'pendiente_entrega', label: 'Pendiente de entrega' },
  { key: 'finalizados', label: 'Finalizados' },
  { key: 'anulados', label: 'Anulados' },
];

export const MODULO_ESTUDIOS_LABEL = 'Programación de turnos';
export const MODULO_ESTUDIOS_LABEL_PACIENTE = 'Mis turnos programados';

export type BandejasResumen = Record<BandejaEstudioKey, number>;

export const emptyBandejasResumen = (): BandejasResumen => ({
  todos: 0,
  pendiente_programar: 0,
  programados: 0,
  documentacion_pendiente: 0,
  pendiente_entrega: 0,
  finalizados: 0,
  anulados: 0,
});
