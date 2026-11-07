/**
 * Formateo de campos fecha/hora para inputs (hora local del navegador, sin toISOString).
 */

const pad2 = (n: number) => String(n).padStart(2, '0');

const _FECHA_SOLO = /^(\d{4})-(\d{2})-(\d{2})$/;

/** YYYY-MM-DD */
export function formatFecha(date: Date): string {
  if (Number.isNaN(date.getTime())) return '';
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

/**
 * Muestra una fecha de calendario (nacimiento, etc.) sin corrimiento UTC.
 *
 * ``new Date('1973-09-01')`` se interpreta como medianoche UTC y en AR (UTC-3)
 * cae el día anterior. Para ``YYYY-MM-DD`` se formatea en local puro.
 */
export function formatFechaDisplay(
  value: string | null | undefined,
  locale = 'es-AR'
): string {
  if (value == null) return 'N/A';
  const raw = String(value).trim();
  if (!raw) return 'N/A';

  // Solo aplicar el atajo si el valor es fecha pura YYYY-MM-DD (sin hora).
  const puro = _FECHA_SOLO.exec(raw);
  if (puro) {
    const y = Number(puro[1]);
    const m = Number(puro[2]);
    const d = Number(puro[3]);
    const local = new Date(y, m - 1, d);
    if (Number.isNaN(local.getTime())) return raw;
    return local.toLocaleDateString(locale, {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  }

  const dt = new Date(raw);
  if (Number.isNaN(dt.getTime())) return raw;
  return dt.toLocaleDateString(locale, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

/** HH:mm (24 h, sin AM/PM). */
export function formatHora(date: Date): string {
  if (Number.isNaN(date.getTime())) return '';
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

const HORA_24: Intl.DateTimeFormatOptions = {
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
};

const FECHA_HORA_24: Intl.DateTimeFormatOptions = {
  day: '2-digit',
  month: '2-digit',
  year: 'numeric',
  ...HORA_24,
};

/** Hora corta 24 h vía locale (p. ej. grillas de agenda). */
export function formatHoraDisplay(date: Date, locale = 'es-AR'): string {
  if (Number.isNaN(date.getTime())) return '';
  // Preferir padding manual: algunos motores ignoran hour12 con es-AR.
  return formatHora(date) || date.toLocaleTimeString(locale, HORA_24);
}

/** Fecha + hora 24 h (dd/mm/aaaa HH:mm). */
export function formatFechaHoraDisplay(
  value: string | Date | null | undefined,
  locale = 'es-AR'
): string {
  if (value == null || value === '') return '—';
  const dt = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(dt.getTime())) return '—';
  const fecha = dt.toLocaleDateString(locale, {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
  return `${fecha} ${formatHora(dt)}`;
}

export const LOCALE_TIME_24 = HORA_24;
export const LOCALE_DATETIME_24 = FECHA_HORA_24;
