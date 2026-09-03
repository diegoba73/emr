import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  FormGroup,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { LimsPanelResumen, ResultadoExamenLims, SolicitudExamenLims } from '../../types/lims';
import { quitarExamenesSolicitudLims } from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';

export interface QuitarExamenesOrdenDialogProps {
  open: boolean;
  orden: SolicitudExamenLims;
  onClose: () => void;
  onSuccess: (orden: SolicitudExamenLims) => void;
}

function resultadoNoVacio(r: ResultadoExamenLims): boolean {
  if ((r.valor_obtenido || '').trim()) return true;
  if (r.valor_numerico !== null && r.valor_numerico !== undefined && r.valor_numerico !== '') {
    return true;
  }
  return Boolean(r.validado_por || r.fecha_validacion);
}

function exclusiveExamIds(panel: LimsPanelResumen, all: LimsPanelResumen[]): number[] {
  const other = new Set(
    all.filter((p) => p.id !== panel.id).flatMap((p) => p.tipos_examen_ids)
  );
  return panel.tipos_examen_ids.filter((id) => !other.has(id));
}

const QuitarExamenesOrdenDialog: React.FC<QuitarExamenesOrdenDialogProps> = ({
  open,
  orden,
  onClose,
  onSuccess,
}) => {
  const [panelIds, setPanelIds] = useState<number[]>([]);
  const [examenIds, setExamenIds] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);

  const paneles = orden.paneles_resumen ?? [];
  const resultados = orden.resultados ?? [];
  const panelExamIds = useMemo(
    () => new Set(paneles.flatMap((p) => p.tipos_examen_ids)),
    [paneles]
  );

  const sueltos = useMemo((): ResultadoExamenLims[] => {
    const fromResultados = resultados.filter((r) => !panelExamIds.has(r.tipo_examen));
    if (fromResultados.length > 0 || resultados.length > 0) return fromResultados;
    const ids = orden.tipos_examen ?? [];
    const nombres = orden.tipos_examen_nombres ?? [];
    return ids
      .filter((id) => !panelExamIds.has(id))
      .map((id, idx) => ({
        id,
        solicitud: orden.id,
        tipo_examen: id,
        tipo_examen_nombre: nombres[ids.indexOf(id)] || nombres[idx] || `Examen #${id}`,
        valor_obtenido: '',
      }));
  }, [resultados, panelExamIds, orden.tipos_examen, orden.tipos_examen_nombres, orden.id]);

  useEffect(() => {
    if (open) {
      setPanelIds([]);
      setExamenIds([]);
    }
  }, [open, orden.id]);

  const panelBloqueado = (panel: LimsPanelResumen): boolean => {
    const exclusive = exclusiveExamIds(panel, paneles);
    return resultados.some((r) => exclusive.includes(r.tipo_examen) && resultadoNoVacio(r));
  };

  const togglePanel = (id: number, checked: boolean) => {
    setPanelIds((prev) => (checked ? [...prev, id] : prev.filter((x) => x !== id)));
  };
  const toggleExamen = (id: number, checked: boolean) => {
    setExamenIds((prev) => (checked ? [...prev, id] : prev.filter((x) => x !== id)));
  };

  const canSubmit = panelIds.length > 0 || examenIds.length > 0;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setSaving(true);
    try {
      const updated = await quitarExamenesSolicitudLims(orden.id, {
        examenes_ids: examenIds,
        paneles_ids: panelIds,
      });
      toast.success('Exámenes/paneles quitados de la orden.');
      onSuccess(updated);
      onClose();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsQuitarExamenes));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={() => !saving && onClose()} fullWidth maxWidth="sm">
      <DialogTitle>Quitar exámenes de {orden.numero || `orden #${orden.id}`}</DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Solo se quitan ítems sin resultado cargado ni validados. Quitar un panel elimina sus
          exámenes que no estén en otro panel de la orden.
        </Typography>
        {paneles.length === 0 && sueltos.length === 0 && (
          <Alert severity="info">No hay estudios para quitar en esta orden.</Alert>
        )}
        {paneles.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Paneles
            </Typography>
            <FormGroup>
              {paneles.map((p) => {
                const blocked = panelBloqueado(p);
                return (
                  <FormControlLabel
                    key={p.id}
                    control={
                      <Checkbox
                        checked={panelIds.includes(p.id)}
                        disabled={blocked || saving}
                        onChange={(e) => togglePanel(p.id, e.target.checked)}
                      />
                    }
                    label={
                      blocked
                        ? `${p.nombre} (tiene resultados cargados)`
                        : p.nombre
                    }
                  />
                );
              })}
            </FormGroup>
          </Box>
        )}
        {sueltos.length > 0 && (
          <Box>
            <Typography variant="subtitle2" gutterBottom>
              Exámenes
            </Typography>
            <FormGroup>
              {sueltos.map((r) => {
                const blocked = resultadoNoVacio(r);
                const label = r.tipo_examen_nombre || r.tipo_examen_codigo || `Examen #${r.tipo_examen}`;
                return (
                  <FormControlLabel
                    key={r.tipo_examen}
                    control={
                      <Checkbox
                        checked={examenIds.includes(r.tipo_examen)}
                        disabled={blocked || saving}
                        onChange={(e) => toggleExamen(r.tipo_examen, e.target.checked)}
                      />
                    }
                    label={blocked ? `${label} (con resultado)` : label}
                  />
                );
              })}
            </FormGroup>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          Cancelar
        </Button>
        <Button
          variant="contained"
          color="error"
          onClick={() => void handleSubmit()}
          disabled={!canSubmit || saving}
        >
          {saving ? <CircularProgress size={22} color="inherit" /> : 'Quitar seleccionados'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default QuitarExamenesOrdenDialog;
