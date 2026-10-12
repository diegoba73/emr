import React, { useEffect, useRef, useState } from 'react';
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
import { getTubosPreviewOrden, postTomarMuestraOrden } from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import type { OrigenParaLugarExtraccion } from '../../utils/limsOrigenSolicitud';
import EtiquetasMuestrasZplOrdenDialog from './EtiquetasMuestrasZplOrdenDialog';

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

/**
 * «Imprimir etiquetas»: crea tubos (PENDIENTE_TOMA) y abre ZPL.
 * No registra toma ni pasa la orden a EN_PROCESO.
 * La UI de Pendientes solo pasa a «Esperando recepción» tras imprimir la última etiqueta.
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
  const [preparing, setPreparing] = useState(false);
  const [prepError, setPrepError] = useState<string | null>(null);
  const [sinTubosCatalogo, setSinTubosCatalogo] = useState(false);
  const [zplOpen, setZplOpen] = useState(false);
  const [ordenLista, setOrdenLista] = useState<SolicitudExamenLims | null>(null);
  const ordenPreparadaRef = useRef<SolicitudExamenLims | null>(null);
  const recepcionNotificadaRef = useRef(false);

  const origenEfectivo: OrigenParaLugarExtraccion = origenOrden || {
    origen_solicitud: orden.origen_solicitud,
    origen_solicitud_display: orden.origen_solicitud_display,
    procedencia_display: orden.procedencia_display,
  };

  const yaTieneMuestras =
    muestrasExistentes.length > 0 ||
    (orden.tubos_pendientes_extraccion?.length ?? 0) > 0 ||
    !!orden.fecha_toma_muestra;

  useEffect(() => {
    if (!open) {
      setZplOpen(false);
      setOrdenLista(null);
      ordenPreparadaRef.current = null;
      recepcionNotificadaRef.current = false;
      setPrepError(null);
      setSinTubosCatalogo(false);
      setPreparing(false);
      return;
    }

    let cancelled = false;
    setPreparing(true);
    setPrepError(null);
    setSinTubosCatalogo(false);
    setZplOpen(false);

    (async () => {
      try {
        if (!yaTieneMuestras) {
          const tubos = await getTubosPreviewOrden(orden.id);
          if (cancelled) return;
          if (!tubos.length) {
            setSinTubosCatalogo(true);
            setPreparing(false);
            return;
          }
        }

        const updated = await postTomarMuestraOrden(orden.id, {});
        if (cancelled) return;
        ordenPreparadaRef.current = updated;
        setOrdenLista(updated);
        setZplOpen(true);
        onPrepared?.(updated);
      } catch (e) {
        if (!cancelled) {
          const msg = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarOrden);
          setPrepError(msg);
          toast.error(msg);
        }
      } finally {
        if (!cancelled) setPreparing(false);
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- solo al abrir / cambiar orden
  }, [open, orden.id]);

  const notifyRecepcion = () => {
    if (recepcionNotificadaRef.current) return;
    const o = ordenPreparadaRef.current || ordenLista || orden;
    recepcionNotificadaRef.current = true;
    onSuccess(o);
  };

  const handleCloseAll = () => {
    // Tubos ya creados ⇒ en backend es «esperando recepción». Si cierra sin imprimir
    // todas (p. ej. sin agente USB), igual refresca la pestaña.
    const pendingNotify = Boolean(ordenPreparadaRef.current);
    setZplOpen(false);
    setOrdenLista(null);
    if (pendingNotify) {
      notifyRecepcion();
    }
    ordenPreparadaRef.current = null;
    onClose();
  };

  const showPrepDialog = open && !zplOpen;

  return (
    <>
      <Dialog open={showPrepDialog} onClose={() => !preparing && onClose()} maxWidth="xs" fullWidth>
        <DialogTitle>Imprimir etiquetas — orden {orden.numero || orden.id}</DialogTitle>
        <DialogContent>
          {preparing ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 3, gap: 1 }}>
              <CircularProgress size={32} />
              <Typography variant="body2" color="text.secondary" textAlign="center">
                Preparando tubos (siguen pendientes de recepción)…
              </Typography>
            </Box>
          ) : sinTubosCatalogo ? (
            <Box sx={{ py: 1 }}>
              <Alert severity="warning" sx={{ mb: 2 }}>
                No se calcularon tubos. Verificá que los exámenes o el panel tengan tipo de tubo
                (EDTA, Citrato, Heparina, Suero…) en el catálogo.
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
          ) : prepError ? (
            <Alert severity="error">{prepError}</Alert>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={preparing}>
            Cancelar
          </Button>
        </DialogActions>
      </Dialog>

      <EtiquetasMuestrasZplOrdenDialog
        open={zplOpen}
        solicitudId={(ordenLista || orden).id}
        solicitudNumero={(ordenLista || orden).numero}
        origenOrden={origenEfectivo}
        onClose={handleCloseAll}
        onAllPrinted={notifyRecepcion}
      />
    </>
  );
};

export default TomarMuestraOrdenDialog;
