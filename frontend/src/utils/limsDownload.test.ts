import { AxiosError } from 'axios';
import { triggerBlobDownload } from '../services/estudiosComplementariosApi';
import {
  assertValidSolicitudId,
  formatLimsPdfDownloadError,
  informeLimsPdfFilename,
} from './limsDownload';

describe('informeLimsPdfFilename', () => {
  it('genera filename seguro sin PHI', () => {
    expect(informeLimsPdfFilename(42)).toBe('informe-lims-solicitud-42.pdf');
    expect(informeLimsPdfFilename(42)).not.toMatch(/paciente|dni|barra/i);
  });
});

describe('assertValidSolicitudId', () => {
  it('rechaza ids inválidos', () => {
    expect(() => assertValidSolicitudId(0)).toThrow('Identificador de solicitud inválido.');
    expect(() => assertValidSolicitudId(-1)).toThrow();
    expect(() => assertValidSolicitudId(1.5)).toThrow();
  });

  it('acepta id entero positivo', () => {
    expect(() => assertValidSolicitudId(1)).not.toThrow();
  });
});

describe('formatLimsPdfDownloadError', () => {
  it('mapea 401/403/404/500 sin exponer payload', () => {
    const mk = (status: number) => {
      const err = new AxiosError('fail');
      err.response = {
        status,
        data: { detail: 'Paciente Juan Pérez DNI 12345', paciente: 'secreto' },
        statusText: '',
        headers: {},
        config: { headers: {} },
      } as NonNullable<typeof err.response>;
      return err;
    };
    expect(formatLimsPdfDownloadError(mk(401))).toBe(
      'La sesión no está activa. Iniciá sesión nuevamente.'
    );
    expect(formatLimsPdfDownloadError(mk(403))).toBe(
      'No tenés permisos para descargar este informe.'
    );
    expect(formatLimsPdfDownloadError(mk(404))).toBe(
      'El informe solicitado no está disponible.'
    );
    expect(formatLimsPdfDownloadError(mk(500))).toBe(
      'No se pudo generar el informe. Intentá nuevamente.'
    );
  });

  it('no expone detail ni ax.message para otros errores', () => {
    const err = new AxiosError('Network Error');
    err.response = {
      status: 400,
      data: { detail: 'Muestra rechazada por hemólisis' },
      statusText: '',
      headers: {},
      config: { headers: {} },
    } as NonNullable<typeof err.response>;
    expect(formatLimsPdfDownloadError(err)).toBe(
      'No se pudo descargar el informe. Intentá nuevamente.'
    );
    expect(formatLimsPdfDownloadError(err)).not.toContain('hemólisis');
    expect(formatLimsPdfDownloadError(err)).not.toContain('Network Error');
  });
});

describe('triggerBlobDownload', () => {
  it('revoca object URL tras descarga', async () => {
    const revoke = jest.fn();
    const create = jest.fn(() => 'blob:test-url');
    const click = jest.fn();
    const remove = jest.fn();
    const appendChild = jest.fn();

    window.URL.createObjectURL = create;
    window.URL.revokeObjectURL = revoke;

    const link = { href: '', download: '', click, remove } as unknown as HTMLAnchorElement;
    jest.spyOn(document, 'createElement').mockReturnValue(link);
    jest.spyOn(document.body, 'appendChild').mockImplementation(appendChild);

    await triggerBlobDownload(new Blob(['%PDF']), 'informe-lims-solicitud-1.pdf');

    expect(create).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
    expect(remove).toHaveBeenCalled();
    expect(revoke).toHaveBeenCalledWith('blob:test-url');
  });
});
