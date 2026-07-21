import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import { Print } from '@mui/icons-material';
import { Link as RouterLink } from 'react-router-dom';
import toast from 'react-hot-toast';
import type { MuestraTransaccional, SolicitudExamenLims } from '../../types/lims';
import {
  downloadEtiquetasOrdenMuestras,
  getTubosPreviewOrden,
  postTomarMuestraOrden,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import {
  formatTuboPreviewLabel,
  totalEtiquetasDesdeTubos,
  type TuboOrdenPreview,
} from '../../utils/limsTubosOrden';

export interface TomarMuestraOrdenDialogProps {
  open: boolean;
  orden: SolicitudExamenLims;
  muestrasExistentes?: MuestraTransaccional[];
  onClose: () => void;
  onSuccess: (orden: SolicitudExamenLims) => void;
}

/**
 * Flujo «Imprimir etiquetas»: confirma tubos, genera muestras (PENDIENTE_TOMA)
 * y descarga el PDF de etiquetas en el mismo paso.
 */
const TomarMuestraOrdenDialog: React.FC<TomarMuestraOrdenDialogProps> = ({
  open,
  orden,
  muestrasExistentes = [],
  onClose,
  onSuccess,
}) => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [tubos, setTubos] = useState<TuboOrdenPreview[]>([]);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const yaTieneMuestras =
    muestrasExistentes.length > 0 ||
    (orden.tubos_pendientes_extraccion?.length ?? 0) > 0 ||
    !!orden.fecha_toma_muestra;

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    setPreviewError(null);
    setTubos([]);
    (async () => {
      try {
        const data = await getTubosPreviewOrden(orden.id);
        if (cancelled) return;
        setTubos(data);
      } catch (e) {
        if (!cancelled) {
          setPreviewError(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarCatalogo));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, orden.id]);

  const totalEtiquetas = totalEtiquetasDesdeTubos(tubos);

  const handleConfirm = async () => {
    setSaving(true);
    try {
      const updated = await postTomarMuestraOrden(orden.id, {});
      try {
        await downloadEtiquetasOrdenMuestras(updated.id, updated.numero);
        toast.success('Etiquetas generadas. Imprimí el PDF y pegá en cada tubo.');
      } catch {
        toast.success('Tubos registrados. Podés reimprimir etiquetas desde la orden.');
      }
      onSuccess(updated);
      onClose();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarOrden));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={() => !saving && onClose()} maxWidth="sm" fullWidth>
      <DialogTitle>Imprimir etiquetas — orden {orden.numero || orden.id}</DialogTitle>
      <DialogContent>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={32} />
          </Box>
        ) : previewError ? (
          <Alert severity="error" sx={{ mb: 1 }}>
            {previewError}
          </Alert>
        ) : tubos.length === 0 ? (
          <Box sx={{ py: 2 }}>
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
        ) : (
          <>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              Se generarán estos tubos con código de barras (máx. 10 exámenes por tubo; el
              hemograma cuenta como uno). La recepción se confirma después escaneando cada tubo.
            </Typography>
            <Chip
              size="small"
              color="primary"
              label={`${totalEtiquetas} etiqueta${totalEtiquetas === 1 ? '' : 's'}`}
              sx={{ mb: 1 }}
            />
            <List dense>
              {tubos.map((t) => (
                <ListItem key={t.tipo_contenedor_id} alignItems="flex-start" sx={{ px: 0 }}>
                  <ListItemText
                    primary={formatTuboPreviewLabel(t)}
                    secondary={
                      t.examenes?.length
                        ? t.examenes.slice(0, 12).join(', ') +
                          (t.examenes.length > 12 ? `… (+${t.examenes.length - 12})` : '')
                        : undefined
                    }
                  />
                </ListItem>
              ))}
            </List>
            {yaTieneMuestras && (
              <Alert severity="info" sx={{ mt: 1 }}>
                Si ya hay tubos de esta orden, solo se crean los faltantes y se reimprimen las etiquetas.
                La recepción se confirma después en Recepción.
              </Alert>
            )}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          Cancelar
        </Button>
        <Button
          variant="contained"
          startIcon={saving ? <CircularProgress size={18} color="inherit" /> : <Print />}
          onClick={handleConfirm}
          disabled={saving || loading || !!previewError || tubos.length === 0}
        >
          {saving
            ? 'Generando…'
            : yaTieneMuestras
              ? 'Reimprimir etiquetas'
              : totalEtiquetas > 1
                ? `Crear tubos e imprimir ${totalEtiquetas} etiquetas`
                : 'Crear tubo e imprimir etiqueta'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TomarMuestraOrdenDialog;
