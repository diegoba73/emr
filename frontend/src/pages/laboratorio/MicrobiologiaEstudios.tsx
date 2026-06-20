import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
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
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { EstadoEstudioMicrobiologia, EstudioMicrobiologia } from '../../types/lims';
import {
  createEstudioMicrobiologia,
  formatDrfError,
  listContenedoresLims,
  listEstudiosMicrobiologia,
  listMuestrasPorSolicitud,
  listSolicitudesExamen,
  listTiposMuestraLims,
} from '../../services/limsApi';
import type { LimsTipoContenedor, LimsTipoMuestra, MuestraTransaccional, SolicitudExamenLims } from '../../types/lims';
import {
  filterMuestrasProcesablesMicro,
  formatMuestraTransaccionalMicroLabel,
  formatSolicitudMicroLabel,
  validateCrearEstudioMicroSelection,
} from '../../utils/limsMicroUx';
import { canAccessMicrobiologia, canOperateMicrobiologia } from '../../utils/limsAccess';
import { EstudioMicrobiologiaEstadoBadge } from '../../components/lims/micro/MicroBadges';

const ESTADOS: EstadoEstudioMicrobiologia[] = [
  'PENDIENTE',
  'RECIBIDO',
  'SEMBRADO',
  'LECTURA_PRELIMINAR',
  'IDENTIFICACION',
  'ANTIBIOGRAMA',
  'LISTO_PARA_VALIDAR',
  'VALIDADO',
  'INFORMADO',
  'CANCELADO',
];

const TIPOS = ['CULTIVO_RUTINA', 'UROCULTIVO', 'HEMOCULTIVO', 'COPROCULTIVO', 'CULTIVO_HERIDA', 'OTRO'];

