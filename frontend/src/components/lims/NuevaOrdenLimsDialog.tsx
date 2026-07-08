import React, { useEffect, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  ThemeProvider,
} from '@mui/material';
import toast from 'react-hot-toast';
import { apiService } from '../../services/api';
import {
  createSolicitudExamenLims,
  formatDrfError,
  getTiposExamenMap,
  listPanelesLims,
} from '../../services/limsApi';
import type { Paciente } from '../../types';
import type { LimsPanelExamen, LimsTipoExamen, OrigenSolicitudLims } from '../../types/lims';
import { formatPacienteLabel } from '../../utils/pacienteFormat';
import { ORIGEN_SOLICITUD_LIMS_OPTIONS, esOrigenAmbulatorioExterno } from '../../utils/limsOrigenSolicitud';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import {
  clinicalDrawerDialogProps,
  scrollableClinicalDialogActionsSx,
  scrollableClinicalDialogContentSx,
  scrollableClinicalDialogPaperSx,
  useClinicalDrawerDialogTheme,
  Z_DIALOG_OVER_CLINICAL_DRAWER,
} from '../../utils/layerZIndex';
import SolicitudAnalisisPapelForm, {
  useSolicitudAnalisisSelection,
} from './SolicitudAnalisisPapelForm';

export interface NuevaOrdenLimsDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated?: (ordenId: number) => void;
  /** Paciente preseleccionado (p. ej. desde consulta). */
  pacienteInicial?: Paciente | null;
  consultaHcId?: number;
  medicoId?: number | null;
  /** Si true, solo agrega al borrador vía callback en lugar de POST inmediato. */
  draftMode?: boolean;
  onAddDraft?: (payload: {
    examenes_ids: number[];
    paneles_ids: number[];
    examenes_labels: string[];
    paneles_labels: string[];
    observaciones?: string;
  }) => void;
}

