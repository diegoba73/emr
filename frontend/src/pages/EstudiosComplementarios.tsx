import React, { useCallback, useEffect, useMemo, useState } from 'react';
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
import { Add, Visibility } from '@mui/icons-material';
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
  canWriteEstudio,
} from '../modules/estudios/permissions';
import {
  createEstudioComplementario,
  listEstudiosComplementarios,
} from '../services/estudiosComplementariosApi';
import type {
  CreateEstudioComplementarioPayload,
  EstudioComplementario,
  EstudioEstado,
  EstudioModalidad,
} from '../types/estudios';
import { Paciente } from '../types';
import { formatPacienteLabel } from '../utils/pacienteFormat';

const EstudiosComplementarios: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser, pacientes, loadPacientes } = useData();
  const [estudios, setEstudios] = useState<EstudioComplementario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filtroEstado, setFiltroEstado] = useState<string>('');
  const [filtroModalidad, setFiltroModalidad] = useState<string>('');
  const [filtroPaciente, setFiltroPaciente] = useState<Paciente | null>(null);
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
  const rol = (currentUser?.rol || '').toLowerCase();

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | number> = {};
      if (filtroEstado) params.estado = filtroEstado;
      if (filtroModalidad) params.modalidad = filtroModalidad;
      if (filtroPaciente?.id) params.paciente = filtroPaciente.id;
      const data = await listEstudiosComplementarios(params);
      setEstudios(data);
    } catch (e) {
      setError(parseEstudiosApiError(e, 'No se pudieron cargar los estudios complementarios.'));
      setEstudios([]);
    } finally {
      setLoading(false);
    }
  }, [filtroEstado, filtroModalidad, filtroPaciente]);

  useEffect(() => {
    if (!canAccessEstudiosModule(currentUser)) return;
    load();
  }, [currentUser, load]);

  useEffect(() => {
    if (writeAccess) {
      loadPacientes();
    }
  }, [writeAccess, loadPacientes]);

  const pacienteNombre = useMemo(() => {
    const map = new Map(pacientes.map((p) => [p.id, formatPacienteLabel(p)]));
    return (id: number) => map.get(id) || `Paciente #${id}`;
  }, [pacientes]);

  const openCreate = () => {
    const defaultPacienteId =
      rol === 'paciente' && currentUser?.paciente?.id
        ? currentUser.paciente.id
        : filtroPaciente?.id || 0;
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
          {writeAccess && rol !== 'paciente' && (
            <AsyncAutocomplete<Paciente>
              label="Paciente"
              endpoint="/pacientes/"
              value={filtroPaciente}
              onChange={setFiltroPaciente}
              getOptionLabel={formatPacienteLabel}
              sx={{ minWidth: 280 }}
            />
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
                <TableCell>F. solicitud</TableCell>
                <TableCell>F. realización</TableCell>
                <TableCell>Centro</TableCell>
                <TableCell align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {estudios.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell>{row.id}</TableCell>
                  {rol !== 'paciente' && (
                    <TableCell>{pacienteNombre(row.paciente_id)}</TableCell>
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
                    <Button
                      size="small"
                      startIcon={<Visibility />}
                      onClick={() => navigate(`/estudios-complementarios/${row.id}`)}
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
