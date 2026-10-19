import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { Add, CalendarMonth, Clear, Visibility } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { withNavBack } from '../utils/navBack';
import AsyncAutocomplete from '../components/common/AsyncAutocomplete';
import { useData } from '../contexts/DataContext';
import { parseEstudiosApiError } from '../modules/estudios/apiErrors';
import {
  ESTADO_CHIP_COLOR,
  ESTADO_LABELS,
  PRACTICA_OPTIONS,
  ORIGEN_OPTIONS,
  labelPractica,
  practicaOptionsFromTipos,
} from '../modules/estudios/constants';
import {
  BANDEJA_OPTIONS,
  emptyBandejasResumen,
  MODULO_ESTUDIOS_LABEL,
  MODULO_ESTUDIOS_LABEL_PACIENTE,
  type BandejaEstudioKey,
  type BandejasResumen,
} from '../modules/estudios/bandejas';
import {
  canAccessEstudiosModule,
  canAsignarTurnoEstudio,
  canWriteEstudio,
} from '../modules/estudios/permissions';
import {
  createEstudioComplementario,
  getBandejasResumenEstudios,
  listEstudiosComplementarios,
  listTiposEstudioComplementario,
} from '../services/estudiosComplementariosApi';
import {
  getCirugiaAbordajes,
  getCirugiaEspecialidades,
  getCirugiaProcedimientos,
} from '../services/apiService';
import { turnosAgendarEstudioPath } from '../utils/agendarEstudioNavigation';
import type {
  CirugiaAbordajeCatalogo,
  CirugiaEspecialidadCatalogo,
  CirugiaProcedimientoCatalogo,
  CreateEstudioComplementarioPayload,
  EstudioComplementario,
  EstudioPractica,
  TipoEstudioComplementario,
} from '../types/estudios';
import { Medico, Paciente } from '../types';
import { formatPacienteLabel, formatPacienteNombre } from '../utils/pacienteFormat';

function labelMedico(m: Medico): string {
  const ap = (m.apellido || '').trim();
  const no = (m.nombre || '').trim();
  if (ap && no) return `${ap}, ${no}`;
  return ap || no || `Médico #${m.id}`;
}

function labelCirugiaIndicacion(row: EstudioComplementario): string {
  const parts = [
    row.cirugia_especialidad_snapshot || row.cirugia_especialidad_nombre,
    row.cirugia_procedimiento_snapshot || row.cirugia_procedimiento_nombre,
    row.cirugia_abordaje_snapshot || row.cirugia_abordaje_nombre,
  ].filter(Boolean);
  if (parts.length) return parts.join(' · ');
  return row.procedimiento_catalogo_nombre || 'Cirugía';
}

