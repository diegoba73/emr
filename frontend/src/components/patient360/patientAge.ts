import { differenceInYears, parseISO, isValid } from 'date-fns';

export function patientAgeYears(fechaNacimiento: string | undefined | null): string {
  if (!fechaNacimiento) return '—';
  try {
    const d = parseISO(fechaNacimiento.length === 10 ? `${fechaNacimiento}T12:00:00` : fechaNacimiento);
    if (!isValid(d)) return '—';
    return String(differenceInYears(new Date(), d));
  } catch {
    return '—';
  }
}
