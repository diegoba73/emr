import { api } from './api';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';

type PdfPayload = {
  filename: string;
  base64: string;
  es_parcial?: boolean;
};

/** Descarga el PDF del informe y abre el diálogo de compartir/guardar. */
export async function downloadInformePdf(id: number): Promise<{ esParcial: boolean }> {
  const data = await api<PdfPayload>(`/informes/${id}/pdf/?format=base64`);
  const dir = FileSystem.cacheDirectory || FileSystem.documentDirectory;
  if (!dir) throw new Error('No se pudo preparar el archivo en este dispositivo.');
  const path = `${dir}${data.filename || `informe-${id}.pdf`}`;
  await FileSystem.writeAsStringAsync(path, data.base64, {
    encoding: FileSystem.EncodingType.Base64,
  });
  if (!(await Sharing.isAvailableAsync())) {
    throw new Error('Este dispositivo no permite compartir el PDF. Abrí el archivo desde archivos del sistema.');
  }
  await Sharing.shareAsync(path, {
    mimeType: 'application/pdf',
    dialogTitle: data.es_parcial ? 'Informe parcial (PDF)' : 'Informe de laboratorio (PDF)',
    UTI: 'com.adobe.pdf',
  });
  return { esParcial: Boolean(data.es_parcial) };
}
