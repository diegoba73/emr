export type Turno = 'MANANA' | 'TARDE' | 'NOCHE';

export interface ControlEnfermeriaRow {
  id: number;
  fecha: string;
  turno: string;
  tension_arterial: string;
  frecuencia_cardiaca: number | null;
  frecuencia_respiratoria: number | null;
  temperatura: string | number | null;
  saturacion_oxigeno: string | number | null;
  dolor: number | null;
  glucemia: number | null;
  observaciones: string;
  registrado_por_nombre?: string | null;
}

export interface BalanceHidricoRow {
  id: number;
  fecha: string;
  turno: string;
  ingresos_vo_ml: number | null;
  ingresos_ev_ml: number | null;
  diuresis_ml: number | null;
  otros_egresos_ml: number | null;
  observaciones: string;
  registrado_por_nombre?: string | null;
}

export interface NotaEnfermeriaRow {
  id: number;
  fecha: string;
  observaciones: string;
  curaciones: string;
  dispositivos: string;
  registrado_por_nombre?: string | null;
}

export interface RegistroKinesiologiaRow {
  id: number;
  fecha: string;
  frecuencia_respiratoria: number | null;
  saturacion_oxigeno: string | number | null;
  oxigenoterapia: string;
  secreciones: string;
  tecnica: string;
  movilizacion: string;
  evolucion: string;
  plan: string;
  registrado_por_nombre?: string | null;
}

export const formatFechaHc = (iso: string) =>
  iso ? new Date(iso).toLocaleString('es-AR') : '—';

export const toIntHc = (v: string) => {
  const n = Number.parseInt(v, 10);
  return Number.isFinite(n) ? n : null;
};

export const toDecHc = (v: string) => (v.trim() === '' ? null : v);

export const TURNO_OPTIONS: { value: Turno; label: string }[] = [
  { value: 'MANANA', label: 'Mañana' },
  { value: 'TARDE', label: 'Tarde' },
  { value: 'NOCHE', label: 'Noche' },
];
