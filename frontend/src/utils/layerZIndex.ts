import { useMemo } from 'react';
import { createTheme, useTheme } from '@mui/material/styles';

/**
 * Capas UI: el drawer clínico usa z-index 1400 (por encima del modal MUI default 1300).
 * Los Dialog hijos del drawer deben ir en slotProps.root (MUI 7) para quedar clickeables.
 */
export const Z_CLINICAL_DRAWER = 1400;
export const Z_DIALOG_OVER_CLINICAL_DRAWER = 1700;
export const Z_MENU_OVER_CLINICAL_DIALOG = 1800;

/** Props para Dialog dentro del drawer clínico (MUI 7: z-index en slotProps.root). */
export const clinicalDrawerDialogProps = {
  disableScrollLock: true,
  slotProps: {
    root: {
      sx: { zIndex: Z_DIALOG_OVER_CLINICAL_DRAWER },
    },
    paper: {
      sx: { overflow: 'visible' },
    },
  },
} as const;

/** Contenido de diálogo clínico: permite menús inline sin recorte. */
export const clinicalDrawerDialogContentSx = {
  overflow: 'visible',
} as const;

/** Diálogo clínico con lista larga: contenido con scroll y acciones fijas abajo. */
export const scrollableClinicalDialogPaperSx = {
  maxHeight: 'min(92vh, 920px)',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
} as const;

export const scrollableClinicalDialogContentSx = {
  flex: '1 1 auto',
  overflowY: 'auto',
  minHeight: 0,
  overscrollBehavior: 'contain',
} as const;

export const scrollableClinicalDialogActionsSx = {
  flexShrink: 0,
  borderTop: 1,
  borderColor: 'divider',
  bgcolor: 'background.paper',
  px: 3,
  py: 1.5,
} as const;

/** Props para Autocomplete/Popper dentro de un Dialog sobre el drawer clínico. */
export const clinicalDrawerAutocompleteSlotProps = {
  popper: {
    disablePortal: true,
    placement: 'bottom-start' as const,
    sx: { zIndex: Z_MENU_OVER_CLINICAL_DIALOG },
  },
} as const;

/** Props para Select/Menu dentro de un Dialog sobre el drawer clínico. */
export const clinicalDrawerSelectMenuProps = {
  MenuProps: {
    disablePortal: true,
    disableScrollLock: true,
    slotProps: {
      paper: {
        sx: { zIndex: Z_MENU_OVER_CLINICAL_DIALOG, maxHeight: 280 },
      },
    },
  },
} as const;

/** Tema anidado: Popover/Menu del Select hereda z-index por encima del drawer. */
export function useClinicalDrawerDialogTheme() {
  const outerTheme = useTheme();
  return useMemo(
    () =>
      createTheme(outerTheme, {
        zIndex: {
          ...outerTheme.zIndex,
          modal: Z_DIALOG_OVER_CLINICAL_DRAWER,
        },
      }),
    [outerTheme]
  );
}
