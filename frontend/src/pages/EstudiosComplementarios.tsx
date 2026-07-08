import React, { useCallback, useEffect, useState } from 'react';
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
import AsyncAutocomplete from '../components/common/AsyncAutocomplete';
import { useData } from '../contexts/DataContext';
import { parseEstudiosApiError } from '../modules/estudios/apiErrors';
import {
  ESTADO_CHIP_COLOR,
  ESTADO_LABELS,
  MODALIDAD_OPTIONS,
  ORIGEN_OPTIONS,
} from '../modules/estudios/constants';
import {
  canAccessEstudiosModule,
  canAsignarTurnoEstudio,
  canWriteEstudio,
} from '../modules/estudios/permissions';
import {
  createEstudioComplementario,
  listEstudiosComplementarios,
} from '../services/estudiosComplementariosApi';
import { turnosAgendarEstudioPath } from '../utils/agendarEstudioNavigation';
import type {
  CreateEstudioComplementarioPayload,
  EstudioComplementario,
  EstudioEstado,
  EstudioModalidad,
} from '../types/estudios';
import { Paciente } from '../types';
import { formatPacienteLabel, formatPacienteNombre } from '../utils/pacienteFormat';

const EstudiosComplementarios: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser, pacientes, loadPacientes } = useData();
  const [estudios, setEstudios] = useState<EstudioComplementario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filtroEstado, setFiltroEstado] = useState<string>('');
  const [filtroModalidad, setFiltroModalidad] = useState<string>('');
  const [busquedaPaciente, setBusquedaPaciente] = useState('');
  const [busquedaPacienteDebounced, setBusquedaPacienteDebounced] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<CreateEstudioComplementarioPayload>({
    paciente_id: 0,
    modalidad: 'IMAGEN_RX',
    origen: 'INTERNO',
    descripcion_clinica: '',
    centro_realizador: '',
  });

  const writeAccess = canWriteEstudio(currentUser);
  const puedeAsignarTurno = canAsignarTurnoEstudio(currentUser);
  const rol = (currentUser?.rol || '').toLowerCase();

  const irAgendarEnCalendario = (estudio: EstudioComplementario) => {
    navigate(turnosAgendarEstudioPath(estudio.id));
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = {};
      if (filtroEstado) params.estado = filtroEstado;
      if (filtroModalidad) params.modalidad = filtroModalidad;
      if (busquedaPacienteDebounced.trim()) params.search = busquedaPacienteDebounced.trim();
      const data = await listEstudiosComplementarios(params);
      setEstudios(data);
    } catch (e) {
      setError(parseEstudiosApiError(e, 'No se pudieron cargar los estudios complementarios.'));
      setEstudios([]);
    } finally {
      setLoading(false);
    }
  }, [filtroEstado, filtroModalidad, busquedaPacienteDebounced]);

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
    if (writeAccess) {
      loadPacientes();
    }
  }, [writeAccess, loadPacientes]);

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
    setForm({
      paciente_id: defaultPacienteId,
      modalidad: 'IMAGEN_RX',
      origen: 'INTERNO',
      descripcion_clinica: '',
      centro_realizador: '',
    });
    setCreateOpen(true);
  };

  const handleCreate = async () => {
    if (!form.paciente_id) {
      setError('Seleccione un paciente.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const created = await createEstudioComplementario(form);
      setCreateOpen(false);
      navigate(`/estudios-complementarios/${created.id}`);
    } catch (e) {
      setError(parseEstudiosApiError(e, 'No se pudo crear el estudio.'));
    } finally {
      setSaving(false);
    }
  };

  if (!canAccessEstudiosModule(currentUser)) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">No tiene acceso al módulo de estudios complementarios.</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }} className="fade-in">
      <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
        Estudios complementarios
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
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel>Estado</InputLabel>
            <Select
              label="Estado"
              value={filtroEstado}
              onChange={(e) => setFiltroEstado(e.target.value)}
            >
              <MenuItem value="">Todos</MenuItem>
              {(Object.keys(ESTADO_LABELS) as EstudioEstado[]).map((st) => (
                <MenuItem key={st} value={st}>
                  {ESTADO_LABELS[st]}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Modalidad</InputLabel>
            <Select
              label="Modalidad"
              value={filtroModalidad}
              onChange={(e) => setFiltroModalidad(e.target.value)}
            >
              <MenuItem value="">Todas</MenuItem>
              {MODALIDAD_OPTIONS.map((m) => (
                <MenuItem key={m.value} value={m.value}>
                  {m.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="outlined" onClick={load} disabled={loading}>
            Actualizar
          </Button>
          {writeAccess && (
            <Button variant="contained" startIcon={<Add />} onClick={openCreate}>
              Nuevo estudio
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
                <TableCell>Tipo / modalidad</TableCell>
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
                    {row.tipo_estudio_nombre || '—'}
                    <Typography variant="caption" display="block" color="text.secondary">
                      {MODALIDAD_OPTIONS.find((m) => m.value === row.modalidad)?.label ||
                        row.modalidad}
                    </Typography>
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
                        navigate(`/estudios-complementarios/${row.id}`);
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
        <DialogTitle>Nuevo estudio complementario</DialogTitle>
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
              <InputLabel>Modalidad *</InputLabel>
              <Select
                label="Modalidad *"
                value={form.modalidad}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    modalidad: e.target.value as EstudioModalidad,
                  }))
                }
              >
                {MODALIDAD_OPTIONS.map((m) => (
                  <MenuItem key={m.value} value={m.value}>
                    {m.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
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
