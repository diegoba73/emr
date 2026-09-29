import ReservaTurnoPaciente from '../../components/ReservaTurnoPaciente';
import React, { useEffect, useState } from 'react';
import {
  Box,
  Chip,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import { getMisTurnos } from '../../services/agendaMedica';
import type { Turno } from '../../types';

const PortalTurnos: React.FC = () => {
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [loading, setLoading] = useState(true);
  const [reload, setReload] = useState(0);


  useEffect(() => {
    getMisTurnos().then(setTurnos)
      .catch(() => setTurnos([]))
      .finally(() => setLoading(false));
  }, [reload]);

  // La API devuelve únicamente los turnos vinculados al usuario autenticado.
  const mine = turnos;

  const now = Date.now();
  const proximos = mine
    .filter((t) => t.fecha_hora_inicio && new Date(t.fecha_hora_inicio).getTime() >= now)
    .sort(
      (a, b) =>
        new Date(a.fecha_hora_inicio).getTime() - new Date(b.fecha_hora_inicio).getTime(),
    );
  const historial = mine
    .filter((t) => t.fecha_hora_inicio && new Date(t.fecha_hora_inicio).getTime() < now)
    .sort(
      (a, b) =>
        new Date(b.fecha_hora_inicio).getTime() - new Date(a.fecha_hora_inicio).getTime(),
    );

  return (
    <Box sx={{ p: 2 }} data-demo="page-portal-turnos">
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Mis turnos
      </Typography>
      <ReservaTurnoPaciente turnos={turnos} onReserved={() => setReload(r => r+1)} />
      {loading && <CircularProgress size={24} />}
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
              primary={new Date(t.fecha_hora_inicio).toLocaleString('es-AR')}
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
              primary={new Date(t.fecha_hora_inicio).toLocaleString('es-AR')}
              secondary={(t.medico ? `${t.medico.apellido}, ${t.medico.nombre}` : t.motivo_reserva) || 'Turno'}
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

export default PortalTurnos;
