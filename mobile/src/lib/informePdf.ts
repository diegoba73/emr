import { api } from './api';
import { EncodingType, File, Paths } from 'expo-file-system';
import * as Sharing from 'expo-sharing';

type PdfPayload = {
  filename: string;
  base64: string;
  es_parcial?: boolean;
};

function safeFilename(name: string | undefined, id: number): string {
  const raw = (name || `informe-${id}.pdf`).replace(/[/\\?%*:|"<>]/g, '_');
  return raw.toLowerCase().endsWith('.pdf') ? raw : `${raw}.pdf`;
}

function isShareCanceled(error: unknown): boolean {
  const msg = error instanceof Error ? error.message : String(error ?? '');
  return /cancel|dismiss|abort|user did not share|sharing.*fail/i.test(msg);
}

/** Descarga el PDF del informe y abre el diálogo de compartir/guardar. */
export async function downloadInformePdf(id: number): Promise<{ esParcial: boolean }> {
  const data = await api<PdfPayload>(`/informes/${id}/pdf/?as_base64=1`, 'GET', undefined, {
    timeoutMs: 90000,
  });
  if (!data?.base64 || typeof data.base64 !== 'string') {
    throw new Error('El servidor no devolvió el PDF del informe.');
  }
  const filename = safeFilename(data.filename, id);
  let file: File;
  try {
    file = new File(Paths.cache, filename);
    file.create({ overwrite: true });
    // Escribir bytes binarios desde base64 (API nueva de expo-file-system).
    file.write(data.base64, { encoding: EncodingType.Base64 });
  } catch (error) {
    const detail = error instanceof Error ? error.message : 'error de almacenamiento';
    throw new Error(`No se pudo guardar el PDF en el dispositivo (${detail}).`);
  }
  if (!(await Sharing.isAvailableAsync())) {
    throw new Error(
      'Este dispositivo no permite compartir el PDF. El archivo quedó en la caché de la app.'
    );
  }
  try {
    await Sharing.shareAsync(file.uri, {
      mimeType: 'application/pdf',
      dialogTitle: data.es_parcial ? 'Informe parcial (PDF)' : 'Informe de laboratorio (PDF)',
      UTI: 'com.adobe.pdf',
    });
  } catch (error) {
    // En Android, cerrar el sheet sin compartir suele rechazar la Promise.
    if (!isShareCanceled(error)) {
      throw new Error(
        error instanceof Error
          ? `No se pudo abrir el menú para guardar el PDF: ${error.message}`
          : 'No se pudo abrir el menú para guardar el PDF.'
      );
    }
  }
  return { esParcial: Boolean(data.es_parcial) };
}
