import { format, parse, startOfWeek, getDay } from 'date-fns';
import { es } from 'date-fns/locale';
import { dateFnsLocalizer } from 'react-big-calendar';

const locales = {
  es: es,
};

export const localizer = dateFnsLocalizer({
  format,
  parse,
  startOfWeek,
  getDay,
  locales,
});

/** Formatos 24 h para react-big-calendar (evita AM/PM del locale del navegador). */
export const calendarFormats24h = {
  timeGutterFormat: 'HH:mm',
  eventTimeRangeFormat: (
    { start, end }: { start: Date; end: Date },
    _culture: string,
    loc: { format: (d: Date, f: string, c?: string) => string }
  ) => `${loc.format(start, 'HH:mm')}–${loc.format(end, 'HH:mm')}`,
  eventTimeRangeStartFormat: (
    { start }: { start: Date },
    _culture: string,
    loc: { format: (d: Date, f: string, c?: string) => string }
  ) => loc.format(start, 'HH:mm'),
  eventTimeRangeEndFormat: (
    { end }: { end: Date },
    _culture: string,
    loc: { format: (d: Date, f: string, c?: string) => string }
  ) => loc.format(end, 'HH:mm'),
  selectRangeFormat: (
    { start, end }: { start: Date; end: Date },
    _culture: string,
    loc: { format: (d: Date, f: string, c?: string) => string }
  ) => `${loc.format(start, 'HH:mm')}–${loc.format(end, 'HH:mm')}`,
  agendaTimeFormat: 'HH:mm',
  agendaTimeRangeFormat: (
    { start, end }: { start: Date; end: Date },
    _culture: string,
    loc: { format: (d: Date, f: string, c?: string) => string }
  ) => `${loc.format(start, 'HH:mm')}–${loc.format(end, 'HH:mm')}`,
};
