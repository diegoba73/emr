import {
  AGENT_DOWN_MSG,
  LabelPrintAgentError,
  NO_PRINTER_MSG,
  imprimirEtiquetaMuestraLocal,
  pingLabelPrintAgent,
  printZplViaLocalAgent,
} from './labelPrintAgent';

const mockPrepare = jest.fn();
const mockConfirm = jest.fn();

jest.mock('./limsApi', () => ({
  postMuestraImprimirEtiqueta: (...args: unknown[]) => mockPrepare(...args),
  postMuestraConfirmarImpresionEtiqueta: (...args: unknown[]) => mockConfirm(...args),
}));

describe('labelPrintAgent', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockPrepare.mockResolvedValue({
      muestra_id: 1,
      profile: '3nstar_ldt114_203_40x23',
      resultado: 'prepared',
      zpl: '^XA^XZ',
    });
    mockConfirm.mockResolvedValue({
      muestra_id: 1,
      profile: '3nstar_ldt114_203_40x23',
      resultado: 'ok',
      transport: 'local_agent',
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('ping: agente caído', async () => {
    jest.spyOn(global, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'));
    const h = await pingLabelPrintAgent();
    expect(h.reachable).toBe(false);
    expect(h.ok).toBe(false);
  });

  it('ping: sin impresora', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ ok: false, printer: null, error: 'no_printer' }),
    } as Response);
    const h = await pingLabelPrintAgent();
    expect(h.reachable).toBe(true);
    expect(h.ok).toBe(false);
  });

  it('printZpl: 400 no_printer', async () => {
    jest.spyOn(global, 'fetch').mockResolvedValue({
      ok: false,
      status: 400,
      json: async () => ({ error: 'no_printer' }),
    } as Response);
    await expect(printZplViaLocalAgent('^XA^XZ')).rejects.toMatchObject({
      code: 'no_printer',
      message: NO_PRINTER_MSG,
    });
  });

  it('imprimirEtiquetaMuestraLocal: no llama al servidor si no hay agente', async () => {
    jest.spyOn(global, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'));
    await expect(imprimirEtiquetaMuestraLocal(9)).rejects.toBeInstanceOf(LabelPrintAgentError);
    expect(mockPrepare).not.toHaveBeenCalled();
    expect(mockConfirm).not.toHaveBeenCalled();
  });

  it('imprimirEtiquetaMuestraLocal: prepare + print + confirmar', async () => {
    jest.spyOn(global, 'fetch').mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith('/health')) {
        return {
          ok: true,
          json: async () => ({ ok: true, printer: '3nStar LDT114' }),
        } as Response;
      }
      if (url.endsWith('/print')) {
        return { ok: true, status: 200, json: async () => ({ ok: true }) } as Response;
      }
      throw new Error(`unexpected ${url}`);
    });
    await imprimirEtiquetaMuestraLocal(9);
    expect(mockPrepare).toHaveBeenCalledWith(9);
    expect(mockConfirm).toHaveBeenCalledWith(9, '3nstar_ldt114_203_40x23');
  });

  it('agente down message estable', () => {
    expect(AGENT_DOWN_MSG.toLowerCase()).toContain('agente');
    expect(NO_PRINTER_MSG.toLowerCase()).toContain('impresora');
  });
});
