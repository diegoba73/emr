import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useData } from '../contexts/DataContext';
import { canAsignarTurnoEstudio } from '../modules/estudios/permissions';
import {
  agendarPedidoEstudio,
  listMedicoTipos,
  listPedidosEstudio,
  listTipoSalas,
  pedidoFotoDownloadPath,
  type PedidoEstudioPaciente,
} from '../services/pedidosEstudioApi';
import { listTiposEstudioComplementario } from '../services/estudiosComplementariosApi';
import { getSlotsMedico, type SlotMedico } from '../services/agendaMedica';
import { apiClient } from '../services/apiClient';
import { getSafeClinicalActionMessage } from '../utils/apiError';
import type { TipoEstudioComplementario } from '../types/estudios';

const PedidosEstudioBandeja: React.FC = () => {
  const { currentUser, medicos, loadMedicos, refreshTurnos } = useData();
  const puede = canAsignarTurnoEstudio(currentUser);
  const [rows, setRows] = useState<PedidoEstudioPaciente[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tipos, setTipos] = useState<TipoEstudioComplementario[]>([]);
  const [sel, setSel] = useState<PedidoEstudioPaciente | null>(null);
  const [tipoId, setTipoId] = useState<number | ''>('');
  const [medicoId, setMedicoId] = useState<number | ''>('');
  const [fecha, setFecha] = useState('');
  const [slots, setSlots] = useState<SlotMedico[]>([]);
  const [slot, setSlot] = useState<SlotMedico | null>(null);
  const [saving, setSaving] = useState(false);
  const [medicoTipos, setMedicoTipos] = useState<number[]>([]);
  const [salasTipo, setSalasTipo] = useState<number[]>([]);
  const [fotoUrl, setFotoUrl] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [pedidos, catalog] = await Promise.all([
        listPedidosEstudio({ estado: 'PENDIENTE' }),
        listTiposEstudioComplementario().catch(() => [] as TipoEstudioComplementario[]),
      ]);
      setRows(pedidos);
      setTipos(catalog);
      await loadMedicos?.();
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudieron cargar los pedidos.'));
    } finally {
      setLoading(false);
    }
  }, [loadMedicos]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!tipoId) {
      setMedicoTipos([]);
      setSalasTipo([]);
      return;
    }
    let active = true;
    Promise.all([listMedicoTipos(), listTipoSalas(Number(tipoId))])
      .then(([mt, salas]) => {
        if (!active) return;
        setMedicoTipos(mt.filter((r) => r.tipo_estudio === Number(tipoId)).map((r) => r.medico));
        setSalasTipo(salas.map((s) => s.recurso));
      })
      .catch(() => {
        if (active) {
          setMedicoTipos([]);
          setSalasTipo([]);
        }
      });
    return () => {
      active = false;
    };
  }, [tipoId]);

  const medicosFiltrados = useMemo(() => {
    if (!tipoId || medicoTipos.length === 0) return [];
    return (medicos || []).filter((m) => medicoTipos.includes(m.id));
  }, [medicos, medicoTipos, tipoId]);

  useEffect(() => {
    if (!medicoId || !fecha || !tipoId) {
      setSlots([]);
      setSlot(null);
      return;
    }
    let active = true;
    // Sin salas en catálogo (o carga fallida → []): cero opciones, no todas.
    if (salasTipo.length === 0) {
      setSlots([]);
      setSlot(null);
      return;
    }
    getSlotsMedico(Number(medicoId), fecha, 'ESTUDIO', {
      tipo_estudio: Number(tipoId),
    })
      .then((s) => {
        if (!active) return;
        setSlots(s.filter((x) => x.recurso_id && salasTipo.includes(x.recurso_id)));
        setSlot(null);
      })
      .catch(() => {
        if (active) {
          setSlots([]);
          setSlot(null);
        }
      });
    return () => {
      active = false;
    };
  }, [medicoId, fecha, salasTipo, tipoId]);

  const openAgendar = async (p: PedidoEstudioPaciente) => {
    setSel(p);
    setTipoId('');
    setMedicoId('');
    setFecha('');
    setSlots([]);
    setSlot(null);
    setFotoUrl(null);
    try {
      const res = await apiClient.get(pedidoFotoDownloadPath(p.id), { responseType: 'blob' });
      setFotoUrl(URL.createObjectURL(res.data));
    } catch {
      setFotoUrl(null);
    }
  };

  const closeAgendar = () => {
    if (fotoUrl) URL.revokeObjectURL(fotoUrl);
    setFotoUrl(null);
    setSel(null);
  };

  const confirmar = async () => {
    if (!sel || !tipoId || !medicoId || !slot) {
      setError('Completá tipo, médico y horario.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await agendarPedidoEstudio(sel.id, {
        tipo_estudio: Number(tipoId),
        medico_id: Number(medicoId),
        inicio: slot.inicio,
        horario_id: slot.horario_id,
      });
      await refreshTurnos?.();
      closeAgendar();
      await load();
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo agendar el pedido.'));
    } finally {
      setSaving(false);
    }
  };

  if (!puede) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>No tenés permiso para gestionar pedidos de estudio.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        Pedidos de estudio (app / portal)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        El paciente subió la foto del pedido. Tipificá, elegí médico y horario; el turno queda
        reservado para que el paciente confirme o reprograme.
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {loading ? (
        <CircularProgress />
      ) : rows.length === 0 ? (
        <Alert severity="info">No hay pedidos pendientes.</Alert>
      ) : (
        <Stack spacing={1}>
          {rows.map((p) => (
            <Box
              key={p.id}
              sx={{
                p: 2,
                border: 1,
                borderColor: 'divider',
                borderRadius: 1,
                display: 'flex',
                justifyContent: 'space-between',
                gap: 2,
                flexWrap: 'wrap',
              }}
            >
              <Box>
                <Typography fontWeight={600}>{p.paciente_nombre}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {p.origen_canal} · {new Date(p.created_at).toLocaleString('es-AR')}
                  {p.notas ? ` · ${p.notas}` : ''}
                </Typography>
              </Box>
              <Button variant="contained" size="small" onClick={() => void openAgendar(p)}>
                Ver foto y agendar
              </Button>
            </Box>
          ))}
        </Stack>
      )}

      <Dialog open={Boolean(sel)} onClose={closeAgendar} fullWidth maxWidth="md">
        <DialogTitle>Agendar pedido #{sel?.id}</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            {fotoUrl ? (
              <Box
                component="img"
                src={fotoUrl}
                alt="Pedido médico"
                sx={{ maxWidth: '100%', maxHeight: 360, objectFit: 'contain', borderRadius: 1 }}
              />
            ) : (
              <Alert severity="warning">No se pudo cargar la foto.</Alert>
            )}
            <TextField
              select
              label="Tipo de estudio"
              value={tipoId}
              onChange={(e) => {
                setTipoId(e.target.value ? Number(e.target.value) : '');
                setMedicoId('');
              }}
              fullWidth
            >
              {tipos.map((t) => (
                <MenuItem key={t.id} value={t.id}>
                  {t.nombre}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Médico"
              value={medicoId}
              onChange={(e) => setMedicoId(e.target.value ? Number(e.target.value) : '')}
              fullWidth
              disabled={!tipoId}
              helperText={
                tipoId && medicosFiltrados.length === 0
                  ? 'Ningún médico tiene este tipo en el catálogo. Configuralo en Catálogo agenda estudios.'
                  : undefined
              }
            >
              {medicosFiltrados.map((m) => (
                <MenuItem key={m.id} value={m.id}>
                  {m.apellido}, {m.nombre}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              type="date"
              label="Fecha"
              value={fecha}
              onChange={(e) => setFecha(e.target.value)}
              InputLabelProps={{ shrink: true }}
              fullWidth
              disabled={!medicoId}
            />
            <TextField
              select
              label="Horario"
              value={slot?.inicio || ''}
              onChange={(e) => setSlot(slots.find((s) => s.inicio === e.target.value) || null)}
              fullWidth
              disabled={!fecha || slots.length === 0}
              helperText={
                fecha && tipoId && salasTipo.length === 0
                  ? 'No hay salas compatibles en el catálogo para este tipo. Configuralo antes de agendar.'
                  : fecha && slots.length === 0
                    ? 'Sin slots de estudio libres ese día.'
                    : undefined
              }
            >
              {slots.map((s) => (
                <MenuItem key={s.inicio} value={s.inicio}>
                  {new Date(s.inicio).toLocaleTimeString('es-AR', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                  {s.recurso_nombre ? ` · ${s.recurso_nombre}` : ''}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeAgendar} disabled={saving}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={() => void confirmar()} disabled={saving || !slot}>
            {saving ? 'Guardando…' : 'Agendar (queda reservado)'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PedidosEstudioBandeja;
