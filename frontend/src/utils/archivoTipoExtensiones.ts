/** Extensiones aceptadas por tipo_archivo (alineado con backend validators). */
export const ACCEPT_BY_TIPO_ARCHIVO: Record<string, string> = {
  PDF: '.pdf,application/pdf',
  FOTO_CLINICA: '.jpg,.jpeg,.png,.webp,.tif,.tiff,image/jpeg,image/png,image/webp',
  RAYOS_X: '.jpg,.jpeg,.png,.tif,.tiff,.webp,.dcm,.pdf,image/*',
  TOMOGRAFIA: '.jpg,.jpeg,.png,.tif,.tiff,.webp,.dcm,.nii,.gz,.pdf,image/*',
  RESONANCIA: '.jpg,.jpeg,.png,.tif,.tiff,.webp,.dcm,.nii,.gz,.pdf,image/*',
  ULTRASONIDO: '.jpg,.jpeg,.png,.tif,.tiff,.webp,.dcm,.pdf,image/*',
  DICOM: '.dcm',
  NIFTI: '.nii,.nii.gz',
  PATOLOGIA: '.tif,.tiff,.png,.jpg,.jpeg,image/*',
  OTRO: '.pdf,.doc,.docx,.txt,.jpg,.jpeg,.png,.webp,.tif,.tiff,.dcm,.nii,.nii.gz,image/*',
};

export const EXTENSIONES_POR_TIPO: Record<string, string[]> = {
  PDF: ['.pdf'],
  FOTO_CLINICA: ['.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff'],
  RAYOS_X: ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.dcm', '.pdf'],
  TOMOGRAFIA: ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.dcm', '.nii', '.nii.gz', '.pdf'],
  RESONANCIA: ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.dcm', '.nii', '.nii.gz', '.pdf'],
  ULTRASONIDO: ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.dcm', '.pdf'],
  DICOM: ['.dcm'],
  NIFTI: ['.nii', '.nii.gz'],
  PATOLOGIA: ['.tif', '.tiff', '.png', '.jpg', '.jpeg'],
  OTRO: [
    '.pdf',
    '.doc',
    '.docx',
    '.txt',
    '.jpg',
    '.jpeg',
    '.png',
    '.webp',
    '.tif',
    '.tiff',
    '.dcm',
    '.nii',
    '.nii.gz',
  ],
};

export function extensionArchivo(nombre: string): string {
  const lower = (nombre || '').toLowerCase();
  if (lower.endsWith('.nii.gz')) return '.nii.gz';
  const i = lower.lastIndexOf('.');
  return i >= 0 ? lower.slice(i) : '';
}

export function archivoCompatibleConTipo(nombreArchivo: string, tipo: string): boolean {
  const ext = extensionArchivo(nombreArchivo);
  const allowed = EXTENSIONES_POR_TIPO[tipo] || EXTENSIONES_POR_TIPO.OTRO;
  return allowed.includes(ext);
}

export function mensajeExtensionesTipo(tipo: string): string {
  const allowed = EXTENSIONES_POR_TIPO[tipo] || EXTENSIONES_POR_TIPO.OTRO;
  return allowed.join(', ');
}