const NuevaOrdenLimsDialog: React.FC<NuevaOrdenLimsDialogProps> = ({
  open,
  onClose,
  onCreated,
  pacienteInicial = null,
  consultaHcId,
  medicoId,
  draftMode = false,
  onAddDraft,
}) => {
  const dialogTheme = useClinicalDrawerDialogTheme();
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [examenes, setExamenes] = useState<LimsTipoExamen[]>([]);
  const [paneles, setPaneles] = useState<LimsPanelExamen[]>([]);
  const [observaciones, setObservaciones] = useState('');

  const [paciente, setPaciente] = useState<Paciente | null>(pacienteInicial);
  const [pacienteQuery, setPacienteQuery] = useState('');
  const [pacienteOptions, setPacienteOptions] = useState<Paciente[]>([]);
  const [searchingPaciente, setSearchingPaciente] = useState(false);
  const [origenManual, setOrigenManual] = useState<OrigenSolicitudLims>('EXTERNO_CEHTA');
  const [medicoExterno, setMedicoExterno] = useState('');

  const {
    selectedPanelesIds,
    selectedExamenesIds,
    togglePanel,
    toggleExamen,
    resetSelection,
    getSelectionArrays,
    hasSelection,
  } = useSolicitudAnalisisSelection();

  useEffect(() => {
    if (!open) return;
    setPaciente(pacienteInicial ?? null);
    setObservaciones('');
    setError('');
    setOrigenManual('EXTERNO_CEHTA');
    setMedicoExterno('');
    resetSelection();
  }, [open, pacienteInicial, resetSelection]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setCatalogLoading(true);
    Promise.all([getTiposExamenMap(), listPanelesLims()])
      .then(([examMap, panList]) => {
        if (cancelled) return;
        setExamenes(Array.from(examMap.values()).filter((e) => e.activo !== false));
        setPaneles(panList.filter((p) => p.activo !== false));
      })
      .catch((e) => {
        if (!cancelled) setError(formatDrfError(e));
      })
      .finally(() => {
        if (!cancelled) setCatalogLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open]);

  useEffect(() => {
    if (!open || pacienteInicial || draftMode) return;
    const q = pacienteQuery.trim();
    if (q.length < 2) {
      setPacienteOptions([]);
      return;
    }
    const t = window.setTimeout(async () => {
      setSearchingPaciente(true);
      try {
        const results = await apiService.buscarPacientes(q);
        setPacienteOptions(results);
      } catch {
        setPacienteOptions([]);
      } finally {
        setSearchingPaciente(false);
      }
    }, 250);
    return () => window.clearTimeout(t);
  }, [pacienteQuery, open, pacienteInicial, draftMode]);

  const resolveLabels = () => {
    const { paneles_ids, examenes_ids } = getSelectionArrays();
    const paneles_labels = paneles_ids
      .map((id) => paneles.find((p) => p.id === id)?.nombre)
      .filter(Boolean) as string[];
    const examenes_labels = examenes_ids
      .map((id) => examenes.find((e) => e.id === id)?.nombre)
      .filter(Boolean) as string[];
    return { paneles_ids, examenes_ids, paneles_labels, examenes_labels };
  };

  const handleSubmit = async () => {
    setError('');
    if (!hasSelection) {
      setError('Seleccioná al menos un análisis o panel.');
      return;
    }

    const { paneles_ids, examenes_ids, paneles_labels, examenes_labels } = resolveLabels();

    if (draftMode) {
      onAddDraft?.({
        paneles_ids,
        examenes_ids,
        paneles_labels,
        examenes_labels,
        observaciones: observaciones.trim() || undefined,
      });
      onClose();
      return;
    }

    if (!paciente?.id) {
      setError('Seleccioná un paciente.');
      return;
    }
    if (esOrigenAmbulatorioExterno(origenManual) && !medicoExterno.trim()) {
      setError('Indique el médico solicitante de la receta externa.');
      return;
    }

    setSaving(true);
    try {
      const orden = await createSolicitudExamenLims({
        paciente_id: paciente.id,
        medico_id: medicoId ?? undefined,
        consulta_hc_id: consultaHcId,
        origen_solicitud: consultaHcId ? undefined : origenManual,
        medico_externo_nombre: esOrigenAmbulatorioExterno(origenManual)
          ? medicoExterno.trim()
          : undefined,
        examenes_ids,
        paneles_ids,
        observaciones: observaciones.trim() || undefined,
      });
      toast.success(`Orden ${orden.numero || `#${orden.id}`} creada.`);
      onCreated?.(orden.id);
      onClose();
    } catch (e) {
      const msg = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes);
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const showPacientePicker = !draftMode && !pacienteInicial;

  return (
    <ThemeProvider theme={dialogTheme}>
      <Dialog
        open={open}
        onClose={saving ? undefined : onClose}
        maxWidth="md"
        fullWidth
        disableScrollLock={clinicalDrawerDialogProps.disableScrollLock}
        slotProps={{
          root: clinicalDrawerDialogProps.slotProps?.root,
          paper: {
            sx: {
              ...scrollableClinicalDialogPaperSx,
              zIndex: Z_DIALOG_OVER_CLINICAL_DRAWER,
            },
          },
        }}
      >
        <DialogTitle sx={{ flexShrink: 0 }}>
          {draftMode ? 'Solicitar análisis de laboratorio' : 'Nueva orden de laboratorio'}
        </DialogTitle>
        <DialogContent dividers sx={scrollableClinicalDialogContentSx}>
          <Stack spacing={2} sx={{ mt: 0.5 }}>
            {error && <Alert severity="error">{error}</Alert>}

            {showPacientePicker && (
              <Autocomplete
                options={pacienteOptions}
                value={paciente}
                onChange={(_e, value) => setPaciente(value)}
                inputValue={pacienteQuery}
                onInputChange={(_e, value) => setPacienteQuery(value)}
                getOptionLabel={(p) => formatPacienteLabel(p)}
                isOptionEqualToValue={(a, b) => a.id === b.id}
                loading={searchingPaciente}
                noOptionsText={
                  pacienteQuery.trim().length < 2
                    ? 'Escribí al menos 2 caracteres'
                    : 'Sin coincidencias'
                }
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Paciente *"
                    placeholder="DNI, apellido o nombre"
                  />
                )}
              />
            )}

            {pacienteInicial && (
              <Alert severity="info" sx={{ py: 0.5 }}>
                Paciente: <strong>{formatPacienteLabel(pacienteInicial)}</strong>
              </Alert>
            )}

            {consultaHcId && (
              <Alert severity="info" sx={{ py: 0.5 }}>
                El origen clínico se determina al guardar según internación, guardia o ambulatorio
                (CEHTA / ICPL).
              </Alert>
            )}

            {!consultaHcId && !draftMode && (
              <>
                <FormControl fullWidth size="small">
                  <InputLabel id="origen-lims-label">Origen clínico</InputLabel>
                  <Select
                    labelId="origen-lims-label"
                    label="Origen clínico"
                    value={origenManual}
                    onChange={(e) => setOrigenManual(e.target.value as OrigenSolicitudLims)}
                  >
                    {ORIGEN_SOLICITUD_LIMS_OPTIONS.map((opt) => (
                      <MenuItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                {esOrigenAmbulatorioExterno(origenManual) && (
                  <TextField
                    fullWidth
                    size="small"
                    required
                    label="Médico solicitante (receta externa)"
                    placeholder="Apellido y nombre del médico"
                    value={medicoExterno}
                    onChange={(e) => setMedicoExterno(e.target.value)}
                    helperText="Receta emitida fuera de la clínica; el paciente presenta el pedido en laboratorio."
                  />
                )}
              </>
            )}

            {catalogLoading ? (
              <Box display="flex" justifyContent="center" py={4}>
                <CircularProgress size={32} />
              </Box>
            ) : (
              <SolicitudAnalisisPapelForm
                examenes={examenes}
                paneles={paneles}
                selectedPanelesIds={selectedPanelesIds}
                selectedExamenesIds={selectedExamenesIds}
                onTogglePanel={togglePanel}
                onToggleExamen={toggleExamen}
                observaciones={observaciones}
                onObservacionesChange={setObservaciones}
                disabled={saving}
              />
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={scrollableClinicalDialogActionsSx}>
          <Button onClick={onClose} disabled={saving}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={saving || catalogLoading || (!draftMode && !pacienteInicial && !paciente)}
          >
            {saving ? (
              <CircularProgress size={22} color="inherit" />
            ) : draftMode ? (
              'Agregar a la consulta'
            ) : (
              'Crear orden'
            )}
          </Button>
        </DialogActions>
      </Dialog>
    </ThemeProvider>
  );
};

export default NuevaOrdenLimsDialog;
