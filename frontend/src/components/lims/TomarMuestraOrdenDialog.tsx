import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import toast from 'react-hot-toast';
import type { MuestraTransaccional, SolicitudExamenLims } from '../../types/lims';
import {
  getAlertasFrecuenciaOrden,
  getSolicitudExamen,
  getTubosPreviewOrden,
  postTomarMuestraOrden,
  type AlertaFrecuenciaOrden,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import type { OrigenParaLugarExtraccion } from '../../utils/limsOrigenSolicitud';
import { origenExigeBloqueoFrecuenciaEnsayos } from '../../utils/limsOrigenSolicitud';
import AlertasFrecuenciaEtiquetasDialog from './AlertasFrecuenciaEtiquetasDialog';
import EtiquetasMuestrasZplOrdenDialog from './EtiquetasMuestrasZplOrdenDialog';
import QuitarExamenesOrdenDialog from './QuitarExamenesOrdenDialog';

export interface TomarMuestraOrdenDialogProps {
  open: boolean;
  orden: SolicitudExamenLims;
  muestrasExistentes?: MuestraTransaccional[];
  onClose: () => void;
  /** Tubos creados / orden actualizada (detalle). No implica «Esperando recepción» en UI. */
  onPrepared?: (orden: SolicitudExamenLims) => void;
  /**
   * Todas las etiquetas del diálogo se imprimieron.
   * En Pendientes: recién ahí pasar a «Esperando recepción».
   */
  onSuccess: (orden: SolicitudExamenLims) => void;
  origenOrden?: OrigenParaLugarExtraccion | null;
}

type Fase =
  | 'idle'
  | 'check_alertas'
  | 'alertas'
  | 'quitar'
  | 'preparing'
  | 'zpl'
  | 'sin_tubos'
  | 'error';

/**
 * «Imprimir etiquetas»: crea tubos (PENDIENTE_TOMA) y abre ZPL.
 * En ambulatorio, si hay alertas de frecuencia/cobertura, lab/bioquímico decide
 * continuar o quitar exámenes antes de preparar tubos.
 */
const TomarMuestraOrdenDialog: React.FC<TomarMuestraOrdenDialogProps> = ({
  open,
  orden,
  muestrasExistentes = [],
  onClose,
  onPrepared,
  onSuccess,
  origenOrden = null,
}) => {
  const [fase, setFase] = useState<Fase>('idle');
  const [prepError, setPrepError] = useState<string | null>(null);
  const [alertas, setAlertas] = useState<AlertaFrecuenciaOrden[]>([]);
  const [ordenTrabajo, setOrdenTrabajo] = useState<SolicitudExamenLims>(orden);
  const [ordenLista, setOrdenLista] = useState<SolicitudExamenLims | null>(null);
  const ordenPreparadaRef = useRef<SolicitudExamenLims | null>(null);
  const recepcionNotificadaRef = useRef(false);
  const skipAlertasRef = useRef(false);

  const origenEfectivo: OrigenParaLugarExtraccion = origenOrden || {
    origen_solicitud: orden.origen_solicitud,
    origen_solicitud_display: orden.origen_solicitud_display,
    procedencia_display: orden.procedencia_display,
  };

  const yaTieneMuestras =
    muestrasExistentes.length > 0 ||
    (ordenTrabajo.tubos_pendientes_extraccion?.length ?? 0) > 0 ||
    !!ordenTrabajo.fecha_toma_muestra;

  const prepareTubos = useCallback(async () => {
    setFase('preparing');
    setPrepError(null);
    try {
      if (!yaTieneMuestras) {
        const tubos = await getTubosPreviewOrden(ordenTrabajo.id);
        if (!tubos.length) {
          setFase('sin_tubos');
          return;
        }
      }
      const updated = await postTomarMuestraOrden(ordenTrabajo.id, {});
      ordenPreparadaRef.current = updated;
      setOrdenLista(updated);
      setOrdenTrabajo(updated);
      setFase('zpl');
      onPrepared?.(updated);
    } catch (e) {
      const msg = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarOrden);
      setPrepError(msg);
      setFase('error');
      toast.error(msg);
    }
  }, [yaTieneMuestras, ordenTrabajo.id, onPrepared]);

  const iniciarFlujo = useCallback(async () => {
    setPrepError(null);
    setAlertas([]);
    const origen = origenEfectivo.origen_solicitud || orden.origen_solicitud;
    const revisaAmbulatorio = !origenExigeBloqueoFrecuenciaEnsayos(origen);

    if (revisaAmbulatorio && !skipAlertasRef.current) {
      setFase('check_alertas');
      try {
        const data = await getAlertasFrecuenciaOrden(orden.id);
        if (data.aplica_revision_etiquetas && (data.alertas?.length ?? 0) > 0) {
          setAlertas(data.alertas);
          setFase('alertas');
          return;
        }
      } catch {
        // Si falla el check, no bloquear la impresión.
      }
    }
    skipAlertasRef.current = false;
    await prepareTubos();
  }, [origenEfectivo.origen_solicitud, orden.origen_solicitud, orden.id, prepareTubos]);

  useEffect(() => {
    if (!open) {
      setFase('idle');
      setOrdenLista(null);
      setAlertas([]);
      setPrepError(null);
      setOrdenTrabajo(orden);
      ordenPreparadaRef.current = null;
      recepcionNotificadaRef.current = false;
      skipAlertasRef.current = false;
      return;
    }

    setOrdenTrabajo(orden);
    void iniciarFlujo();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo al abrir / cambiar orden
  }, [open, orden.id]);

  const notifyRecepcion = () => {
    if (recepcionNotificadaRef.current) return;
    const o = ordenPreparadaRef.current || ordenLista || ordenTrabajo || orden;
    recepcionNotificadaRef.current = true;
    onSuccess(o);
  };

  const handleCloseAll = () => {
    const pendingNotify = Boolean(ordenPreparadaRef.current);
    setFase('idle');
    setOrdenLista(null);
    if (pendingNotify) {
      notifyRecepcion();
    }
    ordenPreparadaRef.current = null;
    onClose();
  };

  const examenIdsSugeridos = alertas
    .map((a) => a.tipo_examen_id)
    .filter((id): id is number => typeof id === 'number' && Number.isFinite(id));

  const showPrepDialog =
    open &&
    (fase === 'check_alertas' ||
      fase === 'preparing' ||
      fase === 'sin_tubos' ||
      fase === 'error');

  return (
    <>
      <Dialog
        open={showPrepDialog}
        onClose={() => fase !== 'preparing' && fase !== 'check_alertas' && onClose()}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Imprimir etiquetas — orden {orden.numero || orden.id}</DialogTitle>
        <DialogContent>
          {fase === 'check_alertas' || fase === 'preparing' ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 3, gap: 1 }}>
              <CircularProgress size={32} />
              <Typography variant="body2" color="text.secondary" textAlign="center">
                {fase === 'check_alertas'
                  ? 'Revisando frecuencia de ensayos…'
                  : 'Preparando tubos (siguen pendientes de recepción)…'}
              </Typography>
            </Box>
          ) : fase === 'sin_tubos' ? (
            <Box sx={{ py: 1 }}>
              <Alert severity="warning" sx={{ mb: 2 }}>
                No se calcularon tubos. Verificá que los exámenes o el panel tengan tipo de
                contenedor (EDTA, Citrato, Heparina, Suero…) en el catálogo.
              </Alert>
              <Button
                component={RouterLink}
                to="/laboratorio/catalogos/examenes"
                variant="outlined"
                size="small"
              >
                Ir a catálogo de exámenes
              </Button>
            </Box>
          ) : fase === 'error' && prepError ? (
            <Alert severity="error">{prepError}</Alert>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={onClose}
            disabled={fase === 'preparing' || fase === 'check_alertas'}
          >
            Cancelar
          </Button>
        </DialogActions>
      </Dialog>

      <AlertasFrecuenciaEtiquetasDialog
        open={open && fase === 'alertas'}
        numeroOrden={ordenTrabajo.numero || String(ordenTrabajo.id)}
        alertas={alertas}
        onCancelar={onClose}
        onContinuar={() => {
          skipAlertasRef.current = true;
          void prepareTubos();
        }}
        onQuitarExamenes={() => {
          void (async () => {
            try {
              const fresh = await getSolicitudExamen(ordenTrabajo.id);
              setOrdenTrabajo(fresh);
            } catch {
              /* keep */
            }
            setFase('quitar');
          })();
        }}
      />

      <QuitarExamenesOrdenDialog
        open={open && fase === 'quitar'}
        orden={ordenTrabajo}
        examenIdsSugeridos={examenIdsSugeridos}
        onClose={() => setFase('alertas')}
        onSuccess={async (updated) => {
          setOrdenTrabajo(updated);
          onPrepared?.(updated);
          // Recargar detalle completo (paneles/resultados) y reabrir flujo de etiquetas.
          try {
            const fresh = await getSolicitudExamen(updated.id);
            setOrdenTrabajo(fresh);
          } catch {
            /* keep updated */
          }
          skipAlertasRef.current = false;
          setFase('check_alertas');
          try {
            const data = await getAlertasFrecuenciaOrden(updated.id);
            if (data.aplica_revision_etiquetas && (data.alertas?.length ?? 0) > 0) {
              setAlertas(data.alertas);
              setFase('alertas');
              return;
            }
            setAlertas([]);
            await prepareTubos();
          } catch {
            await prepareTubos();
          }
        }}
      />

      <EtiquetasMuestrasZplOrdenDialog
        open={open && fase === 'zpl'}
        solicitudId={(ordenLista || ordenTrabajo).id}
        solicitudNumero={(ordenLista || ordenTrabajo).numero}
        origenOrden={origenEfectivo}
        onClose={handleCloseAll}
        onAllPrinted={notifyRecepcion}
      />
    </>
  );
};

export default TomarMuestraOrdenDialog;
