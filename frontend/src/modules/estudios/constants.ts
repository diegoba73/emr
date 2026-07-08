import type { EstudioEstado, EstudioModalidad } from '../../types/estudios';

export const MODALIDAD_OPTIONS: { value: EstudioModalidad; label: string }[] = [
  { value: 'IMAGEN_RX', label: 'Rayos X' },
  { value: 'IMAGEN_TC', label: 'Tomografía' },
  { value: 'IMAGEN_RM', label: 'Resonancia' },
  { value: 'IMAGEN_US', label: 'Ultrasonido' },
  { value: 'PDF_INFORME_EXTERNO', label: 'PDF / informe externo' },
  { value: 'OTRO', label: 'Otro' },
];

export const ESTADO_LABELS: Record<EstudioEstado, string> = {
  SOLICITADO: 'Solicitado',
  CONFIRMADO: 'Confirmado',
  REALIZADO: 'Realizado',
  INFORMADO: 'Informado',
  VALIDADO: 'Validado',
  ENTREGADO: 'Entregado',
  ANULADO: 'Anulado',
};

export const ESTADO_CHIP_COLOR: Record<
  EstudioEstado,
  'default' | 'info' | 'warning' | 'success' | 'error' | 'primary' | 'secondary'
> = {
  SOLICITADO: 'info',
  CONFIRMADO: 'success',
  REALIZADO: 'primary',
  INFORMADO: 'warning',
  VALIDADO: 'secondary',
  ENTREGADO: 'success',
  ANULADO: 'error',
};

export const ORIGEN_OPTIONS = [
  { value: 'INTERNO', label: 'Interno' },
  { value: 'EXTERNO', label: 'Externo' },
  { value: 'IMPORTADO_HISTORICO', label: 'Importado histórico' },
];

export const ARCHIVO_ROL_OPTIONS = [
  { value: 'IMAGEN', label: 'Imagen' },
  { value: 'INFORME_ESCANEADO', label: 'Informe escaneado' },
  { value: 'DICOM_ZIP', label: 'DICOM / ZIP' },
  { value: 'OTRO', label: 'Otro' },
];
