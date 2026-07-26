import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
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
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import { apiService } from '../../services/api';
import type { Medico, Paciente } from '../../types';
import type {
  EstadoEstudioMicrobiologia,
  EstudioMicrobiologia,
  TipoCultivoMicrobiologia,
  TipoMuestraMicrobiologia,
} from '../../types/lims';
import {
  createEstudioMicrobiologia,
  listEstudiosMicrobiologia,
  listTiposCultivoMicro,
  listTiposMuestraMicro,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { formatPacienteLabel } from '../../utils/pacienteFormat';
import { sugerirMuestraPorCultivo, validateCrearEstudioMicroPedido } from '../../utils/limsMicroUx';
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

const MicrobiologiaEstudios: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<EstudioMicrobiologia[]>([]);
  const [loading, setLoading] = useState(true);
  const [estadoFiltro, setEstadoFiltro] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [openCreate, setOpenCreate] = useState(false);
  const [saving, setSaving] = useState(false);

  const [paciente, setPaciente] = useState<Paciente | null>(null);
  const [pacienteQuery, setPacienteQuery] = useState('');
  const [pacienteOptions, setPacienteOptions] = useState<Paciente[]>([]);
  const [searchingPaciente, setSearchingPaciente] = useState(false);

  const [medicoInterno, setMedicoInterno] = useState<Medico | null>(null);
  const [medicoQuery, setMedicoQuery] = useState('');
  const [medicoOptions, setMedicoOptions] = useState<Medico[]>([]);
  const [medicoExterno, setMedicoExterno] = useState('');
  const [medicoExternoMode, setMedicoExternoMode] = useState(false);

  const [tiposCultivo, setTiposCultivo] = useState<TipoCultivoMicrobiologia[]>([]);
  const [tiposMuestra, setTiposMuestra] = useState<TipoMuestraMicrobiologia[]>([]);
  const [tipoCultivoId, setTipoCultivoId] = useState<number | ''>('');
  const [tipoMuestraId, setTipoMuestraId] = useState<number | ''>('');
  const [observaciones, setObservaciones] = useState('');
  const [formError, setFormError] = useState('');

  const allowed = canAccessMicrobiologia(currentUser);
  const canOp = canOperateMicrobiologia(currentUser);

  const load = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    try {
      const data = await listEstudiosMicrobiologia(
        busqueda.trim() ? { search: busqueda.trim() } : undefined
      );
      setRows(data);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarEstudiosMicro));
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

  useEffect(() => {
    if (!openCreate) return;
    let cancelled = false;
    (async () => {
      try {
        const [cultivos, muestras] = await Promise.all([
          listTiposCultivoMicro(),
          listTiposMuestraMicro(),
        ]);
        if (cancelled) return;
        setTiposCultivo(cultivos);
        setTiposMuestra(muestras);
        if (!tipoCultivoId && cultivos[0]) setTipoCultivoId(cultivos[0].id);
      } catch (e) {
        if (!cancelled) {
          toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarDatosMicro));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [openCreate]);

  useEffect(() => {
    if (!openCreate || pacienteQuery.trim().length < 2) {
      setPacienteOptions([]);
      return;
    }
    let cancelled = false;
    const t = window.setTimeout(async () => {
      setSearchingPaciente(true);
      try {
        const list = await apiService.buscarPacientes(pacienteQuery.trim());
        if (!cancelled) setPacienteOptions(list);
      } catch {
        if (!cancelled) setPacienteOptions([]);
      } finally {
        if (!cancelled) setSearchingPaciente(false);
      }
    }, 300);
    return () => {
      cancelled = true;
      window.clearTimeout(t);
    };
  }, [openCreate, pacienteQuery]);

  useEffect(() => {
    if (!openCreate || medicoExternoMode) return;
    const q = medicoQuery.trim();
    if (q.length < 2) {
      setMedicoOptions([]);
      return;
    }
    let cancelled = false;
    const t = window.setTimeout(async () => {
      try {
        const list = await apiService.buscarMedicos(q);
        if (!cancelled) setMedicoOptions(list);
      } catch {
        if (!cancelled) setMedicoOptions([]);
      }
    }, 300);
    return () => {
      cancelled = true;
      window.clearTimeout(t);
    };
  }, [openCreate, medicoQuery, medicoExternoMode]);

  useEffect(() => {
    if (!openCreate || !tipoCultivoId || !tiposCultivo.length || !tiposMuestra.length) return;
    const cultivo = tiposCultivo.find((c) => c.id === tipoCultivoId);
    if (!cultivo) return;
    const sugerida = sugerirMuestraPorCultivo(cultivo.codigo, tiposMuestra);
    if (sugerida) setTipoMuestraId(sugerida.id);
  }, [openCreate, tipoCultivoId, tiposCultivo, tiposMuestra]);

  const onOpenCreate = () => {
    setPaciente(null);
    setPacienteQuery('');
    setMedicoInterno(null);
    setMedicoQuery('');
    setMedicoExterno('');
    setMedicoExternoMode(false);
    setTipoCultivoId('');
    setTipoMuestraId('');
    setObservaciones('');
    setFormError('');
    setOpenCreate(true);
  };

  const crear = async () => {
    setFormError('');
    const err = validateCrearEstudioMicroPedido({
      pacienteId: paciente?.id,
      tipoCultivoId,
      tipoMuestraId,
      medicoInternoId: medicoInterno?.id,
      medicoExterno: medicoExternoMode ? medicoExterno : '',
      requiereMedicoExterno: medicoExternoMode,
    });
    if (err) {
      setFormError(err);
      return;
    }
    setSaving(true);
    try {
      const est = await createEstudioMicrobiologia({
        paciente_id: paciente!.id,
        tipo_cultivo_id: Number(tipoCultivoId),
        tipo_muestra_micro_id: Number(tipoMuestraId),
        observaciones: observaciones.trim() || undefined,
        medico_id: medicoExternoMode ? null : medicoInterno?.id ?? null,
        medico_externo_nombre: medicoExternoMode ? medicoExterno.trim() : undefined,
      });
      toast.success(`Estudio ${est.numero || est.id} creado`);
      setOpenCreate(false);
      navigate(`/laboratorio/microbiologia/estudios/${est.id}`);
    } catch (e) {
      setFormError(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCrearEstudioMicro));
    } finally {
      setSaving(false);
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
        Pedidos de cultivo independientes del laboratorio de química clínica: paciente, médico, tipo
        de cultivo y tipo de muestra.
      </Typography>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          <TextField
            size="small"
            label="Buscar (nº, paciente, DNI)"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
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
                <TableCell>Paciente</TableCell>
                <TableCell>Médico</TableCell>
                <TableCell>Cultivo</TableCell>
                <TableCell>Muestra</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell>Creado</TableCell>
                <TableCell align="right" />
              </TableRow>
            </TableHead>
            <TableBody>
              {filtradas.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8}>
                    <Typography color="text.secondary">Sin estudios.</Typography>
                  </TableCell>
                </TableRow>
              ) : (
                filtradas.map((r) => (
                  <TableRow key={r.id} hover>
                    <TableCell>{r.numero || r.id}</TableCell>
                    <TableCell>{r.paciente_nombre || `#${r.paciente}`}</TableCell>
                    <TableCell>{r.medico_display || '—'}</TableCell>
                    <TableCell>{r.tipo_cultivo_nombre || r.tipo_estudio}</TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        variant="outlined"
                        label={r.tipo_muestra_micro_nombre || r.muestra_tipo_nombre || '—'}
                      />
                    </TableCell>
                    <TableCell>
                      <EstudioMicrobiologiaEstadoBadge estado={r.estado} />
                    </TableCell>
                    <TableCell>
                      {r.created_at ? new Date(r.created_at).toLocaleString() : '—'}
                    </TableCell>
                    <TableCell align="right">
                      <Button
                        size="small"
                        variant="contained"
                        onClick={() => navigate(`/laboratorio/microbiologia/estudios/${r.id}`)}
                      >
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

      <Dialog open={openCreate} onClose={saving ? undefined : () => setOpenCreate(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Nuevo estudio microbiológico</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 0.5 }}>
            {formError ? (
              <Typography color="error" variant="body2">
                {formError}
              </Typography>
            ) : null}

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
                <TextField {...params} label="Paciente *" placeholder="DNI, apellido o nombre" />
              )}
            />

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
              {medicoExternoMode ? 'Usar médico interno del sistema' : 'Médico externo (texto libre)'}
            </Button>

            {medicoExternoMode ? (
              <TextField
                fullWidth
                size="small"
                label="Médico solicitante (externo)"
                placeholder="Apellido y nombre"
                value={medicoExterno}
                onChange={(e) => setMedicoExterno(e.target.value)}
              />
            ) : (
              <Autocomplete
                options={medicoOptions}
                value={medicoInterno}
                onChange={(_e, value) => setMedicoInterno(value)}
                inputValue={medicoQuery}
                onInputChange={(_e, value) => setMedicoQuery(value)}
                getOptionLabel={(m) =>
                  `Dr. ${[m.apellido, m.nombre].filter(Boolean).join(', ')}${
                    m.matricula ? ` — MP ${m.matricula}` : ''
                  }`
                }
                isOptionEqualToValue={(a, b) => a.id === b.id}
                renderInput={(params) => (
                  <TextField {...params} label="Médico solicitante" placeholder="Apellido o matrícula" />
                )}
              />
            )}

            <FormControl fullWidth size="small">
              <InputLabel>Tipo de cultivo *</InputLabel>
              <Select
                label="Tipo de cultivo *"
                value={tipoCultivoId === '' ? '' : tipoCultivoId}
                onChange={(e) => {
                  const v = e.target.value;
                  setTipoCultivoId(String(v) === '' ? '' : Number(v));
                }}
              >
                {tiposCultivo.map((t) => (
                  <MenuItem key={t.id} value={t.id}>
                    {t.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              fullWidth
              size="small"
              multiline
              minRows={2}
              label="Observaciones"
              value={observaciones}
              onChange={(e) => setObservaciones(e.target.value)}
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenCreate(false)} disabled={saving}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={() => void crear()} disabled={saving}>
            {saving ? 'Creando…' : 'Crear estudio'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default MicrobiologiaEstudios;
