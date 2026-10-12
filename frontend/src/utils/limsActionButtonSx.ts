import { alpha, type SxProps, type Theme } from '@mui/material/styles';

/** Acciones LIMS (lista / detalle): tipografía y tamaño unificados. */
export const limsActionBtnSx: SxProps<Theme> = {
  fontSize: '0.8125rem',
  fontWeight: 600,
  lineHeight: 1.25,
  px: 1.5,
  py: 0.5,
  minHeight: 30,
  borderRadius: '8px',
};

/**
 * Outlined primario (azul/celeste): mismo lenguaje visual que Cancelar
 * (borde + texto, sin relleno sólido).
 */
export const limsActionBtnSoftSx: SxProps<Theme> = {
  ...limsActionBtnSx,
  color: (t) => (t.palette.mode === 'dark' ? t.palette.info.light : t.palette.primary.main),
  borderColor: (t) =>
    alpha(t.palette.mode === 'dark' ? t.palette.info.light : t.palette.primary.main, 0.55),
  bgcolor: 'transparent',
  '&:hover': {
    bgcolor: (t) =>
      alpha(t.palette.mode === 'dark' ? t.palette.info.main : t.palette.primary.main, 0.12),
    borderColor: (t) => (t.palette.mode === 'dark' ? t.palette.info.light : t.palette.primary.main),
  },
};

/** Outlined énfasis (acción principal azul): borde un poco más marcado. */
export const limsActionBtnPrimaryOutlineSx: SxProps<Theme> = {
  ...limsActionBtnSoftSx,
  borderColor: (t) => (t.palette.mode === 'dark' ? t.palette.info.light : t.palette.primary.main),
  borderWidth: 1.5,
  '&:hover': {
    bgcolor: (t) =>
      alpha(t.palette.mode === 'dark' ? t.palette.info.main : t.palette.primary.main, 0.16),
    borderColor: (t) => (t.palette.mode === 'dark' ? t.palette.info.light : t.palette.primary.dark),
    borderWidth: 1.5,
  },
};

/** Outlined éxito (Validar): misma lógica que Cancelar, en verde. */
export const limsActionBtnSuccessSx: SxProps<Theme> = {
  ...limsActionBtnSx,
  color: 'success.main',
  borderColor: (t) => alpha(t.palette.success.main, t.palette.mode === 'dark' ? 0.7 : 0.6),
  bgcolor: 'transparent',
  borderWidth: 1.5,
  '&:hover': {
    bgcolor: (t) => alpha(t.palette.success.main, t.palette.mode === 'dark' ? 0.14 : 0.1),
    borderColor: 'success.main',
    borderWidth: 1.5,
  },
  '&.Mui-disabled': {
    borderColor: (t) => alpha(t.palette.success.main, 0.25),
    color: (t) => alpha(t.palette.success.main, 0.4),
  },
};

/** Outlined error (Cancelar): tamaño alineado al resto. */
export const limsActionBtnErrorSx: SxProps<Theme> = {
  ...limsActionBtnSx,
  color: 'error.main',
  borderColor: (t) => alpha(t.palette.error.main, t.palette.mode === 'dark' ? 0.7 : 0.55),
  bgcolor: 'transparent',
  '&:hover': {
    bgcolor: (t) => alpha(t.palette.error.main, t.palette.mode === 'dark' ? 0.14 : 0.08),
    borderColor: 'error.main',
  },
};
