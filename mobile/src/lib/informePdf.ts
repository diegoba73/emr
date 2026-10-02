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

/** Descarga el PDF del informe y abre el diálogo de compartir/guardar. */
export async function downloadInformePdf(id: number): Promise<{ esParcial: boolean }> {
  const data = await api<PdfPayload>(`/informes/${id}/pdf/?format=base64`, 'GET', undefined, {
    timeoutMs: 60000,
  });
  if (!data?.base64) {
    throw new Error('El servidor no devolvió el PDF del informe.');
  }
  const filename = safeFilename(data.filename, id);
  const file = new File(Paths.cache, filename);
  file.create({ overwrite: true });
  file.write(data.base64, { encoding: EncodingType.Base64 });
  if (!(await Sharing.isAvailableAsync())) {
    throw new Error('Este dispositivo no permite compartir el PDF. Abrí el archivo desde archivos del sistema.');
  }
  await Sharing.shareAsync(file.uri, {
    mimeType: 'application/pdf',
    dialogTitle: data.es_parcial ? 'Informe parcial (PDF)' : 'Informe de laboratorio (PDF)',
    UTI: 'com.adobe.pdf',
  });
  return { esParcial: Boolean(data.es_parcial) };
}
