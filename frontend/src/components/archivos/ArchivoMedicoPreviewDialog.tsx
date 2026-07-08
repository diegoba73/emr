import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Typography,
} from '@mui/material';
import { Close, Download } from '@mui/icons-material';
import { ArchivoMedico } from '../../types';
import { downloadArchivoMedico } from '../../services/apiService';
import { getSafeApiErrorMessage } from '../../utils/apiError';
import {
  getArchivoFileName,
  getArchivoPreviewKind,
  guessArchivoMimeType,
  normalizePreviewBlob,
} from '../../utils/archivoMedicoPreview';
import { clinicalDrawerDialogProps } from '../../utils/layerZIndex';

interface ArchivoMedicoPreviewDialogProps {
  open: boolean;
  archivo: ArchivoMedico | null;
  onClose: () => void;
}

const ArchivoMedicoPreviewDialog: React.FC<ArchivoMedicoPreviewDialogProps> = ({
  open,
  archivo,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [previewKind, setPreviewKind] = useState<'pdf' | 'image' | 'unsupported'>('unsupported');
  const [fileName, setFileName] = useState('archivo');

  useEffect(() => {
    if (!open || !archivo) {
      return;
    }

    let cancelled = false;

    const loadPreview = async () => {
      setLoading(true);
      setError('');
      setBlobUrl((prev) => {
        if (prev) {
          window.URL.revokeObjectURL(prev);
        }
        return null;
      });

      const name = getArchivoFileName(archivo);
      const kind = getArchivoPreviewKind(name, archivo.tipo_archivo);
      setFileName(name);
      setPreviewKind(kind);

      try {
        const rawBlob = await downloadArchivoMedico(archivo.id);
        if (cancelled) return;

        const mimeType = guessArchivoMimeType(name, archivo.tipo_archivo);
        const blob = normalizePreviewBlob(rawBlob, mimeType);
        const objectUrl = window.URL.createObjectURL(blob);
        setBlobUrl(objectUrl);
      } catch (err) {
        if (!cancelled) {
          setError(getSafeApiErrorMessage(err, 'No se pudo abrir el archivo.'));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadPreview();

    return () => {
      cancelled = true;
    };
  }, [open, archivo?.id, archivo?.titulo, archivo?.tipo_archivo, archivo?.archivo_nombre]);

  useEffect(() => {
    return () => {
      if (blobUrl) {
        window.URL.revokeObjectURL(blobUrl);
      }
    };
  }, [blobUrl]);

  const handleClose = () => {
    if (blobUrl) {
      window.URL.revokeObjectURL(blobUrl);
    }
    setBlobUrl(null);
    setError('');
    onClose();
  };

  const handleDownload = () => {
    if (!blobUrl) return;
    const link = document.createElement('a');
    link.href = blobUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const handleOpenNewTab = () => {
    if (!blobUrl) return;
    window.open(blobUrl, '_blank', 'noopener,noreferrer');
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="lg" fullWidth {...clinicalDrawerDialogProps}>
      <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pr: 1 }}>
        <Typography variant="h6" component="span" noWrap sx={{ maxWidth: '90%' }}>
          {archivo?.titulo || 'Vista previa'}
        </Typography>
        <IconButton onClick={handleClose} aria-label="Cerrar vista previa">
          <Close />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers sx={{ minHeight: 320, p: 0 }}>
        {loading && (
          <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight={320} gap={2}>
            <CircularProgress />
            <Typography variant="body2" color="text.secondary">
              Cargando archivo...
            </Typography>
          </Box>
        )}
        {!loading && error && (
          <Box p={3}>
            <Alert severity="error">{error}</Alert>
          </Box>
        )}
        {!loading && !error && blobUrl && previewKind === 'pdf' && (
          <Box component="iframe" src={blobUrl} title={fileName} sx={{ width: '100%', height: '70vh', border: 0 }} />
        )}
        {!loading && !error && blobUrl && previewKind === 'image' && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: 320,
              maxHeight: '70vh',
              overflow: 'auto',
              p: 2,
              bgcolor: 'action.hover',
            }}
          >
            <Box
              component="img"
              src={blobUrl}
              alt={fileName}
              sx={{ maxWidth: '100%', maxHeight: '68vh', objectFit: 'contain' }}
            />
          </Box>
        )}
        {!loading && !error && blobUrl && previewKind === 'unsupported' && (
          <Box p={3} textAlign="center">
            <Typography variant="body1" gutterBottom>
              Este tipo de archivo no tiene vista previa integrada.
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Podés descargarlo o abrirlo en una pestaña nueva.
            </Typography>
            <Button variant="outlined" onClick={handleOpenNewTab} sx={{ mr: 1 }}>
              Abrir en pestaña nueva
            </Button>
            <Button variant="contained" startIcon={<Download />} onClick={handleDownload}>
              Descargar
            </Button>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cerrar</Button>
        {blobUrl && (
          <Button variant="contained" startIcon={<Download />} onClick={handleDownload}>
            Descargar
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default ArchivoMedicoPreviewDialog;
