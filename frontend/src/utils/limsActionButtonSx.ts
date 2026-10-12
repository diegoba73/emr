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

/** Secundario: mismo primary, fondo más claro que el contained. */
export const limsActionBtnSoftSx: SxProps<Theme> = {
  ...limsActionBtnSx,
  color: 'primary.main',
  bgcolor: (t) => alpha(t.palette.primary.main, t.palette.mode === 'dark' ? 0.2 : 0.12),
  borderColor: (t) => alpha(t.palette.primary.main, t.palette.mode === 'dark' ? 0.45 : 0.35),
  '&:hover': {
    bgcolor: (t) => alpha(t.palette.primary.main, t.palette.mode === 'dark' ? 0.3 : 0.2),
    borderColor: 'primary.main',
  },
};
