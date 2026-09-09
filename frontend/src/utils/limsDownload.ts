import { AxiosError } from 'axios';

/** Nombre de descarga seguro (sin PHI ni DNI). */
export function informeLimsPdfFilename(solicitudId: number): string {
  return `informe-lims-solicitud-${solicitudId}.pdf`;
}

export function informeMicroPdfFilename(estudioId: number): string {
  return `informe-micro-${estudioId}.pdf`;
}

export function assertValidSolicitudId(solicitudId: number): void {
  if (!Number.isInteger(solicitudId) || solicitudId <= 0) {
    throw new Error('Identificador de solicitud inválido.');
  }
}

/**
 * Abre el diálogo de impresión del navegador con un PDF (sin descargar archivo).
 * Usa un iframe oculto; demora el revoke del blob para no cortar el print dialog.
 */
export async function printPdfBlob(blob: Blob): Promise<void> {
  const pdfBlob =
    blob.type === 'application/pdf' ? blob : new Blob([blob], { type: 'application/pdf' });
  const url = window.URL.createObjectURL(pdfBlob);

  await new Promise<void>((resolve, reject) => {
    const iframe = document.createElement('iframe');
    iframe.setAttribute('title', 'Imprimir talón');
    iframe.style.position = 'fixed';
    iframe.style.right = '0';
    iframe.style.bottom = '0';
    iframe.style.width = '0';
    iframe.style.height = '0';
    iframe.style.border = '0';
    iframe.style.opacity = '0';
    iframe.style.pointerEvents = 'none';

    let settled = false;
    const cleanup = () => {
      window.setTimeout(() => {
        iframe.remove();
        window.URL.revokeObjectURL(url);
      }, 60_000);
    };

    const fail = (err: unknown) => {
      if (settled) return;
      settled = true;
      iframe.remove();
      window.URL.revokeObjectURL(url);
      reject(err instanceof Error ? err : new Error('No se pudo abrir la impresión.'));
    };

    iframe.onload = () => {
      window.setTimeout(() => {
        try {
          const win = iframe.contentWindow;
          if (!win) {
            fail(new Error('No se pudo abrir la impresión.'));
            return;
          }
          win.focus();
          win.print();
          if (!settled) {
            settled = true;
            cleanup();
            resolve();
          }
        } catch (e) {
          fail(e);
        }
      }, 250);
    };

    iframe.onerror = () => fail(new Error('No se pudo cargar el PDF para imprimir.'));
    document.body.appendChild(iframe);
    iframe.src = url;
  });
}

/** Mensajes de error para descarga PDF LIMS sin exponer cuerpo de respuesta ni ax.message. */
export function formatLimsPdfDownloadError(error: unknown): string {
  const ax = error as AxiosError;
  const status = ax.response?.status;
  if (status === 401) {
    return 'La sesión no está activa. Iniciá sesión nuevamente.';
  }
  if (status === 403) {
    return 'No tenés permisos para descargar este informe.';
  }
  if (status === 404) {
    return 'El informe solicitado no está disponible.';
  }
  if (status === 500) {
    return 'No se pudo generar el informe. Intentá nuevamente.';
  }
  if (error instanceof Error && error.message === 'Identificador de solicitud inválido.') {
    return 'No se pudo descargar el informe. Intentá nuevamente.';
  }
  return 'No se pudo descargar el informe. Intentá nuevamente.';
}
