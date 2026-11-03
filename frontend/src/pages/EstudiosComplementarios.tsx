import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
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
import { Add, Clear, Visibility } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { withNavBack } from '../utils/navBack';
import { useData } from '../contexts/DataContext';
import { parseEstudiosApiError } from '../modules/estudios/apiErrors';
import {
  PRACTICA_OPTIONS,
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
  canWriteEstudio,
} from '../modules/estudios/permissions';
import {
  getBandejasResumenEstudios,
  listEstudiosComplementarios,
  listTiposEstudioComplementario,
} from '../services/estudiosComplementariosApi';
import { apiClient } from '../services/apiClient';
import ProgramacionTurnoForm from '../components/turnos/ProgramacionTurnoForm';
import type { EstudioComplementario, TipoEstudioComplementario } from '../types/estudios';
import type { Turno } from '../types';
import {
  fechaLocalHoy,
  kindLabel,
  mergeProgramacionRows,
  type ProgramacionTipoFiltro,
} from '../utils/programacionTurnosRows';
import { canCreateTurno } from '../utils/turnoPermissions';

type TurnosPagePayload = Turno[] | { results?: Turno[]; next?: string | null };

function nextTurnosPath(nextUrl: string): string | null {
  try {
    const parsed = new URL(nextUrl, apiClient.defaults.baseURL || undefined);
    return parsed.pathname.replace(/^\/api/, '') + parsed.search;
  } catch {
    return null;
  }
}

async function fetchTurnosRango(desde: string, hasta: string): Promise<Turno[]> {
  const rows: Turno[] = [];
  let path: string | null = `/turnos/?start=${encodeURIComponent(desde)}&end=${encodeURIComponent(
    hasta + 'T23:59:59'
  )}&page_size=100`;
  const seen = new Set<string>();
  while (path && seen.size < 8) {
    if (seen.has(path)) break;
    seen.add(path);
    const pagePath: string = path;
    const { data } = (await apiClient.get(pagePath)) as { data: TurnosPagePayload };
    if (Array.isArray(data)) {
      rows.push(...data);
      break;
    }
    if (data.results?.length) rows.push(...data.results);
    if (!data.next) {
      path = null;
      break;
    }
    path = nextTurnosPath(String(data.next));
  }
  return rows;
}

