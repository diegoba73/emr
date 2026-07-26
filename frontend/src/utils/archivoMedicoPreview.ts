import { ArchivoMedico } from '../types';

export type ArchivoPreviewKind = 'pdf' | 'image' | 'unsupported';

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tif', 'tiff']);

export function getArchivoFileName(archivo: {
  archivo_nombre?: string | null;
  titulo?: string | null;
}): string {
  return archivo.archivo_nombre || archivo.titulo || 'archivo';
}

export function guessArchivoMimeType(
  filename: string,
  tipoArchivo?: string | null
): string {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  if (ext === 'pdf') return 'application/pdf';
  if (ext === 'jpg' || ext === 'jpeg') return 'image/jpeg';
  if (ext === 'png') return 'image/png';
  if (ext === 'gif') return 'image/gif';
  if (ext === 'webp') return 'image/webp';
  if (ext === 'tif' || ext === 'tiff') return 'image/tiff';
  if (ext === 'bmp') return 'image/bmp';
  if (tipoArchivo === 'PDF') return 'application/pdf';
  if (
    tipoArchivo &&
    ['FOTO_CLINICA', 'RAYOS_X', 'TOMOGRAFIA', 'RESONANCIA', 'ULTRASONIDO', 'PATOLOGIA'].includes(tipoArchivo)
  ) {
    return 'image/jpeg';
  }
  return 'application/octet-stream';
}

export function getArchivoPreviewKind(
  filename: string,
  tipoArchivo?: string | null
): ArchivoPreviewKind {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  if (ext === 'pdf' || tipoArchivo === 'PDF') return 'pdf';
  if (IMAGE_EXTENSIONS.has(ext)) return 'image';
  if (
    tipoArchivo &&
    ['FOTO_CLINICA', 'RAYOS_X', 'TOMOGRAFIA', 'RESONANCIA', 'ULTRASONIDO', 'PATOLOGIA'].includes(tipoArchivo)
  ) {
    return 'image';
  }
  return 'unsupported';
}

/** Infiere tipo_archivo de ArchivoMedico a partir del nombre del fichero. */
export function inferTipoArchivoFromFileName(filename: string): ArchivoMedico['tipo_archivo'] {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  if (ext === 'pdf') return 'PDF';
  if (ext === 'dcm') return 'DICOM';
  if (['nii', 'gz'].includes(ext) || filename.toLowerCase().endsWith('.nii.gz')) return 'NIFTI';
  if (IMAGE_EXTENSIONS.has(ext)) return 'FOTO_CLINICA';
  if (ext === 'zip') return 'OTRO';
  return 'OTRO';
}

export function normalizePreviewBlob(blob: Blob, mimeType: string): Blob {
  if (blob.type && blob.type !== 'application/octet-stream') {
    return blob;
  }
  return new Blob([blob], { type: mimeType });
}
