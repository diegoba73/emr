import { File, Paths } from 'expo-file-system';
import * as Sharing from 'expo-sharing';
import { ApiError } from './client';
import { getApiBase, getToken } from './api';

function safeFilename(name: string | undefined, id: number): string {
  const raw = (name || `informe-${id}.pdf`).replace(/[/\\?%*:|"<>]/g, '_');
  return raw.toLowerCase().endsWith('.pdf') ? raw : `${raw}.pdf`;
}

function isShareCanceled(error: unknown): boolean {
  const msg = error instanceof Error ? error.message : String(error ?? '');
  return /cancel|dismiss|abort|user did not share|sharing.*fail/i.test(msg);
}

function messageFromHttp(status: number, bodyText: string): string {
  try {
    const data = JSON.parse(bodyText) as { detail?: unknown; error?: unknown };
    if (typeof data.detail === 'string' && data.detail.trim()) return data.detail.trim();
    if (typeof data.error === 'string' && data.error.trim()) return data.error.trim();
  } catch {
    /* cuerpo no JSON */
  }
  if (status === 401) return 'La sesión venció. Iniciá sesión nuevamente.';
  if (status === 403) {
    return 'El PDF solo está disponible cuando el informe está validado (FINALIZADO).';
  }
  if (status === 404) return 'Informe no encontrado.';
  return 'No se pudo descargar el PDF del informe.';
}

/** Descarga el PDF binario del informe y abre el diálogo de compartir/guardar. */
export async function downloadInformePdf(id: number): Promise<void> {
  const base = getApiBase().replace(/\/$/, '');
  if (!base.startsWith('https://') && !base.startsWith('http://')) {
    throw new ApiError('La conexión segura de la app todavía no está configurada.', 0);
  }
  const token = getToken();
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 90000);
  let response: Response;
  try {
    response = await fetch(`${base}/informes/${id}/pdf/`, {
      method: 'GET',
      redirect: 'error',
      signal: controller.signal,
      headers: {
        Accept: 'application/pdf',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  } catch {
    throw new ApiError('No se pudo conectar. Verificá tu conexión e intentá nuevamente.', 0);
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    const bodyText = await response.text().catch(() => '');
    throw new ApiError(messageFromHttp(response.status, bodyText), response.status);
  }

  const buffer = await response.arrayBuffer();
  if (!buffer.byteLength) {
    throw new Error('El servidor devolvió un PDF vacío.');
  }
  const bytes = new Uint8Array(buffer);
  // Content-Disposition: attachment; filename="informe-lims-solicitud-123.pdf"
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = /filename="?([^"]+)"?/i.exec(disposition);
  const filename = safeFilename(match?.[1], id);

  let file: File;
  try {
    file = new File(Paths.cache, filename);
    file.create({ overwrite: true, intermediates: true });
    file.write(bytes);
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
      dialogTitle: 'Informe de laboratorio (PDF)',
      UTI: 'com.adobe.pdf',
    });
  } catch (error) {
    if (!isShareCanceled(error)) {
      throw new Error(
        error instanceof Error
          ? `No se pudo abrir el menú para guardar el PDF: ${error.message}`
          : 'No se pudo abrir el menú para guardar el PDF.'
      );
    }
  }
}