const EstudiosComplementarios: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [estudios, setEstudios] = useState<EstudioComplementario[]>([]);
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [tipos, setTipos] = useState<TipoEstudioComplementario[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filtroBandeja, setFiltroBandeja] = useState<BandejaEstudioKey>('todos');
  const [conteos, setConteos] = useState<BandejasResumen>(emptyBandejasResumen);
  const [filtroPractica, setFiltroPractica] = useState<string>('');
  const [filtroTipoActividad, setFiltroTipoActividad] = useState<ProgramacionTipoFiltro>('');
  const [busquedaPaciente, setBusquedaPaciente] = useState('');
  const [busquedaPacienteDebounced, setBusquedaPacienteDebounced] = useState('');
  const [fechaDesde, setFechaDesde] = useState(() => fechaLocalHoy());
  const [fechaHasta, setFechaHasta] = useState(() => fechaLocalHoy());
  const [createOpen, setCreateOpen] = useState(false);
  const initialLoadDone = useRef(false);
  const practicaOptions = practicaOptionsFromTipos(tipos);

  const writeAccess = canWriteEstudio(currentUser) || canCreateTurno(currentUser);
  const rol = (currentUser?.rol || '').toLowerCase();
  const tituloModulo =
    rol === 'paciente' ? MODULO_ESTUDIOS_LABEL_PACIENTE : MODULO_ESTUDIOS_LABEL;
  const mostrarBandejas = filtroTipoActividad !== 'CONSULTA';

  const load = useCallback(async () => {
    if (!initialLoadDone.current) setLoading(true);
    setError(null);
    try {
      const baseParams: Record<string, string | number> = {};
      if (filtroPractica) baseParams.practica = filtroPractica;
      if (filtroTipoActividad && filtroTipoActividad !== 'CONSULTA') {
        baseParams.tipo_actividad = filtroTipoActividad;
      }
      if (busquedaPacienteDebounced.trim()) {
        baseParams.search = busquedaPacienteDebounced.trim();
      }
      const listParams = {
        ...baseParams,
        ...(filtroBandeja !== 'todos' && mostrarBandejas ? { bandeja: filtroBandeja } : {}),
      };

      const loadEstudios = filtroTipoActividad !== 'CONSULTA';
      const [dataEstudios, resumen, dataTurnos] = await Promise.all([
        loadEstudios
          ? listEstudiosComplementarios(listParams)
          : Promise.resolve([] as EstudioComplementario[]),
        loadEstudios
          ? getBandejasResumenEstudios(baseParams)
          : Promise.resolve({} as Record<string, number>),
        fetchTurnosRango(fechaDesde || '2000-01-01', fechaHasta || '2100-12-31').catch(
          () => [] as Turno[]
        ),
      ]);
      setEstudios(dataEstudios);
      setConteos({ ...emptyBandejasResumen(), ...resumen });
      setTurnos(dataTurnos);
    } catch (e) {
      setError(parseEstudiosApiError(e, 'No se pudo cargar la programación.'));
      setEstudios([]);
      setTurnos([]);
    } finally {
      initialLoadDone.current = true;
      setLoading(false);
    }
  }, [
    filtroBandeja,
    filtroPractica,
    filtroTipoActividad,
    busquedaPacienteDebounced,
    fechaDesde,
    fechaHasta,
    mostrarBandejas,
  ]);

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
  }, [currentUser]);

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

  const rows = useMemo(() => {
    let merged = mergeProgramacionRows(turnos, estudios, filtroTipoActividad);
    if (busquedaPacienteDebounced.trim()) {
      const q = busquedaPacienteDebounced.trim().toLowerCase();
      merged = merged.filter((r) => r.pacienteNombre.toLowerCase().includes(q));
    }
    if (filtroPractica) {
      const practLabel = labelPractica(filtroPractica, practicaOptions).toLowerCase();
      merged = merged.filter(
        (r) =>
          r.kind !== 'CONSULTA' &&
          (r.prestacion.toLowerCase().includes(practLabel) ||
            r.prestacion.toLowerCase().includes(filtroPractica.toLowerCase()))
      );
    }
    if (fechaDesde) {
      const desdeMs = new Date(`${fechaDesde}T00:00:00`).getTime();
      merged = merged.filter((r) => {
        if (!r.fechaInicio) return filtroTipoActividad !== 'CONSULTA';
        return new Date(r.fechaInicio).getTime() >= desdeMs;
      });
    }
    if (fechaHasta) {
      const hastaMs = new Date(`${fechaHasta}T23:59:59`).getTime();
      merged = merged.filter((r) => {
        if (!r.fechaInicio) return filtroTipoActividad !== 'CONSULTA';
        return new Date(r.fechaInicio).getTime() <= hastaMs;
      });
    }
    return merged;
  }, [
    turnos,
    estudios,
    filtroTipoActividad,
    busquedaPacienteDebounced,
    filtroPractica,
    practicaOptions,
    fechaDesde,
    fechaHasta,
  ]);

  const puedeFiltrarPorPaciente = rol !== 'paciente';

  const setHoy = () => {
    const hoy = fechaLocalHoy();
    setFechaDesde(hoy);
    setFechaHasta(hoy);
  };

  const openCreate = () => setCreateOpen(true);

  const irDetalle = (row: (typeof rows)[0]) => {
    if (row.estudioId) {
      navigate(
        `/estudios-complementarios/${row.estudioId}`,
        withNavBack('/estudios-complementarios', '← Volver al listado')
      );
      return;
    }
    if (row.turnoId) {
      navigate(`/turnos?turno=${row.turnoId}`);
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
        Lista de consultas, estudios, procedimientos y cirugías con turno. Usá el calendario para la
        vista visual.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Paper sx={{ p: 2, mb: 2 }}>
        {mostrarBandejas && (
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
        )}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          {puedeFiltrarPorPaciente && (
            <>
              <TextField
                size="small"
                label="Buscar paciente"
                placeholder="Nombre, apellido o DNI"
                value={busquedaPaciente}
                onChange={(e) => setBusquedaPaciente(e.target.value)}
                sx={{ minWidth: 240 }}
              />
              {busquedaPaciente && (
                <Button size="small" startIcon={<Clear />} onClick={() => setBusquedaPaciente('')}>
                  Limpiar
                </Button>
              )}
            </>
          )}
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Tipo</InputLabel>
            <Select
              label="Tipo"
              value={filtroTipoActividad}
              onChange={(e) => {
                setFiltroTipoActividad(e.target.value as ProgramacionTipoFiltro);
                if (e.target.value === 'CONSULTA') setFiltroBandeja('todos');
              }}
            >
              <MenuItem value="">Todos</MenuItem>
              <MenuItem value="CONSULTA">Consulta médica</MenuItem>
              <MenuItem value="ESTUDIO">Estudios</MenuItem>
              <MenuItem value="PROCEDIMIENTO">Procedimientos</MenuItem>
              <MenuItem value="CIRUGIA">Cirugías</MenuItem>
            </Select>
          </FormControl>
          <Autocomplete
            size="small"
            sx={{ minWidth: 240 }}
            options={practicaOptions.length ? practicaOptions : PRACTICA_OPTIONS}
            value={
              (practicaOptions.length ? practicaOptions : PRACTICA_OPTIONS).find(
                (m) => m.value === filtroPractica
              ) || null
            }
            onChange={(_e, opt) => setFiltroPractica(opt?.value || '')}
            getOptionLabel={(o) => o.label}
            isOptionEqualToValue={(a, b) => a.value === b.value}
            renderInput={(params) => (
              <TextField {...params} label="Prestación / práctica" placeholder="Buscar…" />
            )}
          />
          <TextField
            size="small"
            label="Desde"
            type="date"
            value={fechaDesde}
            onChange={(e) => setFechaDesde(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 150 }}
          />
          <TextField
            size="small"
            label="Hasta"
            type="date"
            value={fechaHasta}
            onChange={(e) => setFechaHasta(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ width: 150 }}
          />
          <Button variant="outlined" onClick={setHoy}>
            Hoy
          </Button>
          <Button variant="outlined" onClick={load} disabled={loading}>
            Actualizar
          </Button>
          {writeAccess && (
            <Button variant="contained" startIcon={<Add />} onClick={openCreate}>
              Nuevo turno
            </Button>
          )}
        </Box>
      </Paper>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : rows.length === 0 ? (
        <Alert severity="info">No hay ítems para los filtros seleccionados.</Alert>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Fecha / hora</TableCell>
                {rol !== 'paciente' && <TableCell>Paciente</TableCell>}
                <TableCell>Tipo</TableCell>
                <TableCell>Prestación</TableCell>
                <TableCell>Profesional</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell align="right">Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.key} hover>
                  <TableCell>
                    {row.fechaInicio
                      ? new Date(row.fechaInicio).toLocaleString('es-AR', {
                          day: '2-digit',
                          month: '2-digit',
                          year: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                        })
                      : '—'}
                  </TableCell>
                  {rol !== 'paciente' && <TableCell>{row.pacienteNombre}</TableCell>}
                  <TableCell>
                    <Chip
                      size="small"
                      variant="outlined"
                      color={
                        row.kind === 'CONSULTA'
                          ? 'primary'
                          : row.kind === 'CIRUGIA'
                            ? 'error'
                            : row.kind === 'PROCEDIMIENTO'
                              ? 'warning'
                              : 'info'
                      }
                      label={kindLabel(row.kind)}
                    />
                  </TableCell>
                  <TableCell>{row.prestacion}</TableCell>
                  <TableCell>{row.medicoNombre}</TableCell>
                  <TableCell>
                    <Chip size="small" label={row.estadoLabel} />
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      startIcon={<Visibility />}
                      onClick={() => irDetalle(row)}
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

      <Dialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        maxWidth="sm"
        fullWidth
        scroll="paper"
      >
        <DialogTitle>Nuevo turno / solicitud</DialogTitle>
        <DialogContent dividers>
          <ProgramacionTurnoForm
            allowConsulta
            initialTipo="CONSULTA"
            onCancel={() => setCreateOpen(false)}
            onSuccess={() => {
              setCreateOpen(false);
              void load();
            }}
            submitLabel="Crear"
          />
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default EstudiosComplementarios;
