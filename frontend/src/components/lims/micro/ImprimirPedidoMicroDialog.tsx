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
import {
  getEstudioMicroEtiquetaZpl,
  postEstudioMicroImprimirEtiqueta,
  printTalonEstudioMicro,
} from '../../../services/limsMicroApi';
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
  /** true = reimpresión (ya esperando recepción / ya etiquetado) */
  reimpresion?: boolean;
  onClose: () => void;
  /**
   * Tras marcar etiquetas_impresas (pasa a Esperando recepción).
   * Se llama al confirmar «Imprimir etiqueta», aunque falle el agente USB.
   */
  onEtiquetasOk?: () => void | Promise<void>;
}

/**
 * Vista previa ZPL (sin mutar) + Imprimir etiqueta / talón.
 * Al imprimir: marca etiquetas → callback (Pendientes → Esperando recepción) → envía ZPL al USB.
 */
const ImprimirPedidoMicroDialog: React.FC<ImprimirPedidoMicroDialogProps> = ({
  open,
  estudioId,
  estudioNumero,
  reimpresion = false,
  onClose,
  onEtiquetasOk,
}) => {
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [busy, setBusy] = useState<'etiqueta' | 'talon' | null>(null);
  const [payload, setPayload] = useState<EtiquetaEstudioMicroZpl | null>(null);
  const printLock = useRef(false);
  const onEtiquetasOkRef = useRef(onEtiquetasOk);
  onEtiquetasOkRef.current = onEtiquetasOk;

  useEffect(() => {
    if (!open) {
      setPayload(null);
      setLoadError(null);
      setLoading(false);
      setBusy(null);
      printLock.current = false;
      return;
    }

    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    setPayload(null);

    getEstudioMicroEtiquetaZpl(estudioId)
      .then((data) => {
        if (!cancelled) setPayload(data);
      })
      .catch((e) => {
        if (!cancelled) {
          const msg = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes);
          setLoadError(msg);
          toast.error(msg);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, estudioId]);

  const handleEtiqueta = async () => {
    if (printLock.current || busy || loading) return;
    printLock.current = true;
    setBusy('etiqueta');
    try {
      if (!reimpresion) {
        // Marca etiquetas_impresas_at (sin depender del agente USB).
        await postEstudioMicroImprimirEtiqueta(estudioId);
      }

      let printOk = false;
      try {
        await imprimirEtiquetaEstudioMicroLocal(estudioId);
        printOk = true;
        toast.success(
          reimpresion ? 'Etiqueta reimpresa.' : 'Etiqueta enviada a impresión.'
        );
      } catch (printErr) {
        toast.error(
          `${printerErrorMessage(printErr)}${
            reimpresion ? '' : ' El pedido igual pasó a Esperando recepción.'
          }`
        );
      }

      // Mover de pestaña / refrescar recién al terminar (evita desmontar el diálogo a mitad).
      if (!reimpresion || printOk) {
        await onEtiquetasOkRef.current?.();
      }
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
    } finally {
      setBusy(null);
      printLock.current = false;
    }
  };

  const handleTalon = async () => {
    if (busy || loading) return;
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
  const anyBusy = Boolean(busy) || loading;

  return (
    <Dialog
      open={open}
      onClose={() => !anyBusy && onClose()}
      maxWidth="sm"
      fullWidth
      scroll="paper"
    >
      <DialogTitle>
        Imprimir etiquetas
        {estudioNumero ? ` — orden ${estudioNumero}` : ''}
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Etiqueta = impresora USB (agente ZPL). Talón = hoja A4 (impresora común) si falla la
          etiquetadora — podés imprimirlo antes de cerrar. Al imprimir la etiqueta el pedido pasa
          a «Esperando recepción»; no recepciona la muestra.
        </Typography>
        {loading ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 4, gap: 1 }}>
            <CircularProgress size={32} />
            <Typography variant="body2" color="text.secondary" textAlign="center">
              Cargando etiqueta…
            </Typography>
          </Box>
        ) : loadError ? (
          <Typography color="error" variant="body2">
            {loadError}
          </Typography>
        ) : (
          <>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
              Etiqueta 40 × 23 mm · Perfil 203 dpi
              {payload?.profile ? ` · ${payload.profile}` : ''}
            </Typography>
            {estudioNumero ? (
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                {estudioNumero}
              </Typography>
            ) : null}
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
            <Box sx={{ mt: 1.5, display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                variant="contained"
                size="small"
                disabled={anyBusy || !!loadError || !canPrint}
                onClick={() => void handleEtiqueta()}
              >
                {busy === 'etiqueta'
                  ? 'Imprimiendo…'
                  : reimpresion
                    ? 'Reimprimir etiqueta'
                    : 'Imprimir etiqueta'}
              </Button>
            </Box>
          </>
        )}
      </DialogContent>
      <DialogActions sx={{ flexWrap: 'wrap', gap: 1 }}>
        <Button
          variant="outlined"
          disabled={anyBusy || !!loadError}
          onClick={() => void handleTalon()}
        >
          {busy === 'talon' ? 'Abriendo impresión…' : 'Imprimir talón'}
        </Button>
        <Box sx={{ flex: 1 }} />
        <Button onClick={onClose} disabled={anyBusy}>
          Cerrar
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ImprimirPedidoMicroDialog;
