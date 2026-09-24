import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { EtiquetaEstudioMicroZpl } from '../../../types/lims';
import { getEstudioMicroEtiquetaZpl, printTalonEstudioMicro } from '../../../services/limsMicroApi';
import {
  imprimirEtiquetaEstudioMicroLocal,
  LabelPrintAgentError,
} from '../../../services/labelPrintAgent';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../../utils/apiError';
import { printerErrorMessage } from '../EtiquetaMuestraZplDialog';

export interface ImprimirPedidoMicroDialogProps {
  open: boolean;
  estudioId: number;
  estudioNumero?: string | null;
  /** true = reimpresión (ya esperando recepción) */
  reimpresion?: boolean;
  onClose: () => void;
  /** Tras imprimir etiqueta (marca etiquetas_impresas); no se llama al bajar solo el talón. */
  onEtiquetasOk?: () => void;
}

/**
 * Vista previa ZPL 40×23 + impresión USB local (mismo agente que lab clínico) + talón A4.
 * El talón no muta estado ni etiquetas_impresas_at.
 */
const ImprimirPedidoMicroDialog: React.FC<ImprimirPedidoMicroDialogProps> = ({
  open,
  estudioId,
  estudioNumero,
  reimpresion,
  onClose,
  onEtiquetasOk,
}) => {
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState<'etiqueta' | 'talon' | null>(null);
  const [payload, setPayload] = useState<EtiquetaEstudioMicroZpl | null>(null);
  const printLock = useRef(false);

  useEffect(() => {
    if (!open) {
      setPayload(null);
      printLock.current = false;
      return;
    }
    let cancelled = false;
    setLoading(true);
    getEstudioMicroEtiquetaZpl(estudioId)
      .then((data) => {
        if (!cancelled) setPayload(data);
      })
      .catch((e) => {
        if (!cancelled) {
          toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
          onClose();
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, estudioId, onClose]);

  const handleEtiqueta = async () => {
    if (printLock.current || busy) return;
    printLock.current = true;
    setBusy('etiqueta');
    try {
      await imprimirEtiquetaEstudioMicroLocal(estudioId);
      toast.success(reimpresion ? 'Etiqueta reimpresa.' : 'Etiqueta enviada a impresión.');
      onEtiquetasOk?.();
      onClose();
    } catch (e) {
      toast.error(printerErrorMessage(e));
    } finally {
      setBusy(null);
      printLock.current = false;
    }
  };

  const handleTalon = async () => {
    if (busy) return;
    setBusy('talon');
    try {
      await printTalonEstudioMicro(estudioId);
      toast.success('Diálogo de impresión abierto — elegí una impresora común.');
    } catch (e) {
      if (e instanceof LabelPrintAgentError) {
        toast.error(e.message);
      } else {
        toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
      }
    } finally {
      setBusy(null);
    }
  };

  const lines = payload?.lines ?? [];
  const errors = payload?.validation_errors ?? [];
  const canPrint = Boolean(payload?.printable);

  return (
    <Dialog open={open} onClose={() => !busy && onClose()} maxWidth="xs" fullWidth>
      <DialogTitle>
        Imprimir — {estudioNumero || `estudio ${estudioId}`}
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          <strong>Etiqueta</strong>: 40 × 23 mm por USB (agente local), igual que lab clínico
          {reimpresion ? '' : ' — pasa a «Esperando recepción» la primera vez'}.{' '}
          <strong>Talón</strong>: media hoja A4 — no cambia el estado del pedido.
        </Typography>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={28} />
          </Box>
        ) : (
          <>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
              Etiqueta 40 × 23 mm · Perfil 203 dpi
              {payload?.profile ? ` · ${payload.profile}` : ''}
            </Typography>
            {lines.length === 4 ? (
              <Box
                sx={{
                  border: '1px solid',
                  borderColor: 'divider',
                  px: 2,
                  py: 1.5,
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                  bgcolor: 'background.paper',
                }}
              >
                <Typography sx={{ fontWeight: 700, fontSize: '1.05rem', lineHeight: 1.3 }}>
                  {lines[0]}
                </Typography>
                <Typography sx={{ fontSize: '0.9rem', lineHeight: 1.35 }}>{lines[1]}</Typography>
                <Typography sx={{ fontSize: '0.9rem', lineHeight: 1.35 }}>{lines[2]}</Typography>
                <Typography sx={{ fontSize: '0.9rem', lineHeight: 1.35 }}>{lines[3]}</Typography>
              </Box>
            ) : (
              <Typography color="text.secondary" variant="body2">
                No se puede generar la etiqueta completa todavía.
              </Typography>
            )}
            {errors.length > 0 && (
              <Box sx={{ mt: 1 }}>
                {errors.map((err) => (
                  <Typography key={err} variant="body2" color="warning.main">
                    {err}
                  </Typography>
                ))}
              </Box>
            )}
          </>
        )}
        {busy ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={28} />
          </Box>
        ) : null}
      </DialogContent>
      <DialogActions sx={{ flexWrap: 'wrap', gap: 1 }}>
        <Button variant="outlined" disabled={!!busy || loading} onClick={() => void handleTalon()}>
          Imprimir talón
        </Button>
        <Button
          variant="contained"
          disabled={!!busy || loading || !canPrint}
          onClick={() => void handleEtiqueta()}
        >
          {reimpresion ? 'Reimprimir etiqueta' : 'Imprimir etiqueta'}
        </Button>
        <Box sx={{ flex: 1 }} />
        <Button onClick={onClose} disabled={!!busy}>
          Cerrar
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ImprimirPedidoMicroDialog;