const EstudiosComplementarios: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser, pacientes, loadPacientes, medicos, loadMedicos } = useData();
  const [estudios, setEstudios] = useState<EstudioComplementario[]>([]);
  const [tipos, setTipos] = useState<TipoEstudioComplementario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filtroBandeja, setFiltroBandeja] = useState<BandejaEstudioKey>('todos');
  const [conteos, setConteos] = useState<BandejasResumen>(emptyBandejasResumen);
  const [filtroPractica, setFiltroPractica] = useState<string>('');
  const [filtroTipoActividad, setFiltroTipoActividad] = useState<string>('');
  const [busquedaPaciente, setBusquedaPaciente] = useState('');
  const [busquedaPacienteDebounced, setBusquedaPacienteDebounced] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [procSeleccionado, setProcSeleccionado] = useState<{
    id: number;
    nombre: string;
    clasificacion_quirurgica?: string;
  } | null>(null);
  const [cirEspOptions, setCirEspOptions] = useState<CirugiaEspecialidadCatalogo[]>([]);
  const [cirProcOptions, setCirProcOptions] = useState<CirugiaProcedimientoCatalogo[]>([]);
  const [cirAbrOptions, setCirAbrOptions] = useState<CirugiaAbordajeCatalogo[]>([]);
  const [form, setForm] = useState<CreateEstudioComplementarioPayload>({
    paciente_id: 0,
    practica: '',
    tipo_actividad: 'ESTUDIO',
    medico_solicitante: null,
    anestesista_previsto: null,
    origen: 'INTERNO',
    descripcion_clinica: '',
    centro_realizador: '',
  });
  const initialLoadDone = useRef(false);
  const practicaOptions = practicaOptionsFromTipos(tipos);

  const writeAccess = canWriteEstudio(currentUser);
  const puedeAsignarTurno = canAsignarTurnoEstudio(currentUser);
  const rol = (currentUser?.rol || '').toLowerCase();
  const tituloModulo =
    rol === 'paciente' ? MODULO_ESTUDIOS_LABEL_PACIENTE : MODULO_ESTUDIOS_LABEL;

  const irAgendarEnCalendario = (estudio: EstudioComplementario) => {
    navigate(turnosAgendarEstudioPath(estudio.id));
  };

  const load = useCallback(async () => {
    if (!initialLoadDone.current) setLoading(true);
    setError(null);
    try {
      const baseParams: Record<string, string | number> = {};
      if (filtroPractica) baseParams.practica = filtroPractica;
      if (filtroTipoActividad) baseParams.tipo_actividad = filtroTipoActividad;
      if (busquedaPacienteDebounced.trim()) {
        baseParams.search = busquedaPacienteDebounced.trim();
      }
      const listParams = {
        ...baseParams,
        ...(filtroBandeja !== 'todos' ? { bandeja: filtroBandeja } : {}),
      };
      const [data, resumen] = await Promise.all([
        listEstudiosComplementarios(listParams),
        getBandejasResumenEstudios(baseParams),
      ]);
      setEstudios(data);
      setConteos({ ...emptyBandejasResumen(), ...resumen });
    } catch (e) {
      setError(parseEstudiosApiError(e, 'No se pudieron cargar los estudios.'));
      setEstudios([]);
    } finally {
      initialLoadDone.current = true;
      setLoading(false);
    }
  }, [filtroBandeja, filtroPractica, filtroTipoActividad, busquedaPacienteDebounced]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setBusquedaPacienteDebounced(busquedaPaciente);
    }, 400);
    return () => window.clearTimeout(timer);
  }, [busquedaPaciente]);

  useEffect(() => {
    if (!canAccessEstudiosModule(currentUser)) return;
    load();
  }, [currentUser, load]);

  useEffect(() => {
    if (!canAccessEstudiosModule(currentUser)) return;
    void listTiposEstudioComplementario()
      .then(setTipos)
      .catch(() => setTipos([]));
    void getCirugiaEspecialidades(true)
      .then((rows) => setCirEspOptions(rows as CirugiaEspecialidadCatalogo[]))
      .catch(() => setCirEspOptions([]));
  }, [currentUser]);

  useEffect(() => {
    if (!form.cirugia_especialidad) {
      setCirProcOptions([]);
      return;
    }
    void getCirugiaProcedimientos(form.cirugia_especialidad, true)
      .then((rows) => setCirProcOptions(rows as CirugiaProcedimientoCatalogo[]))
      .catch(() => setCirProcOptions([]));
  }, [form.cirugia_especialidad]);

  useEffect(() => {
    if (!form.cirugia_procedimiento) {
      setCirAbrOptions([]);
      return;
    }
    void getCirugiaAbordajes(form.cirugia_procedimiento, true)
      .then((rows) => setCirAbrOptions(rows as CirugiaAbordajeCatalogo[]))
      .catch(() => setCirAbrOptions([]));
  }, [form.cirugia_procedimiento]);

  useEffect(() => {
    if (!canAccessEstudiosModule(currentUser)) return;
    const refreshIfVisible = () => {
      if (document.visibilityState === 'visible') void load();
    };
    document.addEventListener('visibilitychange', refreshIfVisible);
    window.addEventListener('focus', refreshIfVisible);
    const id = window.setInterval(refreshIfVisible, 20000);
    return () => {
      document.removeEventListener('visibilitychange', refreshIfVisible);
      window.removeEventListener('focus', refreshIfVisible);
      window.clearInterval(id);
    };
  }, [currentUser, load]);

  useEffect(() => {
    if (writeAccess) {
      loadPacientes();
      loadMedicos();
    }
  }, [writeAccess, loadPacientes, loadMedicos]);

  const pacienteNombre = useCallback(
    (row: EstudioComplementario) => {
      if (row.paciente_nombre) return row.paciente_nombre;
      const p = pacientes.find((item) => item.id === row.paciente_id);
      return p ? formatPacienteNombre(p) : `Paciente #${row.paciente_id}`;
    },
    [pacientes]
  );

  const puedeFiltrarPorPaciente = rol !== 'paciente';

  const openCreate = () => {
    const defaultPacienteId =
      rol === 'paciente' && currentUser?.paciente?.id ? currentUser.paciente.id : 0;
    const defaultPractica = practicaOptions[0]?.value || PRACTICA_OPTIONS[0]?.value || '';
    const defaultTipo = tipos.find((t) => (t.practica || t.codigo) === defaultPractica);
    setForm({
      paciente_id: defaultPacienteId,
      practica: defaultPractica,
      tipo_estudio: defaultTipo?.id,
      tipo_actividad: 'ESTUDIO',
      procedimiento_catalogo: null,
      cirugia_especialidad: null,
      cirugia_procedimiento: null,
      cirugia_abordaje: null,
      medico_solicitante: null,
      anestesista_previsto: null,
      origen: 'INTERNO',
      descripcion_clinica: '',
      centro_realizador: '',
    });
    setProcSeleccionado(null);
    setCreateOpen(true);
  };

  const handleCreate = async () => {
    if (!form.paciente_id) {
      setError('Seleccione un paciente.');
      return;
    }
    const esProc = form.tipo_actividad === 'PROCEDIMIENTO';
    const esCir = form.tipo_actividad === 'CIRUGIA';
    if (!form.medico_solicitante) {
      setError(
        esCir
          ? 'Seleccioná el cirujano.'
          : 'Seleccioná el profesional que realiza el estudio o procedimiento.'
      );
      return;
    }
    if (esCir && !form.anestesista_previsto) {
      setError('Seleccioná el anestesista.');
      return;
    }
    if (esProc && !form.procedimiento_catalogo) {
      setError('Seleccioná un procedimiento del catálogo (no quirúrgico).');
      return;
    }
    if (esCir && (!form.cirugia_especialidad || !form.cirugia_procedimiento)) {
      setError('Seleccioná especialidad y procedimiento quirúrgico.');
      return;
    }
    if (!esProc && !esCir && !form.practica && !form.tipo_estudio) {
      setError('Seleccioná una práctica.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const payload: CreateEstudioComplementarioPayload = esProc
        ? {
            paciente_id: form.paciente_id,
            tipo_actividad: 'PROCEDIMIENTO',
            procedimiento_catalogo: form.procedimiento_catalogo,
            medico_solicitante: form.medico_solicitante,
            origen: form.origen,
            descripcion_clinica: form.descripcion_clinica,
            centro_realizador: form.centro_realizador,
          }
        : esCir
          ? {
              paciente_id: form.paciente_id,
              tipo_actividad: 'CIRUGIA',
              cirugia_especialidad: form.cirugia_especialidad,
              cirugia_procedimiento: form.cirugia_procedimiento,
              cirugia_abordaje: form.cirugia_abordaje || null,
              medico_solicitante: form.medico_solicitante,
              anestesista_previsto: form.anestesista_previsto,
              origen: form.origen,
              descripcion_clinica: form.descripcion_clinica,
              centro_realizador: form.centro_realizador,
            }
        : {
            ...form,
            tipo_actividad: 'ESTUDIO',
            procedimiento_catalogo: null,
            anestesista_previsto: null,
            medico_solicitante: form.medico_solicitante,
          };
      const created = await createEstudioComplementario(payload);
      setCreateOpen(false);
      navigate(
        `/estudios-complementarios/${created.id}`,
        withNavBack('/estudios-complementarios', '← Volver al listado')
      );
    } catch (e) {
      setError(parseEstudiosApiError(e, 'No se pudo crear el estudio.'));
    } finally {
      setSaving(false);
    }
  };

  if (!canAccessEstudiosModule(currentUser)) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">No tiene acceso a {MODULO_ESTUDIOS_LABEL.toLowerCase()}.</Alert>
      </Box>
    );
  }

  return (
    <Box data-demo="page-estudios" sx={{ p: 3 }} className="fade-in">
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
        {tituloModulo}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Imagenología e informes clínicos por paciente (sin visor PACS).
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
          {BANDEJA_OPTIONS.map((opt) => {
            const count = conteos[opt.key] ?? 0;
            const selected = filtroBandeja === opt.key;
            return (
              <Chip
                key={opt.key}
                label={`${opt.label} (${count})`}
                color={selected ? 'primary' : 'default'}
                variant={selected ? 'filled' : 'outlined'}
                onClick={() => setFiltroBandeja(opt.key)}
                clickable
              />
            );
          })}
        </Box>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          {puedeFiltrarPorPaciente && (
            <>
              <TextField
                size="small"
                label="Buscar paciente"
                placeholder="Nombre, apellido o DNI"
                value={busquedaPaciente}
                onChange={(e) => setBusquedaPaciente(e.target.value)}
                sx={{ minWidth: 280 }}
              />
              {busquedaPaciente && (
                <Button
                  size="small"
                  startIcon={<Clear />}
                  onClick={() => setBusquedaPaciente('')}
                >
                  Limpiar paciente
                </Button>
              )}
            </>
          )}
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Tipo</InputLabel>
            <Select
              label="Tipo"
              value={filtroTipoActividad}
              onChange={(e) => setFiltroTipoActividad(e.target.value)}
            >
              <MenuItem value="">Todos</MenuItem>
              <MenuItem value="ESTUDIO">Estudios</MenuItem>
              <MenuItem value="PROCEDIMIENTO">Procedimientos</MenuItem>
              <MenuItem value="CIRUGIA">Cirugías</MenuItem>
            </Select>
          </FormControl>
          <Autocomplete
            size="small"
            sx={{ minWidth: 260 }}
            options={practicaOptions}
            value={practicaOptions.find((m) => m.value === filtroPractica) || null}
            onChange={(_e, opt) => setFiltroPractica(opt?.value || '')}
            getOptionLabel={(o) => o.label}
            isOptionEqualToValue={(a, b) => a.value === b.value}
            renderInput={(params) => (
              <TextField {...params} label="Práctica" placeholder="Buscar práctica…" />
            )}
          />
          <Button variant="outlined" onClick={load} disabled={loading}>
            Actualizar
          </Button>
          {writeAccess && (
            <Button variant="contained" startIcon={<Add />} onClick={openCreate}>
              Nueva solicitud
            </Button>
          )}
        </Box>
      </Paper>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : estudios.length === 0 ? (
        <Alert severity="info">No hay estudios para los filtros seleccionados.</Alert>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                {rol !== 'paciente' && <TableCell>Paciente</TableCell>}
                <TableCell>Actividad</TableCell>
                <TableCell>Tipo / práctica</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell>Turno</TableCell>
                <TableCell>F. solicitud</TableCell>
                <TableCell>F. realización</TableCell>
                <TableCell>Centro</TableCell>
                <TableCell align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {estudios.map((row) => (
                <TableRow
                  key={row.id}
                  hover
                  sx={{ cursor: row.estado === 'SOLICITADO' && puedeAsignarTurno ? 'pointer' : undefined }}
                  onClick={() => {
                    if (row.estado === 'SOLICITADO' && puedeAsignarTurno) {
                      irAgendarEnCalendario(row);
                    }
                  }}
                >
                  <TableCell>{row.id}</TableCell>
                  {rol !== 'paciente' && (
                    <TableCell>{pacienteNombre(row)}</TableCell>
                  )}
                  <TableCell>
                    <Chip
                      size="small"
                      variant="outlined"
                      label={row.tipo_actividad === 'CIRUGIA' ? 'Cirugía' : row.tipo_actividad === 'PROCEDIMIENTO' ? 'Procedimiento' : 'Estudio'}
                    />
                  </TableCell>
                  <TableCell>
                    {row.tipo_actividad === 'CIRUGIA'
                      ? labelCirugiaIndicacion(row)
                      : row.tipo_actividad === 'PROCEDIMIENTO'
                        ? (row.procedimiento_catalogo_nombre || 'Procedimiento')
                        : row.tipo_estudio_nombre || '—'}
                    {row.tipo_actividad === 'ESTUDIO' && (
                      <Typography variant="caption" display="block" color="text.secondary">
                        {labelPractica(row.practica, practicaOptions)}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={ESTADO_LABELS[row.estado]}
                      color={ESTADO_CHIP_COLOR[row.estado]}
                    />
                  </TableCell>
                  <TableCell>
                    {row.turno_fecha_hora_inicio ? (
                      <>
                        {new Date(row.turno_fecha_hora_inicio).toLocaleString()}
                        {row.turno_recurso_nombre ? (
                          <Typography variant="caption" display="block" color="text.secondary">
                            {row.turno_recurso_nombre}
                          </Typography>
                        ) : null}
                      </>
                    ) : row.estado === 'SOLICITADO' && puedeAsignarTurno ? (
                      <Typography variant="body2" color="primary">
                        Clic para elegir horario en calendario
                      </Typography>
                    ) : (
                      '—'
                    )}
                  </TableCell>
                  <TableCell>
                    {row.fecha_solicitud
                      ? new Date(row.fecha_solicitud).toLocaleString()
                      : '—'}
                  </TableCell>
                  <TableCell>
                    {row.fecha_realizacion
                      ? new Date(row.fecha_realizacion).toLocaleString()
                      : '—'}
                  </TableCell>
                  <TableCell>{row.centro_realizador || '—'}</TableCell>
                  <TableCell align="right">
                    {row.estado === 'SOLICITADO' && puedeAsignarTurno && (
                      <Button
                        size="small"
                        startIcon={<CalendarMonth />}
                        onClick={(ev) => {
                          ev.stopPropagation();
                          irAgendarEnCalendario(row);
                        }}
                        sx={{ mr: 1 }}
                      >
                        Turno
                      </Button>
                    )}
                    <Button
                      size="small"
                      startIcon={<Visibility />}
                      onClick={(ev) => {
                        ev.stopPropagation();
                        navigate(
                          `/estudios-complementarios/${row.id}`,
                          withNavBack('/estudios-complementarios', '← Volver al listado')
                        );
                      }}
                    >
                      Ver
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Nueva solicitud — Estudios y procedimientos</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            {rol !== 'paciente' ? (
              <AsyncAutocomplete<Paciente>
                label="Paciente *"
                endpoint="/pacientes/"
                value={pacientes.find((p) => p.id === form.paciente_id) || null}
                onChange={(p) => setForm((f) => ({ ...f, paciente_id: p?.id || 0 }))}
                getOptionLabel={formatPacienteLabel}
              />
            ) : (
              <TextField
                label="Paciente"
                value={formatPacienteLabel(
                  pacientes.find((p) => p.id === form.paciente_id) || undefined
                )}
                disabled
                fullWidth
              />
            )}
            <FormControl fullWidth>
              <InputLabel>Tipo de actividad</InputLabel>
              <Select
                label="Tipo de actividad"
                value={form.tipo_actividad || 'ESTUDIO'}
                onChange={(e) => {
                  setForm((f) => ({
                    ...f,
                    tipo_actividad: e.target.value as 'ESTUDIO' | 'PROCEDIMIENTO' | 'CIRUGIA',
                    procedimiento_catalogo: null,
                    cirugia_especialidad: null,
                    cirugia_procedimiento: null,
                    cirugia_abordaje: null,
                    anestesista_previsto: null,
                  }));
                  setProcSeleccionado(null);
                }}
              >
                <MenuItem value="ESTUDIO">Estudio</MenuItem>
                <MenuItem value="PROCEDIMIENTO">Procedimiento (no quirúrgico)</MenuItem>
                <MenuItem value="CIRUGIA">Cirugía</MenuItem>
              </Select>
            </FormControl>
            <Autocomplete
              options={medicos}
              value={medicos.find((m) => m.id === form.medico_solicitante) || null}
              onChange={(_e, opt) =>
                setForm((f) => ({ ...f, medico_solicitante: opt?.id || null }))
              }
              getOptionLabel={labelMedico}
              isOptionEqualToValue={(a, b) => a.id === b.id}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label={
                    form.tipo_actividad === 'CIRUGIA'
                      ? 'Cirujano *'
                      : 'Profesional que lo realiza *'
                  }
                  required
                />
              )}
            />
            {form.tipo_actividad === 'CIRUGIA' && (
              <Autocomplete
                options={medicos}
                value={medicos.find((m) => m.id === form.anestesista_previsto) || null}
                onChange={(_e, opt) =>
                  setForm((f) => ({ ...f, anestesista_previsto: opt?.id || null }))
                }
                getOptionLabel={labelMedico}
                isOptionEqualToValue={(a, b) => a.id === b.id}
                renderInput={(params) => (
                  <TextField {...params} label="Anestesista *" required />
                )}
              />
            )}
            {form.tipo_actividad === 'PROCEDIMIENTO' ? (
              <AsyncAutocomplete<{ id: number; nombre: string; clasificacion_quirurgica?: string }>
                label="Procedimiento *"
                endpoint="/procedimientos-catalogo/"
                value={procSeleccionado}
                onChange={(opt) => {
                  if (opt && opt.clasificacion_quirurgica === 'QUIRURGICO') {
                    setError('Ese ítem es quirúrgico; usá el alta Cirugía.');
                    setProcSeleccionado(null);
                    setForm((f) => ({ ...f, procedimiento_catalogo: null }));
                    return;
                  }
                  setProcSeleccionado(opt);
                  setForm((f) => ({ ...f, procedimiento_catalogo: opt?.id || null }));
                }}
                getOptionLabel={(o) => o.nombre}
                required
                minSearchLength={2}
                placeholder="Buscar procedimiento…"
              />
            ) : form.tipo_actividad === 'CIRUGIA' ? (
              <>
                <Autocomplete
                  options={cirEspOptions}
                  value={cirEspOptions.find((e) => e.id === form.cirugia_especialidad) || null}
                  onChange={(_e, opt) =>
                    setForm((f) => ({
                      ...f,
                      cirugia_especialidad: opt?.id || null,
                      cirugia_procedimiento: null,
                      cirugia_abordaje: null,
                    }))
                  }
                  getOptionLabel={(o) => o.nombre}
                  isOptionEqualToValue={(a, b) => a.id === b.id}
                  renderInput={(params) => (
                    <TextField {...params} label="Especialidad quirúrgica *" required />
                  )}
                />
                <Autocomplete
                  options={cirProcOptions}
                  disabled={!form.cirugia_especialidad}
                  value={cirProcOptions.find((p) => p.id === form.cirugia_procedimiento) || null}
                  onChange={(_e, opt) =>
                    setForm((f) => ({
                      ...f,
                      cirugia_procedimiento: opt?.id || null,
                      cirugia_abordaje: null,
                    }))
                  }
                  getOptionLabel={(o) => o.nombre}
                  isOptionEqualToValue={(a, b) => a.id === b.id}
                  renderInput={(params) => (
                    <TextField {...params} label="Procedimiento quirúrgico *" required />
                  )}
                />
                <Autocomplete
                  options={cirAbrOptions}
                  disabled={!form.cirugia_procedimiento}
                  value={cirAbrOptions.find((a) => a.id === form.cirugia_abordaje) || null}
                  onChange={(_e, opt) =>
                    setForm((f) => ({ ...f, cirugia_abordaje: opt?.id || null }))
                  }
                  getOptionLabel={(o) => o.nombre}
                  isOptionEqualToValue={(a, b) => a.id === b.id}
                  renderInput={(params) => (
                    <TextField {...params} label="Abordaje (opcional)" />
                  )}
                />
              </>
            ) : (
            <Autocomplete
              options={practicaOptions}
              value={practicaOptions.find((m) => m.value === form.practica) || null}
              onChange={(_e, opt) => {
                const practica = (opt?.value || '') as EstudioPractica;
                const tipo = tipos.find((t) => (t.practica || t.codigo) === practica);
                setForm((f) => ({
                  ...f,
                  practica,
                  tipo_estudio: tipo?.id,
                }));
              }}
              getOptionLabel={(o) => o.label}
              isOptionEqualToValue={(a, b) => a.value === b.value}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Práctica *"
                  required
                  placeholder="Buscar práctica…"
                />
              )}
            />
            )}
            <FormControl fullWidth>
              <InputLabel>Origen</InputLabel>
              <Select
                label="Origen"
                value={form.origen || 'INTERNO'}
                onChange={(e) => setForm((f) => ({ ...f, origen: e.target.value }))}
              >
                {ORIGEN_OPTIONS.map((o) => (
                  <MenuItem key={o.value} value={o.value}>
                    {o.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              label="Centro realizador"
              value={form.centro_realizador || ''}
              onChange={(e) => setForm((f) => ({ ...f, centro_realizador: e.target.value }))}
              fullWidth
            />
            <TextField
              label="Descripción clínica"
              value={form.descripcion_clinica || ''}
              onChange={(e) => setForm((f) => ({ ...f, descripcion_clinica: e.target.value }))}
              multiline
              minRows={2}
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateOpen(false)}>Cancelar</Button>
          <Button variant="contained" onClick={handleCreate} disabled={saving}>
            {saving ? 'Guardando…' : 'Crear'}
          </Button>
        </DialogActions>
      </Dialog>

    </Box>
  );
};

export default EstudiosComplementarios;
