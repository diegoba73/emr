import ReservaTurnoPaciente from '../../components/ReservaTurnoPaciente';
import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import { getMisTurnos } from '../../services/agendaMedica';
import { apiService } from '../../services/api';
import type { Turno } from '../../types';
import { formatFechaHoraDisplay } from '../../utils/dateFieldFormat';
import { getSafeClinicalActionMessage } from '../../utils/apiError';
import { getTurnoAgendaKind } from '../../utils/turnoKind';
import { useLiveRefresh } from '../../hooks/useLiveRefresh';
import { getTurnosRevision } from '../../services/apiService';

function esTurnoEstudioPaciente(turno: Turno): boolean {
  if (turno.viene_de_pedido_estudio) return true;
  if (turno.estudio_complementario?.id) return true;
  const kind = getTurnoAgendaKind(turno);
  return kind === 'estudio' || kind === 'procedimiento' || kind === 'cirugia';
}

const PortalTurnos: React.FC = () => {
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');

  const loadTurnosPortal = useCallback((opts?: { silent?: boolean }) => {
    if (!opts?.silent) setLoading(true);
    return getMisTurnos()
      .then(setTurnos)
      .catch(() => setTurnos([]))
      .finally(() => {
        if (!opts?.silent) setLoading(false);
      });
  }, []);

  useEffect(() => {
    void loadTurnosPortal();
  }, [reload, loadTurnosPortal]);

  useLiveRefresh(() => loadTurnosPortal({ silent: true }), {
    enabled: true,
    getRevision: getTurnosRevision,
  });

  const now = Date.now();
  const activos = turnos
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
  const historial = turnos
    .filter((t) => t.fecha_hora_inicio && new Date(t.fecha_hora_inicio).getTime() < now)
    .sort(
      (a, b) =>
        new Date(b.fecha_hora_inicio).getTime() - new Date(a.fecha_hora_inicio).getTime(),
    );

  const activoEsEstudio = Boolean(turnoActivo && esTurnoEstudioPaciente(turnoActivo));
  const pideAceptacionReprogramacion = Boolean(
    turnoActivo?.requiere_aceptacion_paciente && turnoActivo?.estado === 'RESERVADO',
  );
  const puedeConfirmarTurno = Boolean(
    turnoActivo &&
      turnoActivo.estado === 'RESERVADO' &&
      (!activoEsEstudio || pideAceptacionReprogramacion),
  );

  const confirmar = async () => {
    if (!turnoActivo || !puedeConfirmarTurno) return;
    setBusy(true);
    setError('');
    setOk('');
    try {
      await apiService.confirmarTurno(turnoActivo.id);
      setOk(
        pideAceptacionReprogramacion
          ? 'Aceptaste el nuevo horario.'
          : 'Turno confirmado.'
      );
      setReload((r) => r + 1);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo confirmar el turno.'));
    } finally {
      setBusy(false);
    }
  };

  const rechazarReprogramacion = async () => {
    if (!turnoActivo || !pideAceptacionReprogramacion) return;
    setBusy(true);
    setError('');
    setOk('');
    try {
      await apiService.cancelarTurno(
        turnoActivo.id,
        'Paciente rechazó el horario reprogramado desde el portal',
      );
      setOk('Rechazaste el nuevo horario. El turno quedó cancelado.');
      setReload((r) => r + 1);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo rechazar el horario.'));
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
            {activoEsEstudio ? ' · Estudio' : ''}
          </Typography>
          {puedeConfirmarTurno && (
            <Button variant="contained" size="small" disabled={busy} onClick={() => void confirmar()}>
              {pideAceptacionReprogramacion ? 'Aceptar nuevo horario' : 'Confirmar turno'}
            </Button>
          )}
          {pideAceptacionReprogramacion && (
            <Button
              variant="outlined"
              color="error"
              size="small"
              disabled={busy}
              sx={{ ml: 1 }}
              onClick={() => void rechazarReprogramacion()}
            >
              Rechazar nuevo horario
            </Button>
          )}
          {pideAceptacionReprogramacion ? (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Secretaría reprogramó tu turno
              {activoEsEstudio ? ' de estudio' : ''}. Aceptá el nuevo horario o rechazalo. Si
              rechazás, el turno se cancela y el horario queda libre.
            </Typography>
          ) : activoEsEstudio ? (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Este turno de estudio lo gestiona secretaría. Si necesitás cambiarlo o cancelarlo,
              contactalos (presencial o por teléfono).
            </Typography>
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
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
              secondary={
                [
                  t.medico ? `${t.medico.apellido}, ${t.medico.nombre}` : t.motivo_reserva,
                  esTurnoEstudioPaciente(t) ? 'Estudio' : null,
                ]
                  .filter(Boolean)
                  .join(' · ') || 'Turno'
              }
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
