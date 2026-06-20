/**
 * Tipos / helpers para react-big-calendar en Turnos.
 * Formato local de fecha/hora: `utils/dateFieldFormat.ts` (formatFecha / formatHora).
 */

export type CalendarSlotInfo = {
  start: Date;
  end: Date;
  action: string;
  slots?: Date[];
};

export function isSelectableSlotAction(action: string): boolean {
  return action === 'doubleClick' || action === 'select' || action === 'click';
}
