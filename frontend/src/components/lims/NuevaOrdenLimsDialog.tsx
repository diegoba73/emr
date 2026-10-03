import React, { useCallback, useEffect, useState } from 'react';
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
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import { apiService } from '../../services/api';
import { useData } from '../../contexts/DataContext';
import type { Medico } from '../../types';
import { getCurrentMedicoId, shouldLockMedicoField } from '../../utils/turnoPermissions';
import { canCreateMedico, isMedicoSoloAmbulatorio } from '../../utils/permissions';
import { createMedico, getEspecialidades } from '../../services/apiService';
import type { Especialidad } from '../../types';
import {
  agregarExamenesSolicitudLims,
  createSolicitudExamenLims,
  getOrdenAbiertaPaciente,
  getRestriccionesEnsayosPaciente,
  getTiposExamenMap,
  listPanelesLims,
  type RestriccionesEnsayosLims,
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
import { formatPacienteLabel, formatPacienteObraSocial } from '../../utils/pacienteFormat';
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
import { addLocalDays, formatFechaLocal, startOfLocalDay } from '../../utils/limsOrdenesFecha';
import { mensajeBloqueoExamen, puedeOmitirRestriccionFrecuenciaEnsayos } from '../../utils/limsRestriccionesEnsayos';

export type PedidoTab = 'lab' | 'micro';

export interface DraftMicroPayload {
  items: Array<{
    tipo_cultivo_id: number;
    tipo_muestra_micro_id: number;
    cultivo_nombre: string;
    muestra_nombre: string;
  }>;
  observaciones?: string;
  fecha_programada_toma: string;
}

export interface NuevaOrdenLimsDialogProps {
  open: boolean;
  onClose: () => void;
  onCreated?: (ordenId: number) => void;
  onCreatedMicro?: (estudioIds: number[]) => void;
  /** Paciente preseleccionado (p. ej. desde consulta). */
  pacienteInicial?: Paciente | null;
  /** Solo para restricciones de ensayos (agregar a orden sin ficha completa). */
  pacienteId?: number | null;
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
    fecha_programada_toma: string;
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
  pacienteId = null,
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
  const [restriccionesEnsayos, setRestriccionesEnsayos] = useState<RestriccionesEnsayosLims>({});
  const { currentUser } = useData();
  const omiteRestriccionesEnsayos = puedeOmitirRestriccionFrecuenciaEnsayos(currentUser?.rol);
  const soloAmbulatorio = isMedicoSoloAmbulatorio(currentUser);
  const origenOptions = soloAmbulatorio
    ? ORIGEN_SOLICITUD_LIMS_OPTIONS.filter(
        (opt) => opt.group === 'Ambulatorio' || opt.group === 'Ambulatorio externo'
      )
    : ORIGEN_SOLICITUD_LIMS_OPTIONS;
  const [examenes, setExamenes] = useState<LimsTipoExamen[]>([]);
  const [paneles, setPaneles] = useState<LimsPanelExamen[]>([]);
  const [cultivos, setCultivos] = useState<TipoCultivoMicrobiologia[]>([]);
  const [tiposMuestraMicro, setTiposMuestraMicro] = useState<TipoMuestraMicrobiologia[]>([]);
  const [microItems, setMicroItems] = useState<MicroPedidoItem[]>([]);
  const [observaciones, setObservaciones] = useState('');
  const [observacionesMicro, setObservacionesMicro] = useState('');
  const [fechaProgramadaToma, setFechaProgramadaToma] = useState(() =>
    formatFechaLocal(startOfLocalDay())
  );

  const [paciente, setPaciente] = useState<Paciente | null>(pacienteInicial);
  const [pacienteQuery, setPacienteQuery] = useState('');
  const [pacienteOptions, setPacienteOptions] = useState<Paciente[]>([]);
  const [searchingPaciente, setSearchingPaciente] = useState(false);
  const [origenManual, setOrigenManual] = useState<OrigenSolicitudLims>('AMBULATORIO_ICPL');
  const [medicoExterno, setMedicoExterno] = useState('');
  const [medicoExternoMode, setMedicoExternoMode] = useState(false);
  const lockMedico = shouldLockMedicoField(currentUser);
  const [medicoInterno, setMedicoInterno] = useState<Medico | null>(null);
  const [medicoQuery, setMedicoQuery] = useState('');
  const [medicoOptions, setMedicoOptions] = useState<Medico[]>([]);
  const [searchingMedico, setSearchingMedico] = useState(false);
  const [openNuevoMedico, setOpenNuevoMedico] = useState(false);
  const [nuevoMedicoSaving, setNuevoMedicoSaving] = useState(false);
  const [nuevoMedicoError, setNuevoMedicoError] = useState('');
  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [nuevoMedicoForm, setNuevoMedicoForm] = useState({
    nombre: '',
    apellido: '',
    matricula: '',
    especialidad_id: '',
  });
  const puedeAltaMedico = canCreateMedico(currentUser);
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
  } = useSolicitudAnalisisSelection({ examenes, paneles });

  useEffect(() => {
    if (!open) return;
    setPaciente(pacienteInicial ?? null);
    setObservaciones('');
    setObservacionesMicro('');
    setFechaProgramadaToma(formatFechaLocal(startOfLocalDay()));
    setMicroItems([]);
    setTab('lab');
    setError('');
    setOrigenManual('AMBULATORIO_ICPL');
    setMedicoExterno('');
    setMedicoExternoMode(false);
    setMedicoInterno(null);
    setMedicoQuery('');
    setMedicoOptions([]);
    setRestriccionesEnsayos({});
    resetSelection();
  }, [open, pacienteInicial, resetSelection]);

  // Si solo llega pacienteId (agregar a orden), cargar ficha para mostrar obra social.
  useEffect(() => {
    if (!open || pacienteInicial) return;
    const pid = pacienteId ?? null;
    if (!pid) return;
    let cancelled = false;
    apiService
      .getPaciente(pid)
      .then((p) => {
        if (!cancelled) setPaciente(p);
      })
      .catch(() => {
        /* la orden sigue operativa aunque falle la ficha */
      });
    return () => {
      cancelled = true;
    };
  }, [open, pacienteId, pacienteInicial]);

  useEffect(() => {
    if (!open || omiteRestriccionesEnsayos) {
      setRestriccionesEnsayos({});
      return;
    }
    const pid = paciente?.id ?? pacienteInicial?.id ?? pacienteId ?? null;
    if (!pid) {
      setRestriccionesEnsayos({});
      return;
    }
    let cancelled = false;
    getRestriccionesEnsayosPaciente(pid)
      .then((data) => {
        if (!cancelled) setRestriccionesEnsayos(data || {});
      })
      .catch(() => {
        if (!cancelled) setRestriccionesEnsayos({});
      });
    return () => {
      cancelled = true;
    };
  }, [open, omiteRestriccionesEnsayos, paciente?.id, pacienteInicial?.id, pacienteId]);

  const handleToggleExamen = useCallback(
    (id: number) => {
      if (selectedExamenesIds.has(id)) {
        toggleExamen(id);
        return;
      }
      const exam = examenes.find((e) => e.id === id);
      const msg = mensajeBloqueoExamen(exam?.codigo, restriccionesEnsayos);
      if (msg) {
        window.alert(msg);
        return;
      }
      toggleExamen(id);
    },
    [examenes, restriccionesEnsayos, selectedExamenesIds, toggleExamen]
  );
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
    if (!fechaProgramadaToma) {
      setError('Indicá el día de la extracción.');
      return;
    }
    if (hasSelection) {
      const { paneles_ids, examenes_ids, paneles_labels, examenes_labels } = resolveLabels();
      onAddDraft?.({
        paneles_ids,
        examenes_ids,
        paneles_labels,
        examenes_labels,
        observaciones: observaciones.trim() || undefined,
        fecha_programada_toma: fechaProgramadaToma,
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
        fecha_programada_toma: fechaProgramadaToma,
      });
    }
    onClose();
  };

  const executeCreate = async () => {
    if (!paciente?.id) {
      setError('Seleccioná un paciente.');
      return;
    }
    if (!fechaProgramadaToma) {
      setError('Indicá el día de la extracción.');
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
          fecha_programada_toma: fechaProgramadaToma,
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
          fecha_programada_toma: fechaProgramadaToma,
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

    if (!fechaProgramadaToma) {
      setError('Indicá el día de la extracción.');
      return;
    }

    if (!hasLab && !hasMicro) {
      setError('Seleccioná análisis de Lab. Clínico y/o cultivos de Microbiología.');
      return;
    }

    const pacienteId = paciente?.id ?? pacienteInicial?.id;
    if (hasLab && pacienteId) {
      try {
        const abierta = await getOrdenAbiertaPaciente(pacienteId, fechaProgramadaToma);
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
  const pacienteVisible = paciente ?? pacienteInicial;
  const obraSocialLabel = formatPacienteObraSocial(pacienteVisible);

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
            {agregarAOrdenId ? (
              <Alert severity="info" sx={{ py: 0.5 }}>
                Si el examen cabe en un tubo ya generado se reutiliza; si necesita otro tubo o
                extracción, se crea uno pendiente de toma para imprimir y recibir.
              </Alert>
            ) : null}

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
                renderOption={(props, option) => {
                  const os = formatPacienteObraSocial(option);
                  return (
                    <li {...props} key={option.id}>
                      <Box sx={{ py: 0.25 }}>
                        <Typography variant="body2">{formatPacienteLabel(option)}</Typography>
                        <Typography variant="caption" color={os ? 'text.secondary' : 'warning.main'}>
                          {os || 'Sin obra social cargada'}
                        </Typography>
                      </Box>
                    </li>
                  );
                }}
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

            {pacienteVisible && (
              <Alert
                severity={obraSocialLabel ? 'info' : 'warning'}
                sx={{ py: 0.5 }}
              >
                Obra social:{' '}
                <strong>{obraSocialLabel || 'Sin obra social cargada'}</strong>
              </Alert>
            )}

            {!agregarAOrdenId && (
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                <TextField
                  required
                  size="small"
                  type="date"
                  label="Extracción"
                  value={fechaProgramadaToma}
                  onChange={(e) => setFechaProgramadaToma(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                  sx={{ minWidth: 170 }}
                  helperText="Día en que se saca la muestra"
                />
                <Button
                  size="small"
                  variant={
                    fechaProgramadaToma === formatFechaLocal(startOfLocalDay())
                      ? 'contained'
                      : 'outlined'
                  }
                  onClick={() => setFechaProgramadaToma(formatFechaLocal(startOfLocalDay()))}
                >
                  Hoy
                </Button>
                <Button
                  size="small"
                  variant={
                    fechaProgramadaToma ===
                    formatFechaLocal(addLocalDays(startOfLocalDay(), 1))
                      ? 'contained'
                      : 'outlined'
                  }
                  onClick={() =>
                    setFechaProgramadaToma(formatFechaLocal(addLocalDays(startOfLocalDay(), 1)))
                  }
                >
                  Mañana
                </Button>
              </Stack>
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
                    {origenOptions.map((opt) => (
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
                  <Stack spacing={1}>
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
                    {puedeAltaMedico && !lockMedico && (
                      <Button
                        size="small"
                        variant="outlined"
                        sx={{ alignSelf: 'flex-start' }}
                        onClick={() => {
                          setNuevoMedicoError('');
                          setNuevoMedicoForm({
                            nombre: '',
                            apellido: '',
                            matricula: '',
                            especialidad_id: '',
                          });
                          setOpenNuevoMedico(true);
                          void getEspecialidades()
                            .then(setEspecialidades)
                            .catch(() => setEspecialidades([]));
                        }}
                      >
                        Nuevo médico
                      </Button>
                    )}
                  </Stack>
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
                onToggleExamen={handleToggleExamen}
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

      <Dialog
        open={openNuevoMedico}
        onClose={nuevoMedicoSaving ? undefined : () => setOpenNuevoMedico(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Nuevo médico</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 1 }}>
            {nuevoMedicoError && <Alert severity="error">{nuevoMedicoError}</Alert>}
            <TextField
              label="Apellido *"
              size="small"
              value={nuevoMedicoForm.apellido}
              onChange={(e) =>
                setNuevoMedicoForm((f) => ({ ...f, apellido: e.target.value }))
              }
            />
            <TextField
              label="Nombre *"
              size="small"
              value={nuevoMedicoForm.nombre}
              onChange={(e) =>
                setNuevoMedicoForm((f) => ({ ...f, nombre: e.target.value }))
              }
            />
            <TextField
              label="Matrícula *"
              size="small"
              value={nuevoMedicoForm.matricula}
              onChange={(e) =>
                setNuevoMedicoForm((f) => ({ ...f, matricula: e.target.value }))
              }
            />
            <TextField
              select
              label="Especialidad"
              size="small"
              value={nuevoMedicoForm.especialidad_id}
              onChange={(e) =>
                setNuevoMedicoForm((f) => ({ ...f, especialidad_id: e.target.value }))
              }
            >
              <MenuItem value="">Sin especialidad</MenuItem>
              {especialidades.map((esp) => (
                <MenuItem key={esp.id} value={String(esp.id)}>
                  {esp.nombre}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button disabled={nuevoMedicoSaving} onClick={() => setOpenNuevoMedico(false)}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            disabled={nuevoMedicoSaving}
            onClick={() => {
              void (async () => {
                const nombre = nuevoMedicoForm.nombre.trim();
                const apellido = nuevoMedicoForm.apellido.trim();
                const matricula = nuevoMedicoForm.matricula.trim();
                if (!nombre || !apellido || !matricula) {
                  setNuevoMedicoError('Completá nombre, apellido y matrícula.');
                  return;
                }
                setNuevoMedicoSaving(true);
                setNuevoMedicoError('');
                try {
                  const created = await createMedico({
                    nombre,
                    apellido,
                    matricula,
                    especialidad_id: nuevoMedicoForm.especialidad_id
                      ? Number(nuevoMedicoForm.especialidad_id)
                      : undefined,
                  } as Partial<Medico>);
                  setMedicoInterno(created);
                  setMedicoQuery(
                    `Dr. ${[created.apellido, created.nombre].filter(Boolean).join(', ')}`
                  );
                  setMedicoOptions((prev) =>
                    prev.some((m) => m.id === created.id) ? prev : [created, ...prev]
                  );
                  setOpenNuevoMedico(false);
                  toast.success('Médico dado de alta.');
                } catch (e) {
                  setNuevoMedicoError(
                    getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.genericClinicalAction)
                  );
                } finally {
                  setNuevoMedicoSaving(false);
                }
              })();
            }}
          >
            {nuevoMedicoSaving ? <CircularProgress size={20} color="inherit" /> : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>
    </ThemeProvider>
  );
};

export default NuevaOrdenLimsDialog;
