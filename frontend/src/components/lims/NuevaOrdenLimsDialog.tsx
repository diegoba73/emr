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
  DialogContentText,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  TextField,
  ThemeProvider,
} from '@mui/material';
import toast from 'react-hot-toast';
import { apiService } from '../../services/api';
import { useData } from '../../contexts/DataContext';
import type { Medico } from '../../types';
import { getCurrentMedicoId, shouldLockMedicoField } from '../../utils/turnoPermissions';
import {
  agregarExamenesSolicitudLims,
  createSolicitudExamenLims,
  getOrdenAbiertaPaciente,
  getTiposExamenMap,
  listPanelesLims,
} from '../../services/limsApi';
import {
  createEstudiosMicrobiologiaBatch,
  listTiposCultivoMicro,
  listTiposMuestraMicro,
} from '../../services/limsMicroApi';
import type { Paciente } from '../../types';
import type {
  LimsPanelExamen,
  LimsTipoExamen,
  OrigenSolicitudLims,
  TipoCultivoMicrobiologia,
  TipoMuestraMicrobiologia,
} from '../../types/lims';
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
import SolicitudMicrobiologiaForm, {
  type MicroPedidoItem,
} from './SolicitudMicrobiologiaForm';

export type PedidoTab = 'lab' | 'micro';

export interface DraftMicroPayload {
  items: Array<{
    tipo_cultivo_id: number;
    tipo_muestra_micro_id: number;
    cultivo_nombre: string;
    muestra_nombre: string;
  }>;
  observaciones?: string;
}

export interface NuevaOrdenLimsDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated?: (ordenId: number) => void;
  onCreatedMicro?: (estudioIds: number[]) => void;
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
  onAddDraftMicro?: (payload: DraftMicroPayload) => void;
  /** Si se setea, agrega exámenes a esa orden abierta en lugar de crear una nueva. */
  agregarAOrdenId?: number | null;
  agregarAOrdenNumero?: string | null;
}

