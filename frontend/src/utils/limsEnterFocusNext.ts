import type { KeyboardEvent as ReactKeyboardEvent } from 'react';

/**
 * Navegación Enter → siguiente campo (misma UX que CargaResultadosLims).
 * Shift+Enter conserva salto de línea en multilínea.
 */
export const LIMS_ENTER_FOCUS_ATTR = 'data-lims-enter-focus';

export function focusLimsEnterField(
  key: string,
  attr: string = LIMS_ENTER_FOCUS_ATTR
): boolean {
  const input = document.querySelector<HTMLInputElement | HTMLTextAreaElement>(
    `[${attr}="${key}"]`
  );
  if (!input || input.disabled || input.readOnly) return false;
  input.focus();
  if (typeof input.select === 'function') {
    try {
      input.select();
    } catch {
      /* algunos inputs no permiten select */
    }
  }
  return true;
}

export function focusNextLimsEnterField(
  focusOrder: string[],
  currentKey: string,
  opts?: { onAfterLast?: () => void; attr?: string }
): void {
  const attr = opts?.attr ?? LIMS_ENTER_FOCUS_ATTR;
  const idx = focusOrder.indexOf(currentKey);
  if (idx === -1) return;
  for (let i = idx + 1; i < focusOrder.length; i += 1) {
    if (focusLimsEnterField(focusOrder[i], attr)) return;
  }
  opts?.onAfterLast?.();
}

export function handleLimsEnterNext(
  focusOrder: string[],
  currentKey: string,
  opts?: { onAfterLast?: () => void; attr?: string }
): (ev: ReactKeyboardEvent) => void {
  return (ev) => {
    if (ev.key !== 'Enter' || ev.shiftKey || ev.nativeEvent.isComposing) return;
    // No interceptar Enter con Autocomplete abierto (selección de opción).
    const target = ev.target as HTMLElement | null;
    if (target?.getAttribute('aria-expanded') === 'true') return;
    ev.preventDefault();
    focusNextLimsEnterField(focusOrder, currentKey, opts);
  };
}
