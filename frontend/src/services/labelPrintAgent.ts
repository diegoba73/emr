/**
 * Agente local de impresión ZPL (USB) en la PC del operador.
 * Escucha solo en 127.0.0.1 — no usa la impresora del servidor.
 */
import { postMuestraConfirmarImpresionEtiqueta, postMuestraImprimirEtiqueta } from './limsApi';
import {
  postEstudioMicroConfirmarImpresionEtiqueta,
  postEstudioMicroImprimirEtiqueta,
} from './limsMicroApi';

export const LABEL_PRINT_AGENT_URL = 'http://127.0.0.1:18181';

const AGENT_TIMEOUT_MS = 8000;

export const AGENT_DOWN_MSG =
  'En esta PC no hay agente de impresión. Instálelo solo donde la impresora USB esté conectada.';

export const NO_PRINTER_MSG = 'No se encontró impresora de etiquetas en esta PC.';

export const PRINT_UNCERTAIN_MSG =
  'No se pudo confirmar la impresión. Verifique la impresora antes de reimprimir.';

export type LabelPrintAgentErrorCode = 'agent_down' | 'no_printer' | 'print_failed';

export class LabelPrintAgentError extends Error {
  code: LabelPrintAgentErrorCode;

  constructor(code: LabelPrintAgentErrorCode, message: string) {
    super(message);
    this.name = 'LabelPrintAgentError';
    this.code = code;
  }
}

export type LabelPrintAgentHealth = {
  reachable: boolean;
  ok: boolean;
  printer: string | null;
};

async function fetchAgent(path: string, init: RequestInit, timeoutMs = AGENT_TIMEOUT_MS): Promise<Response> {
  const ctrl = new AbortController();
  const t = window.setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    return await fetch(`${LABEL_PRINT_AGENT_URL}${path}`, {
      ...init,
      signal: ctrl.signal,
    });
  } catch (e) {
    const name = (e as { name?: string })?.name;
    if (name === 'AbortError') {
      throw new LabelPrintAgentError('agent_down', AGENT_DOWN_MSG);
    }
    throw new LabelPrintAgentError('agent_down', AGENT_DOWN_MSG);
  } finally {
    window.clearTimeout(t);
  }
}

export async function pingLabelPrintAgent(): Promise<LabelPrintAgentHealth> {
  try {
    const res = await fetchAgent('/health', { method: 'GET' });
    if (!res.ok) {
      return { reachable: true, ok: false, printer: null };
    }
    const body = (await res.json()) as { ok?: boolean; printer?: string | null; error?: string };
    const printer = typeof body.printer === 'string' && body.printer.trim() ? body.printer.trim() : null;
    return { reachable: true, ok: Boolean(body.ok && printer), printer };
  } catch (e) {
    if (e instanceof LabelPrintAgentError) {
      return { reachable: false, ok: false, printer: null };
    }
    return { reachable: false, ok: false, printer: null };
  }
}

export async function printZplViaLocalAgent(zpl: string): Promise<void> {
  const payload = (zpl || '').trim();
  if (!payload) {
    throw new LabelPrintAgentError('print_failed', PRINT_UNCERTAIN_MSG);
  }
  let res: Response;
  try {
    res = await fetchAgent('/print', {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
      body: payload,
    });
  } catch (e) {
    if (e instanceof LabelPrintAgentError) throw e;
    throw new LabelPrintAgentError('agent_down', AGENT_DOWN_MSG);
  }
  if (res.status === 400) {
    let code = '';
    try {
      const body = (await res.json()) as { error?: string };
      code = (body.error || '').trim();
    } catch {
      code = '';
    }
    if (code === 'no_printer') {
      throw new LabelPrintAgentError('no_printer', NO_PRINTER_MSG);
    }
    throw new LabelPrintAgentError('print_failed', PRINT_UNCERTAIN_MSG);
  }
  if (!res.ok) {
    throw new LabelPrintAgentError('print_failed', PRINT_UNCERTAIN_MSG);
  }
}

/**
 * Prepara ZPL en el servidor, imprime en la PC local y confirma auditoría.
 * Falla rápido si el agente o la impresora USB no están en esta máquina.
 */
export async function imprimirEtiquetaMuestraLocal(muestraId: number): Promise<void> {
  const health = await pingLabelPrintAgent();
  if (!health.reachable) {
    throw new LabelPrintAgentError('agent_down', AGENT_DOWN_MSG);
  }
  if (!health.ok || !health.printer) {
    throw new LabelPrintAgentError('no_printer', NO_PRINTER_MSG);
  }
  const prepared = await postMuestraImprimirEtiqueta(muestraId);
  await printZplViaLocalAgent(prepared.zpl || '');
  try {
    await postMuestraConfirmarImpresionEtiqueta(muestraId, prepared.profile);
  } catch {
    // La etiqueta ya salió; no pedir reimpresión por un fallo de auditoría.
  }
}

/**
 * Prepara ZPL de estudio micro, imprime en la PC local y confirma auditoría.
 * Misma impresora USB / agente que lab clínico.
 */
export async function imprimirEtiquetaEstudioMicroLocal(estudioId: number): Promise<void> {
  const health = await pingLabelPrintAgent();
  if (!health.reachable) {
    throw new LabelPrintAgentError('agent_down', AGENT_DOWN_MSG);
  }
  if (!health.ok || !health.printer) {
    throw new LabelPrintAgentError('no_printer', NO_PRINTER_MSG);
  }
  const prepared = await postEstudioMicroImprimirEtiqueta(estudioId);
  await printZplViaLocalAgent(prepared.zpl || '');
  try {
    await postEstudioMicroConfirmarImpresionEtiqueta(estudioId, prepared.profile);
  } catch {
    // La etiqueta ya salió; no pedir reimpresión por un fallo de auditoría.
  }
}
