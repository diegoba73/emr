import React, { useState } from 'react';
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
import {
  downloadEtiquetasEstudioMicro,
  printTalonEstudioMicro,
} from '../../../services/limsMicroApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../../utils/apiError';

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
 * Dual: etiqueta PDF de cultivo (impresora tubos / hoja de etiquetas) + talón A4 de respaldo.
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
  const [busy, setBusy] = useState<'etiqueta' | 'talon' | null>(null);

  const handleEtiqueta = async () => {
    if (busy) return;
    setBusy('etiqueta');
    try {
      await downloadEtiquetasEstudioMicro(estudioId);
      toast.success(reimpresion ? 'Etiqueta reimpresa.' : 'Etiqueta generada.');
      onEtiquetasOk?.();
      onClose();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
    } finally {
      setBusy(null);
    }
  };

  const handleTalon = async () => {
    if (busy) return;
    setBusy('talon');
    try {
      await printTalonEstudioMicro(estudioId);
      toast.success('Diálogo de impresión abierto — elegí una impresora común.');
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
    } finally {
      setBusy(null);
    }
  };

  return (
    <Dialog open={open} onClose={() => !busy && onClose()} maxWidth="xs" fullWidth>
      <DialogTitle>
        Imprimir — {estudioNumero || `estudio ${estudioId}`}
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          <strong>Etiqueta</strong>: PDF del cultivo (pasa a «Esperando recepción» si es la primera
          vez). <strong>Talón</strong>: abre impresión en media hoja A4 (paciente, DNI, lugar,
          médico y estudios) — no cambia el estado del pedido.
        </Typography>
        {busy ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
            <CircularProgress size={28} />
          </Box>
        ) : null}
      </DialogContent>
      <DialogActions sx={{ flexWrap: 'wrap', gap: 1 }}>
        <Button variant="outlined" disabled={!!busy} onClick={() => void handleTalon()}>
          Imprimir talón
        </Button>
        <Button variant="contained" disabled={!!busy} onClick={() => void handleEtiqueta()}>
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
