import { ArchivoMedico } from '../types';

export type ArchivoPreviewKind = 'pdf' | 'image' | 'unsupported';

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'tif', 'tiff']);

export function getArchivoFileName(archivo: Pick<ArchivoMedico, 'archivo_nombre' | 'titulo'>): string {
  return archivo.archivo_nombre || archivo.titulo || 'archivo';
}

export function guessArchivoMimeType(
  filename: string,
  tipoArchivo?: ArchivoMedico['tipo_archivo']
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
  tipoArchivo?: ArchivoMedico['tipo_archivo']
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

export function normalizePreviewBlob(blob: Blob, mimeType: string): Blob {
  if (blob.type && blob.type !== 'application/octet-stream') {
    return blob;
  }
  return new Blob([blob], { type: mimeType });
}
