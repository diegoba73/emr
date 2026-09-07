import React, { useEffect, useRef, useState } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
  CircularProgress,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { EtiquetaMuestraZpl } from '../../types/lims';
import { getMuestraEtiquetaZpl, postMuestraImprimirEtiqueta } from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';

export interface EtiquetaMuestraZplDialogProps {
  open: boolean;
  muestraId: number;
  onClose: () => void;
  /** Si true, al abrir intenta imprimir tras cargar preview (flujo botones separados usa false). */
  autoPrint?: boolean;
}

const PRINT_UNCERTAIN_MSG =
  'No se pudo confirmar la impresión. Verifique la impresora antes de reimprimir.';

/** Errores de impresión: nunca sugerir reintento automático / "Intentá nuevamente". */
export function printerErrorMessage(error: unknown): string {
  const status = (error as { response?: { status?: number } })?.response?.status;
  const data = (error as { response?: { data?: { error?: string } } })?.response?.data;
  const msg = typeof data?.error === 'string' ? data.error : '';
  if (status === 400 && msg) {
    return msg;
  }
  if (status === 503 && msg.toLowerCase().includes('no configurada')) {
    return 'Impresora de etiquetas no configurada';
  }
  return PRINT_UNCERTAIN_MSG;
}

const EtiquetaMuestraZplDialog: React.FC<EtiquetaMuestraZplDialogProps> = ({
  open,
  muestraId,
  onClose,
}) => {
  const [loading, setLoading] = useState(false);
  const [printing, setPrinting] = useState(false);
  const [payload, setPayload] = useState<EtiquetaMuestraZpl | null>(null);
  const printLock = useRef(false);

  useEffect(() => {
    if (!open) {
      setPayload(null);
      printLock.current = false;
      return;
    }
    let cancelled = false;
    setLoading(true);
    getMuestraEtiquetaZpl(muestraId)
      .then((data) => {
        if (!cancelled) setPayload(data);
      })
      .catch((e) => {
        if (!cancelled) {
          toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarMuestra));
          onClose();
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, muestraId, onClose]);

  const handlePrint = async () => {
    if (printLock.current || printing) return;
    printLock.current = true;
    setPrinting(true);
    try {
      await postMuestraImprimirEtiqueta(muestraId);
      toast.success('Etiqueta enviada a impresión');
      onClose();
    } catch (e) {
      toast.error(printerErrorMessage(e));
    } finally {
      setPrinting(false);
      printLock.current = false;
    }
  };

  const lines = payload?.lines ?? [];
  const errors = payload?.validation_errors ?? [];
  const canPrint = Boolean(payload?.printable);

  return (
    <Dialog open={open} onClose={() => !printing && onClose()} maxWidth="xs" fullWidth>
      <DialogTitle>Vista previa etiqueta</DialogTitle>
      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
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
              <Box sx={{ mt: 1.5 }}>
                {errors.map((err) => (
                  <Typography key={err} variant="body2" color="warning.main">
                    {err}
                  </Typography>
                ))}
              </Box>
            )}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={printing}>
          Cerrar
        </Button>
        <Button
          variant="contained"
          onClick={handlePrint}
          disabled={loading || printing || !canPrint}
        >
          {printing ? 'Imprimiendo…' : 'Imprimir etiqueta'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default EtiquetaMuestraZplDialog;
