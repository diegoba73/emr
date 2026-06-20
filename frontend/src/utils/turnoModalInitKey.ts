/**
 * Clave estable por apertura lógica del TurnoModal: evita re-inicializar formData en re-renders.
 */
export function getTurnoModalFormInitKey(
  open: boolean,
  editingTurnoId: number | null | undefined,
  selectedDateTime: Date | null | undefined
): string {
  if (!open) return '';
  if (editingTurnoId != null && editingTurnoId !== undefined) {
    return `edit:${editingTurnoId}`;
  }
  if (selectedDateTime && !Number.isNaN(selectedDateTime.getTime())) {
    return `create:${selectedDateTime.getTime()}`;
  }
  return 'new-empty';
}