const NuevaOrdenLimsDialog: React.FC<NuevaOrdenLimsDialogProps> = ({
  open,
  onClose,
  onCreated,
  onCreatedMicro,
  pacienteInicial = null,
  consultaHcId,
  medicoId,
  draftMode = false,
  onAddDraft,
  onAddDraftMicro,
  agregarAOrdenId = null,
  agregarAOrdenNumero = null,
}) => {
  const dialogTheme = useClinicalDrawerDialogTheme();
  const soloLab = Boolean(agregarAOrdenId);
  const [tab, setTab] = useState<PedidoTab>('lab');
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [mergeConfirm, setMergeConfirm] = useState<{
    id: number;
    numero: string | null;
  } | null>(null);
  const [pendingSubmit, setPendingSubmit] = useState<'draft' | 'create' | null>(null);
  const [examenes, setExamenes] = useState<LimsTipoExamen[]>([]);
  const [paneles, setPaneles] = useState<LimsPanelExamen[]>([]);
  const [cultivos, setCultivos] = useState<TipoCultivoMicrobiologia[]>([]);
  const [tiposMuestraMicro, setTiposMuestraMicro] = useState<TipoMuestraMicrobiologia[]>([]);
  const [microItems, setMicroItems] = useState<MicroPedidoItem[]>([]);
  const [observaciones, setObservaciones] = useState('');
  const [observacionesMicro, setObservacionesMicro] = useState('');

  const [paciente, setPaciente] = useState<Paciente | null>(pacienteInicial);
  const [pacienteQuery, setPacienteQuery] = useState('');
  const [pacienteOptions, setPacienteOptions] = useState<Paciente[]>([]);
  const [searchingPaciente, setSearchingPaciente] = useState(false);
  const [origenManual, setOrigenManual] = useState<OrigenSolicitudLims>('AMBULATORIO_ICPL');
  const [medicoExterno, setMedicoExterno] = useState('');
  const [medicoExternoMode, setMedicoExternoMode] = useState(false);
  const { currentUser } = useData();
  const lockMedico = shouldLockMedicoField(currentUser);
  const [medicoInterno, setMedicoInterno] = useState<Medico | null>(null);
  const [medicoQuery, setMedicoQuery] = useState('');
  const [medicoOptions, setMedicoOptions] = useState<Medico[]>([]);
  const [searchingMedico, setSearchingMedico] = useState(false);
  const usarMedicoExterno =
    medicoExternoMode || esOrigenAmbulatorioExterno(origenManual);

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
    setObservacionesMicro('');
    setMicroItems([]);
    setTab('lab');
    setError('');
    setOrigenManual('AMBULATORIO_ICPL');
    setMedicoExterno('');
    setMedicoExternoMode(false);
    setMedicoInterno(null);
    setMedicoQuery('');
    setMedicoOptions([]);
    resetSelection();
  }, [open, pacienteInicial, resetSelection]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setCatalogLoading(true);
    const loaders: Promise<unknown>[] = [
      getTiposExamenMap().then((examMap) => {
        if (!cancelled) {
          setExamenes(Array.from(examMap.values()).filter((e) => e.activo !== false));
        }
      }),
      listPanelesLims({ activo: true }).then((panList) => {
        if (!cancelled) setPaneles(panList.filter((p) => p.activo !== false));
      }),
    ];
    if (!soloLab) {
      loaders.push(
        listTiposCultivoMicro().then((list) => {
          if (!cancelled) setCultivos(list.filter((c) => c.activo !== false));
        }),
        listTiposMuestraMicro().then((list) => {
          if (!cancelled) setTiposMuestraMicro(list.filter((t) => t.activo !== false));
        })
      );
    }
    Promise.all(loaders)
      .catch((e) => {
        if (!cancelled) setError(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarCatalogo));
      })
      .finally(() => {
        if (!cancelled) setCatalogLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, soloLab]);

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

  useEffect(() => {
    if (!open || !lockMedico) return;
    const mid = getCurrentMedicoId(currentUser);
    if (!mid) return;
    let cancelled = false;
    (async () => {
      try {
        const m = await apiService.getMedico(mid);
        if (!cancelled) {
          setMedicoInterno(m);
          setMedicoQuery(`${m.apellido || ''} ${m.nombre || ''}`.trim());
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, lockMedico, currentUser]);

  useEffect(() => {
    if (!open || lockMedico || draftMode || consultaHcId || usarMedicoExterno) return;
    const q = medicoQuery.trim();
    if (q.length < 2) {
      setMedicoOptions([]);
      return;
    }
    const tmr = window.setTimeout(async () => {
      setSearchingMedico(true);
      try {
        const results = await apiService.buscarMedicos(q);
        setMedicoOptions(results);
      } catch {
        setMedicoOptions([]);
      } finally {
        setSearchingMedico(false);
      }
    }, 250);
    return () => window.clearTimeout(tmr);
  }, [medicoQuery, open, lockMedico, draftMode, consultaHcId, usarMedicoExterno]);

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

  const executeDraft = () => {
    if (hasSelection) {
      const { paneles_ids, examenes_ids, paneles_labels, examenes_labels } = resolveLabels();
      onAddDraft?.({
        paneles_ids,
        examenes_ids,
        paneles_labels,
        examenes_labels,
        observaciones: observaciones.trim() || undefined,
      });
    }
    if (microItems.length > 0) {
      onAddDraftMicro?.({
        items: microItems.map((i) => ({
          tipo_cultivo_id: i.tipo_cultivo_id,
          tipo_muestra_micro_id: i.tipo_muestra_micro_id,
          cultivo_nombre: i.cultivo_nombre,
          muestra_nombre: i.muestra_nombre,
        })),
        observaciones: observacionesMicro.trim() || undefined,
      });
    }
    onClose();
  };

  const executeCreate = async () => {
    if (!paciente?.id) {
      setError('Seleccioná un paciente.');
      return;
    }
    if (usarMedicoExterno && !medicoExterno.trim()) {
      setError('Indicá el médico solicitante externo.');
      return;
    }
    const { paneles_ids, examenes_ids } = getSelectionArrays();
    const hasLab = examenes_ids.length > 0 || paneles_ids.length > 0;
    const hasMicro = microItems.length > 0;
    if (!hasLab && !hasMicro) {
      setError('Seleccioná análisis de Lab. Clínico y/o cultivos de Microbiología.');
      return;
    }

    setSaving(true);
    try {
      let labId: number | undefined;
      if (hasLab) {
        const orden = await createSolicitudExamenLims({
          paciente_id: paciente.id,
          medico_id: usarMedicoExterno
            ? undefined
            : medicoId ?? medicoInterno?.id ?? undefined,
          consulta_hc_id: consultaHcId,
          origen_solicitud: consultaHcId ? undefined : origenManual,
          medico_externo_nombre: usarMedicoExterno
            ? medicoExterno.trim()
            : undefined,
          examenes_ids,
          paneles_ids,
          observaciones: observaciones.trim() || undefined,
        });
        labId = orden.id;
        if (orden.merged) {
          toast.success(
            `Exámenes agregados a la orden ${orden.numero || `#${orden.id}`}.`
          );
        } else {
          toast.success(`Orden Lab. ${orden.numero || `#${orden.id}`} creada.`);
        }
        onCreated?.(orden.id);
      }

      if (hasMicro) {
        const estudios = await createEstudiosMicrobiologiaBatch({
          paciente_id: paciente.id,
          medico_id: usarMedicoExterno
            ? null
            : medicoId ?? medicoInterno?.id ?? null,
          medico_externo_nombre: usarMedicoExterno
            ? medicoExterno.trim()
            : undefined,
          consulta_hc_id: consultaHcId,
          origen_solicitud: consultaHcId ? undefined : origenManual,
          observaciones: observacionesMicro.trim() || undefined,
          items: microItems.map((i) => ({
            tipo_cultivo_id: i.tipo_cultivo_id,
            tipo_muestra_micro_id: i.tipo_muestra_micro_id,
          })),
        });
        toast.success(
          estudios.length === 1
            ? `Pedido micro ${estudios[0].numero || `#${estudios[0].id}`} creado.`
            : `${estudios.length} pedidos de microbiología creados.`
        );
        onCreatedMicro?.(estudios.map((e) => e.id));
        if (!labId && estudios[0]) onCreated?.(estudios[0].id);
      }

      onClose();
    } catch (e) {
      const msg = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes);
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = async () => {
    setError('');
    const hasLab = hasSelection;
    const hasMicro = !soloLab && microItems.length > 0;

    if (agregarAOrdenId) {
      if (!hasLab) {
        setError('Seleccioná al menos un análisis o panel.');
        return;
      }
      const { paneles_ids, examenes_ids } = getSelectionArrays();
      setSaving(true);
      try {
        const orden = await agregarExamenesSolicitudLims(agregarAOrdenId, {
          examenes_ids,
          paneles_ids,
        });
        toast.success(
          `Exámenes agregados a la orden ${orden.numero || agregarAOrdenNumero || `#${orden.id}`}.`
        );
        onCreated?.(orden.id);
        onClose();
      } catch (e) {
        setError(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
      } finally {
        setSaving(false);
      }
      return;
    }

    if (!hasLab && !hasMicro) {
      setError('Seleccioná análisis de Lab. Clínico y/o cultivos de Microbiología.');
      return;
    }

    const pacienteId = paciente?.id ?? pacienteInicial?.id;
    if (hasLab && pacienteId) {
      try {
        const abierta = await getOrdenAbiertaPaciente(pacienteId);
        if (abierta) {
          setMergeConfirm({ id: abierta.id, numero: abierta.numero });
          setPendingSubmit(draftMode ? 'draft' : 'create');
          return;
        }
      } catch {
        /* si falla el check, seguimos con create */
      }
    }

    if (draftMode) {
      executeDraft();
      return;
    }
    await executeCreate();
  };

  const confirmMerge = async () => {
    const mode = pendingSubmit;
    setMergeConfirm(null);
    setPendingSubmit(null);
    if (mode === 'draft') executeDraft();
    else if (mode === 'create') await executeCreate();
  };

  const showPacientePicker = !draftMode && !pacienteInicial && !agregarAOrdenId;

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
          {draftMode
            ? 'Solicitar análisis de laboratorio'
            : agregarAOrdenId
              ? `Agregar exámenes a ${agregarAOrdenNumero || `orden #${agregarAOrdenId}`}`
              : 'Nueva orden de laboratorio'}
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

            {!consultaHcId && !draftMode && !agregarAOrdenId && (
              <>
                <FormControl fullWidth size="small">
                  <InputLabel id="origen-lims-label">Origen clínico</InputLabel>
                  <Select
                    labelId="origen-lims-label"
                    label="Origen clínico"
                    value={origenManual}
                    onChange={(e) => {
                      const next = e.target.value as OrigenSolicitudLims;
                      setOrigenManual(next);
                      if (esOrigenAmbulatorioExterno(next)) {
                        setMedicoExternoMode(true);
                        setMedicoInterno(null);
                        setMedicoQuery('');
                      }
                    }}
                  >
                    {ORIGEN_SOLICITUD_LIMS_OPTIONS.map((opt) => (
                      <MenuItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>

                {!lockMedico && !esOrigenAmbulatorioExterno(origenManual) && (
                  <Button
                    size="small"
                    variant="text"
                    onClick={() => {
                      setMedicoExternoMode((v) => !v);
                      setMedicoInterno(null);
                      setMedicoExterno('');
                      setMedicoQuery('');
                    }}
                    sx={{ alignSelf: 'flex-start' }}
                  >
                    {medicoExternoMode
                      ? 'Usar médico interno del sistema'
                      : 'Médico externo (texto libre)'}
                  </Button>
                )}

                {usarMedicoExterno ? (
                  <TextField
                    fullWidth
                    size="small"
                    required
                    label="Médico solicitante (externo)"
                    placeholder="Apellido y nombre del médico"
                    value={medicoExterno}
                    onChange={(e) => setMedicoExterno(e.target.value)}
                    helperText={
                      esOrigenAmbulatorioExterno(origenManual)
                        ? 'Receta emitida fuera de la clínica; el paciente presenta el pedido en laboratorio.'
                        : 'Médico fuera del sistema; se guarda como texto libre.'
                    }
                  />
                ) : (
                  <Autocomplete
                    options={medicoOptions}
                    value={medicoInterno}
                    onChange={(_e, value) => setMedicoInterno(value)}
                    inputValue={medicoQuery}
                    onInputChange={(_e, value, reason) => {
                      if (reason === 'reset' && lockMedico) return;
                      setMedicoQuery(value);
                    }}
                    getOptionLabel={(m) =>
                      `Dr. ${[m.apellido, m.nombre].filter(Boolean).join(', ')}${
                        m.matricula ? ` — MP ${m.matricula}` : ''
                      }`
                    }
                    isOptionEqualToValue={(a, b) => a.id === b.id}
                    loading={searchingMedico}
                    disabled={lockMedico}
                    noOptionsText={
                      medicoQuery.trim().length < 2
                        ? 'Escribí al menos 2 caracteres'
                        : 'Sin coincidencias'
                    }
                    renderInput={(params) => (
                      <TextField
                        {...params}
                        label="Médico solicitante"
                        placeholder="Apellido o matrícula"
                        helperText={
                          lockMedico
                            ? 'Se asigna automáticamente a tu usuario médico.'
                            : 'Médico de la clínica que solicita el análisis.'
                        }
                      />
                    )}
                  />
                )}
              </>
            )}

            {!soloLab && (
              <Tabs
                value={tab}
                onChange={(_, v: PedidoTab) => setTab(v)}
                variant="fullWidth"
                sx={{ borderBottom: 1, borderColor: 'divider' }}
              >
                <Tab
                  value="lab"
                  label={`Lab. Clínico${hasSelection ? ` (${selectedExamenesIds.size + selectedPanelesIds.size})` : ''}`}
                />
                <Tab
                  value="micro"
                  label={`Microbiología${microItems.length ? ` (${microItems.length})` : ''}`}
                />
              </Tabs>
            )}

            {catalogLoading ? (
              <Box display="flex" justifyContent="center" py={4}>
                <CircularProgress size={32} />
              </Box>
            ) : tab === 'lab' || soloLab ? (
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
            ) : (
              <Stack spacing={2}>
                <SolicitudMicrobiologiaForm
                  cultivos={cultivos}
                  tiposMuestra={tiposMuestraMicro}
                  items={microItems}
                  onChangeItems={setMicroItems}
                  disabled={saving}
                />
                <TextField
                  fullWidth
                  size="small"
                  multiline
                  minRows={2}
                  label="Observaciones (microbiología)"
                  value={observacionesMicro}
                  onChange={(e) => setObservacionesMicro(e.target.value)}
                  disabled={saving}
                />
              </Stack>
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
            disabled={
              saving ||
              catalogLoading ||
              (!draftMode && !agregarAOrdenId && !pacienteInicial && !paciente)
            }
          >
            {saving ? (
              <CircularProgress size={22} color="inherit" />
            ) : draftMode ? (
              'Agregar a la consulta'
            ) : agregarAOrdenId ? (
              'Agregar exámenes'
            ) : (
              'Crear pedido'
            )}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={Boolean(mergeConfirm)}
        onClose={() => {
          setMergeConfirm(null);
          setPendingSubmit(null);
        }}
      >
        <DialogTitle>Ya hay una orden solicitada</DialogTitle>
        <DialogContent>
          <DialogContentText>
            El paciente ya tiene la orden{' '}
            <strong>{mergeConfirm?.numero || `#${mergeConfirm?.id}`}</strong> pendiente de toma. Los
            exámenes de Lab. Clínico se agregarán a esa orden. Los cultivos de microbiología se
            crean aparte. ¿Continuar?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setMergeConfirm(null);
              setPendingSubmit(null);
            }}
          >
            Cancelar
          </Button>
          <Button variant="contained" onClick={() => void confirmMerge()}>
            Continuar
          </Button>
        </DialogActions>
      </Dialog>
    </ThemeProvider>
  );
};

export default NuevaOrdenLimsDialog;
