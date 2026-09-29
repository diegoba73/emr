export const dateKey = (date: Date) => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
export function monthCells(month: Date): (string | null)[] {
  const first = new Date(month.getFullYear(), month.getMonth(), 1);
  const offset = (first.getDay()+6)%7;
  const count = new Date(month.getFullYear(), month.getMonth()+1, 0).getDate();
  const cells: (string | null)[] = Array(offset).fill(null);
  for (let day=1; day<=count; day++) cells.push(dateKey(new Date(month.getFullYear(), month.getMonth(), day)));
  while (cells.length % 7) cells.push(null);
  return cells;
}
export function notificationTurnoId(data: unknown): string | null {
  if (!data || typeof data !== 'object') return null;
  const id = (data as { turno_id?: unknown }).turno_id;
  if (typeof id !== 'string' && typeof id !== 'number') return null;
  const text = String(id);
  return /^[1-9]\d{0,14}$/.test(text) ? text : null;
}
