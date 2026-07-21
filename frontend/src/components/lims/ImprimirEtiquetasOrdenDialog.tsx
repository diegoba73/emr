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
import { Print } from '@mui/icons-material';
import toast from 'react-hot-toast';
import { downloadEtiquetasOrdenMuestras } from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';

export interface ImprimirEtiquetasOrdenDialogProps {
  open: boolean;
  solicitudId: number;
  solicitudNumero?: string | null;
  onClose: () => void;
}

const ImprimirEtiquetasOrdenDialog: React.FC<ImprimirEtiquetasOrdenDialogProps> = ({
  open,
  solicitudId,
  solicitudNumero,
  onClose,
}) => {
  const [downloading, setDownloading] = useState(false);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await downloadEtiquetasOrdenMuestras(solicitudId, solicitudNumero);
      toast.success('Etiquetas descargadas. Imprimí el PDF y pegá en cada tubo.');
      onClose();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarOrden));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <Dialog open={open} onClose={() => !downloading && onClose()} maxWidth="xs" fullWidth>
      <DialogTitle>Imprimir etiquetas de muestras</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary">
          Las muestras fueron registradas con código de barras. Descargá el PDF con las etiquetas,
          imprimilas y pegalas en cada tubo antes de enviar al laboratorio.
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={downloading}>
          Después
        </Button>
        <Button
          variant="contained"
          startIcon={downloading ? <CircularProgress size={18} color="inherit" /> : <Print />}
          onClick={handleDownload}
          disabled={downloading}
        >
          {downloading ? 'Generando…' : 'Descargar etiquetas PDF'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ImprimirEtiquetasOrdenDialog;
