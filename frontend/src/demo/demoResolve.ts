import { pacientesService } from '../services/pacientes';
import { listSolicitudesExamen } from '../services/limsApi';
import { MKTG_LIMS_FINAL, MKTG_LIMS_VIVO, MKTG_PORTAL_PACIENTE_DNI } from './tourSteps';

/** Resuelve el id del paciente demo (portal / HC). */
export async function resolveDemoPatientId(): Promise<number | null> {
  try {
    const fromOrden = await listSolicitudesExamen({ numero: MKTG_LIMS_FINAL });
    const pId = fromOrden[0]?.paciente;
    if (typeof pId === 'number' && Number.isFinite(pId)) return pId;
  } catch {
    /* ignore */
  }
  try {
    const fromVivo = await listSolicitudesExamen({ numero: MKTG_LIMS_VIVO });
    const pId = fromVivo[0]?.paciente;
    if (typeof pId === 'number' && Number.isFinite(pId)) return pId;
  } catch {
    /* ignore */
  }
  try {
    const list = await pacientesService.search(MKTG_PORTAL_PACIENTE_DNI);
    const match = (list || []).find(
      (p) => (p.dni || '').toUpperCase() === MKTG_PORTAL_PACIENTE_DNI
    );
    if (match?.id != null) return Number(match.id);
    if (list?.[0]?.id != null) return Number(list[0].id);
  } catch {
    /* ignore */
  }
  return null;
}

/** Resuelve id de SolicitudExamen por número LAB-MKTG-…. */
export async function resolveDemoLimsOrdenId(
  numero: string = MKTG_LIMS_VIVO
): Promise<number | null> {
  try {
    const rows = await listSolicitudesExamen({ numero });
    const match = rows.find((r) => (r.numero || '').toUpperCase() === numero.toUpperCase());
    if (match?.id != null) return Number(match.id);
    if (rows[0]?.id != null) return Number(rows[0].id);
  } catch {
    /* ignore */
  }
  return null;
}