const MicrobiologiaEstudios: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<EstudioMicrobiologia[]>([]);
  const [loading, setLoading] = useState(true);
  const [estadoFiltro, setEstadoFiltro] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [openCreate, setOpenCreate] = useState(false);
  const [form, setForm] = useState({
    solicitud_id: '' as number | '',
    muestra_id: '' as number | '',
    tipo_estudio: 'CULTIVO_RUTINA',
    observaciones: '',
  });
  const [solicitudesPicker, setSolicitudesPicker] = useState<SolicitudExamenLims[]>([]);
  const [muestrasPicker, setMuestrasPicker] = useState<MuestraTransaccional[]>([]);
  const [pickerLoading, setPickerLoading] = useState(false);
  const [tiposMuestraMap, setTiposMuestraMap] = useState<Map<number, LimsTipoMuestra>>(new Map());
  const [contenedoresMap, setContenedoresMap] = useState<Map<number, LimsTipoContenedor>>(new Map());

  const allowed = canAccessMicrobiologia(currentUser);
  const canOp = canOperateMicrobiologia(currentUser);

  const load = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    try {
      const data = await listEstudiosMicrobiologia(busqueda.trim() ? { search: busqueda.trim() } : undefined);
      setRows(data);
    } catch (e) {
      toast.error(formatDrfError(e));
    } finally {
      setLoading(false);
    }
  }, [allowed, busqueda]);

  useEffect(() => {
    load();
  }, [load]);

  const filtradas = useMemo(() => {
    if (!estadoFiltro) return rows;
    return rows.filter((r) => r.estado === estadoFiltro);
  }, [rows, estadoFiltro]);

  const loadPickerData = useCallback(async () => {
    setPickerLoading(true);
    try {
      const [sols, tipos, conts] = await Promise.all([
        listSolicitudesExamen(),
        listTiposMuestraLims(),
        listContenedoresLims(),
      ]);
      setSolicitudesPicker(
        sols.filter((s) => s.estado !== 'CANCELADO' && s.estado !== 'ENTREGADO').slice(0, 200)
      );
      setTiposMuestraMap(new Map(tipos.map((t) => [t.id, t])));
      setContenedoresMap(new Map(conts.map((c) => [c.id, c])));
    } catch (e) {
      toast.error(formatDrfError(e));
    } finally {
      setPickerLoading(false);
    }
  }, []);

  const onOpenCreate = () => {
    setForm({ solicitud_id: '', muestra_id: '', tipo_estudio: 'CULTIVO_RUTINA', observaciones: '' });
    setMuestrasPicker([]);
    setOpenCreate(true);
    loadPickerData();
  };

  const onSelectSolicitud = async (sid: number | '') => {
    setForm((f) => ({ ...f, solicitud_id: sid, muestra_id: '' }));
    if (sid === '') {
      setMuestrasPicker([]);
      return;
    }
    setPickerLoading(true);
    try {
      const sol = solicitudesPicker.find((s) => s.id === sid);
      const muestras = await listMuestrasPorSolicitud(sid, sol?.numero ?? undefined);
      setMuestrasPicker(filterMuestrasProcesablesMicro(muestras));
    } catch (e) {
      toast.error(formatDrfError(e));
      setMuestrasPicker([]);
    } finally {
      setPickerLoading(false);
    }
  };

  const muestrasProcesables = useMemo(() => muestrasPicker, [muestrasPicker]);

  const crear = async () => {
    const err = validateCrearEstudioMicroSelection(form.solicitud_id, form.muestra_id);
    if (err) {
      toast.error(err);
      return;
    }
    const sid = Number(form.solicitud_id);
    const mid = Number(form.muestra_id);
    try {
      const est = await createEstudioMicrobiologia({
        solicitud_id: sid,
        muestra_id: mid,
        tipo_estudio: form.tipo_estudio,
        observaciones: form.observaciones,
      });
      toast.success('Estudio creado');
      setOpenCreate(false);
      navigate(`/laboratorio/microbiologia/estudios/${est.id}`);
    } catch (e) {
      toast.error(formatDrfError(e));
    }
  };

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>Sin acceso a microbiología LIMS.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>
        Estudios de microbiología
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Flujo independiente de <code>ResultadoExamen</code> clínico general. Vinculado a orden y muestra LIMS.
      </Typography>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          <TextField size="small" label="Buscar (nº estudio / orden)" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Estado</InputLabel>
            <Select label="Estado" value={estadoFiltro} onChange={(e) => setEstadoFiltro(e.target.value)}>
              <MenuItem value="">Todos</MenuItem>
              {ESTADOS.map((s) => (
                <MenuItem key={s} value={s}>
                  {s}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button variant="outlined" onClick={load}>
            Actualizar
          </Button>
          {canOp && (
            <Button variant="contained" onClick={onOpenCreate}>
              Nuevo estudio
            </Button>
          )}
          <Button variant="text" onClick={() => navigate('/laboratorio/microbiologia/catalogos')}>
            Catálogos
          </Button>
        </Box>
      </Paper>

      {loading ? (
        <CircularProgress />
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Nº estudio</TableCell>
                <TableCell>Solicitud</TableCell>
                <TableCell>Muestra</TableCell>
                <TableCell>Tipo</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell>Creado</TableCell>
                <TableCell align="right" />
              </TableRow>
            </TableHead>
            <TableBody>
              {filtradas.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7}>
                    <Typography color="text.secondary">Sin estudios.</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filtradas.map((r) => (
                  <TableRow key={r.id} hover>
                    <TableCell>{r.numero || r.id}</TableCell>
                    <TableCell>
                      <Chip size="small" label={`#${r.solicitud}`} variant="outlined" />
                    </TableCell>
                    <TableCell>#{r.muestra}</TableCell>
                    <TableCell>{r.tipo_estudio}</TableCell>
                    <TableCell>
                      <EstudioMicrobiologiaEstadoBadge estado={r.estado} />
                    </TableCell>
                    <TableCell>{r.created_at ? new Date(r.created_at).toLocaleString() : '—'}</TableCell>
                    <TableCell align="right">
                      <Button size="small" variant="contained" onClick={() => navigate(`/laboratorio/microbiologia/estudios/${r.id}`)}>
                        Abrir
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      <Dialog open={openCreate} onClose={() => setOpenCreate(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Nuevo estudio microbiológico</DialogTitle>
        <DialogContent>
          {pickerLoading && <CircularProgress size={24} sx={{ my: 1 }} />}
          <FormControl fullWidth margin="dense" disabled={pickerLoading}>
            <InputLabel>Solicitud LIMS</InputLabel>
            <Select
              label="Solicitud LIMS"
              value={form.solicitud_id === '' ? '' : form.solicitud_id}
              onChange={(e) => {
                const v = e.target.value;
                onSelectSolicitud(String(v) === '' ? '' : Number(v));
              }}
            >
              <MenuItem value="">
                <em>Seleccionar…</em>
              </MenuItem>
              {solicitudesPicker.map((s) => (
                <MenuItem key={s.id} value={s.id}>
                  {formatSolicitudMicroLabel(s)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth margin="dense" disabled={form.solicitud_id === '' || pickerLoading}>
            <InputLabel>Muestra transaccional</InputLabel>
            <Select
              label="Muestra transaccional"
              value={form.muestra_id === '' ? '' : form.muestra_id}
              onChange={(e) => {
                const v = e.target.value;
                setForm((f) => ({
                  ...f,
                  muestra_id: String(v) === '' ? '' : Number(v),
                }));
              }}
            >
              <MenuItem value="">
                <em>Seleccionar…</em>
              </MenuItem>
              {muestrasProcesables.map((m) => (
                <MenuItem key={m.id} value={m.id}>
                  {formatMuestraTransaccionalMicroLabel(m, tiposMuestraMap, contenedoresMap)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {form.solicitud_id !== '' && muestrasProcesables.length === 0 && !pickerLoading && (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
              Sin muestras en RECIBIDA, CONSERVADA o EN_PROCESO para esta solicitud.
            </Typography>
          )}
          <Accordion disableGutters elevation={0} sx={{ mt: 1 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="caption">Ingreso manual (avanzado)</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <TextField
                fullWidth
                margin="dense"
                label="ID solicitud LIMS"
                type="number"
                value={form.solicitud_id === '' ? '' : form.solicitud_id}
                onChange={(e) => {
                  const v = e.target.value;
                  onSelectSolicitud(v === '' ? '' : Number(v));
                }}
              />
              <TextField
                fullWidth
                margin="dense"
                label="ID muestra transaccional"
                type="number"
                value={form.muestra_id === '' ? '' : form.muestra_id}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    muestra_id: e.target.value === '' ? '' : Number(e.target.value),
                  }))
                }
              />
            </AccordionDetails>
          </Accordion>
          <FormControl fullWidth margin="dense">
            <InputLabel>Tipo</InputLabel>
            <Select label="Tipo" value={form.tipo_estudio} onChange={(e) => setForm((f) => ({ ...f, tipo_estudio: e.target.value }))}>
              {TIPOS.map((t) => (
                <MenuItem key={t} value={t}>
                  {t}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            fullWidth
            margin="dense"
            multiline
            label="Observaciones"
            value={form.observaciones}
            onChange={(e) => setForm((f) => ({ ...f, observaciones: e.target.value }))}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCreate(false)}>Cancelar</Button>
          <Button variant="contained" onClick={crear}>
            Crear
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MicrobiologiaEstudios;
