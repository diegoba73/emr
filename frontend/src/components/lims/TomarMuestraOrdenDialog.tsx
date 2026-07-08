import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  FormGroup,
  Typography,
} from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';
import toast from 'react-hot-toast';
import type { MuestraTransaccional, SolicitudExamenLims } from '../../types/lims';
import {
  getTiposExamenMap,
  listTiposMuestraLims,
  postTomarMuestraOrden,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import {
  buildOpcionesTiposMuestraTomar,
  idsTiposMuestraRequeridosPendientes,
  type TipoMuestraTomarOpcion,
} from '../../utils/limsTiposMuestraOrden';

export interface TomarMuestraOrdenDialogProps {
  open: boolean;
  orden: SolicitudExamenLims;
  muestrasExistentes: MuestraTransaccional[];
  onClose: () => void;
  onSuccess: (orden: SolicitudExamenLims) => void;
}

const TomarMuestraOrdenDialog: React.FC<TomarMuestraOrdenDialogProps> = ({
  open,
  orden,
  muestrasExistentes,
  onClose,
  onSuccess,
}) => {
  const [loadingCatalog, setLoadingCatalog] = useState(false);
  const [saving, setSaving] = useState(false);
  const [opciones, setOpciones] = useState<TipoMuestraTomarOpcion[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoadingCatalog(true);
    setSelected(new Set());
    (async () => {
      try {
        const [examMap, tiposMuestra] = await Promise.all([
          getTiposExamenMap(),
          listTiposMuestraLims({ activo: true }),
        ]);
        if (cancelled) return;
        const opts = buildOpcionesTiposMuestraTomar(orden, examMap, tiposMuestra, muestrasExistentes);
        setOpciones(opts);
        const preselect = idsTiposMuestraRequeridosPendientes(orden, examMap, tiposMuestra, muestrasExistentes);
        const validPreselect = preselect.filter((id) => opts.some((o) => o.tipoMuestraId === id));
        setSelected(new Set(validPreselect.length > 0 ? validPreselect : opts.length === 1 ? [opts[0].tipoMuestraId] : []));
      } catch (e) {
        if (!cancelled) {
          toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarCatalogo));
          onClose();
        }
      } finally {
        if (!cancelled) setLoadingCatalog(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, orden, muestrasExistentes, onClose]);

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const seleccionarRequeridas = () => {
    setSelected(new Set(opciones.filter((o) => o.requeridoPorOrden).map((o) => o.tipoMuestraId)));
  };

  const seleccionarTodas = () => {
    setSelected(new Set(opciones.map((o) => o.tipoMuestraId)));
  };

  const requeridas = opciones.filter((o) => o.requeridoPorOrden);
  const hayVarias = opciones.length > 1;
  const selectedCount = selected.size;

  const handleConfirm = async () => {
    if (selectedCount === 0) {
      toast.error('Seleccioná al menos un tipo de muestra');
      return;
    }
    setSaving(true);
    try {
      const updated = await postTomarMuestraOrden(orden.id, {
        muestras: Array.from(selected).map((tipo_muestra_id) => ({ tipo_muestra_id })),
      });
      toast.success(
        selectedCount === 1 ? 'Muestra registrada y tomada' : `${selectedCount} muestras registradas y tomadas`
      );
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
      <DialogTitle>Tomar muestra — orden {orden.numero || orden.id}</DialogTitle>
      <DialogContent>
        {loadingCatalog ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress size={32} />
          </Box>
        ) : opciones.length === 0 ? (
          <Box sx={{ py: 2 }}>
            <Alert severity="warning" sx={{ mb: 2 }}>
              No hay tipos de muestra disponibles. Cargá el catálogo (sangre, orina, etc.) antes de tomar muestras.
            </Alert>
            <Button component={RouterLink} to="/laboratorio/catalogos/tipos-muestra" variant="outlined" size="small">
              Ir a tipos de muestra
            </Button>
          </Box>
        ) : (
          <>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Elegí del catálogo qué muestra(s) tomaste. Se registrarán y quedarán disponibles para cargar
              resultados.
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
              {requeridas.length > 0 && (
                <Button size="small" onClick={seleccionarRequeridas}>
                  Requeridas por la orden ({requeridas.length})
                </Button>
              )}
              {hayVarias && (
                <Button size="small" onClick={seleccionarTodas}>
                  Todas ({opciones.length})
                </Button>
              )}
            </Box>
            <FormGroup>
              {opciones.map((t) => (
                <FormControlLabel
                  key={t.tipoMuestraId}
                  control={
                    <Checkbox
                      checked={selected.has(t.tipoMuestraId)}
                      onChange={() => toggle(t.tipoMuestraId)}
                      disabled={saving}
                    />
                  }
                  label={
                    <Box>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                        <Typography variant="body2">
                          {t.codigo} — {t.nombre}
                        </Typography>
                        {t.requeridoPorOrden && (
                          <Chip size="small" label="Requerido" color="primary" variant="outlined" />
                        )}
                      </Box>
                      {t.colorTubo && (
                        <Typography variant="caption" color="text.secondary" display="block">
                          Tubo: {t.colorTubo}
                        </Typography>
                      )}
                      {t.examenesAsociados.length > 0 && (
                        <Typography variant="caption" color="text.secondary" display="block">
                          Exámenes: {t.examenesAsociados.join(', ')}
                        </Typography>
                      )}
                    </Box>
                  }
                />
              ))}
            </FormGroup>
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          Cancelar
        </Button>
        <Button
          variant="contained"
          onClick={handleConfirm}
          disabled={saving || loadingCatalog || opciones.length === 0 || selectedCount === 0}
        >
          {saving ? 'Registrando…' : selectedCount > 1 ? `Tomar ${selectedCount} muestras` : 'Tomar muestra'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TomarMuestraOrdenDialog;
