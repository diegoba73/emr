import ReservaTurnoPaciente from '../../components/ReservaTurnoPaciente';
import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import {
  getMisTurnos,
  getSlotsReprogramacionTurno,
  type SlotMedico,
} from '../../services/agendaMedica';
import { apiService } from '../../services/api';
import {
  listPedidosEstudio,
  type PedidoEstudioPaciente,
} from '../../services/pedidosEstudioApi';
import type { Turno } from '../../types';
import { formatFechaHoraDisplay } from '../../utils/dateFieldFormat';
import { getSafeClinicalActionMessage } from '../../utils/apiError';
import { formatLocalDateTimeSeconds } from '../../utils/formatLocalDateTime';

const PortalTurnos: React.FC = () => {
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [pedidos, setPedidos] = useState<PedidoEstudioPaciente[]>([]);
  const [loading, setLoading] = useState(true);
  const [pedidosLoading, setPedidosLoading] = useState(true);
  const [pedidosError, setPedidosError] = useState('');
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');
  const [reprogFecha, setReprogFecha] = useState('');
  const [reprogSlots, setReprogSlots] = useState<SlotMedico[]>([]);
  const [showReprog, setShowReprog] = useState(false);

  useEffect(() => {
    setLoading(true);
    getMisTurnos()
      .then(setTurnos)
      .catch(() => setTurnos([]))
      .finally(() => setLoading(false));
  }, [reload]);

  useEffect(() => {
    setPedidosLoading(true);
    setPedidosError('');
    listPedidosEstudio()
      .then(setPedidos)
      .catch((e) => {
        setPedidos([]);
        setPedidosError(getSafeClinicalActionMessage(e, 'No se pudieron cargar tus pedidos.'));
      })
      .finally(() => setPedidosLoading(false));
  }, [reload]);

  // La API devuelve únicamente los turnos vinculados al usuario autenticado.
  const mine = turnos;

  const now = Date.now();
  const activos = mine
    .filter(
      (t) =>
        t.fecha_hora_inicio &&
        new Date(t.fecha_hora_inicio).getTime() >= now &&
        (t.estado === 'RESERVADO' || t.estado === 'CONFIRMADO'),
    )
    .sort(
      (a, b) =>
        new Date(a.fecha_hora_inicio).getTime() - new Date(b.fecha_hora_inicio).getTime(),
    );
  const turnoActivo = activos[0] ?? null;
  const proximos = activos;
  const historial = mine
    .filter((t) => t.fecha_hora_inicio && new Date(t.fecha_hora_inicio).getTime() < now)
    .sort(
      (a, b) =>
        new Date(b.fecha_hora_inicio).getTime() - new Date(a.fecha_hora_inicio).getTime(),
    );

  const medicoId =
    turnoActivo?.medico?.id || turnoActivo?.medico_id || null;
  const puedeReprogramarPedido = Boolean(
    turnoActivo?.viene_de_pedido_estudio && medicoId
  );

  const confirmar = async () => {
    if (!turnoActivo) return;
    setBusy(true);
    setError('');
    setOk('');
    try {
      await apiService.confirmarTurno(turnoActivo.id);
      setOk('Turno confirmado.');
      setReload((r) => r + 1);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo confirmar el turno.'));
    } finally {
      setBusy(false);
    }
  };

  const cargarSlots = async () => {
    if (!turnoActivo || !/^\d{4}-\d{2}-\d{2}$/.test(reprogFecha)) return;
    setBusy(true);
    setError('');
    try {
      const { slots, detail } = await getSlotsReprogramacionTurno(turnoActivo.id, reprogFecha);
      setReprogSlots(slots);
      if (!slots.length) {
        setError(detail || 'No hay horarios libres compatibles con tu estudio ese día.');
      }
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudieron cargar horarios.'));
      setReprogSlots([]);
    } finally {
      setBusy(false);
    }
  };

  const reprogramar = async (slot: SlotMedico) => {
    if (!turnoActivo) return;
    setBusy(true);
    setError('');
    setOk('');
    try {
      const inicio = new Date(slot.inicio);
      const fin = new Date(slot.fin || inicio.getTime() + (slot.duracion_min || 20) * 60_000);
      await apiService.reprogramarTurno(turnoActivo.id, {
        fecha_hora_inicio: formatLocalDateTimeSeconds(inicio),
        fecha_hora_fin: formatLocalDateTimeSeconds(fin),
        motivo: 'Reprogramado por el paciente (pedido de estudio)',
        recurso_id: slot.recurso_id || undefined,
      });
      setOk('Turno reprogramado.');
      setShowReprog(false);
      setReprogSlots([]);
      setReload((r) => r + 1);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo reprogramar.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Box sx={{ p: 2 }} data-demo="page-portal-turnos">
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Mis turnos
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {ok && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setOk('')}>
          {ok}
        </Alert>
      )}
      {loading && <CircularProgress size={24} />}
      <Typography variant="subtitle1" sx={{ mt: 1 }}>
        Mis pedidos de estudio
      </Typography>
      {pedidosLoading && <CircularProgress size={20} sx={{ mb: 1 }} />}
      {pedidosError && (
        <Alert severity="error" sx={{ mb: 1 }} onClose={() => setPedidosError('')}>
          {pedidosError}
        </Alert>
      )}
      {!pedidosLoading && !pedidosError && pedidos.length === 0 && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          No tenés pedidos de estudio enviados.
        </Typography>
      )}
      {!pedidosLoading && pedidos.length > 0 && (
        <List dense sx={{ mb: 2 }}>
          {pedidos.map((p) => (
            <ListItem
              key={p.id}
              secondaryAction={<Chip size="small" label={p.estado} />}
              disablePadding={Boolean(p.turno)}
            >
              {p.turno ? (
                <ListItemButton
                  onClick={() => {
                    setOk(`Turno vinculado #${p.turno}`);
                    setReload((r) => r + 1);
                  }}
                >
                  <ListItemText
                    primary={`Pedido #${p.id} · ${formatFechaHoraDisplay(p.created_at)}`}
                    secondary={
                      p.estado === 'AGENDADO'
                        ? `Agendado · turno #${p.turno}`
                        : p.notas || 'Pendiente de tipificación por secretaría'
                    }
                  />
                </ListItemButton>
              ) : (
                <ListItemText
                  primary={`Pedido #${p.id} · ${formatFechaHoraDisplay(p.created_at)}`}
                  secondary={p.notas || 'Pendiente de tipificación por secretaría'}
                />
              )}
            </ListItem>
          ))}
        </List>
      )}
      {!loading && !turnoActivo && (
        <ReservaTurnoPaciente
          turnos={turnos}
          onReserved={() => setReload((r) => r + 1)}
        />
      )}
      {!loading && turnoActivo && (
        <Box sx={{ mb: 2, p: 2, bgcolor: 'background.paper', borderRadius: 1, boxShadow: 1 }}>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Tu turno
          </Typography>
          <Typography>
            {formatFechaHoraDisplay(turnoActivo.fecha_hora_inicio)}
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 1 }}>
            {(turnoActivo.medico
              ? `${turnoActivo.medico.apellido}, ${turnoActivo.medico.nombre}`
              : turnoActivo.motivo_reserva) || 'Turno'}{' '}
            · {turnoActivo.estado}
            {turnoActivo.viene_de_pedido_estudio ? ' · Estudio (pedido)' : ''}
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 1 }}>
            {turnoActivo.estado === 'RESERVADO' && (
              <Button variant="contained" size="small" disabled={busy} onClick={() => void confirmar()}>
                Confirmar turno
              </Button>
            )}
            {puedeReprogramarPedido && (
              <Button
                variant="outlined"
                size="small"
                disabled={busy}
                onClick={() => {
                  setShowReprog((v) => !v);
                  setReprogSlots([]);
                  setError('');
                }}
              >
                {showReprog ? 'Cerrar reprogramación' : 'Pedir otro horario'}
              </Button>
            )}
          </Stack>
          {showReprog && puedeReprogramarPedido && (
            <Stack spacing={1.5} sx={{ mt: 1, maxWidth: 420 }}>
              <TextField
                type="date"
                label="Fecha"
                value={reprogFecha}
                onChange={(e) => {
                  setReprogFecha(e.target.value);
                  setReprogSlots([]);
                }}
                InputLabelProps={{ shrink: true }}
                fullWidth
                disabled={busy}
              />
              <Button variant="outlined" disabled={busy || !reprogFecha} onClick={() => void cargarSlots()}>
                Ver horarios
              </Button>
              <TextField
                select
                label="Horario libre"
                value=""
                onChange={(e) => {
                  const s = reprogSlots.find((x) => x.inicio === e.target.value);
                  if (s) void reprogramar(s);
                }}
                fullWidth
                disabled={busy || reprogSlots.length === 0}
                helperText={
                  reprogFecha && reprogSlots.length === 0
                    ? 'Sin slots o todavía no consultaste.'
                    : 'Al elegir un horario se reprograma de inmediato.'
                }
              >
                {reprogSlots.map((s) => (
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
          )}
          {!puedeReprogramarPedido && (
            <Typography variant="body2" color="text.secondary">
              Ya tenés un turno reservado. No podés sacar otro desde aquí. Si necesitás
              cancelarlo, pedile a secretaría.
            </Typography>
          )}
        </Box>
      )}
      <Typography variant="subtitle1" sx={{ mt: 2 }}>
        Próximos
      </Typography>
      <List dense>
        {proximos.length === 0 && (
          <ListItem>
            <ListItemText primary="Sin turnos próximos" />
          </ListItem>
        )}
        {proximos.map((t) => (
          <ListItem key={t.id} secondaryAction={<Chip size="small" label={t.estado} />}>
            <ListItemText
              primary={formatFechaHoraDisplay(t.fecha_hora_inicio)}
              secondary={(t.medico ? `${t.medico.apellido}, ${t.medico.nombre}` : t.motivo_reserva) || 'Turno'}
            />
          </ListItem>
        ))}
      </List>
      <Typography variant="subtitle1" sx={{ mt: 2 }}>
        Historial
      </Typography>
      <List dense>
        {historial.slice(0, 20).map((t) => (
          <ListItem key={t.id} secondaryAction={<Chip size="small" label={t.estado} />}>
            <ListItemText
              primary={formatFechaHoraDisplay(t.fecha_hora_inicio)}
              secondary={(t.medico ? `${t.medico.apellido}, ${t.medico.nombre}` : t.motivo_reserva) || 'Turno'}
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

export default PortalTurnos;
