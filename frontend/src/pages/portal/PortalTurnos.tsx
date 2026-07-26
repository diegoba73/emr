import React, { useEffect, useMemo, useState } from 'react';
import {
  Box,
  Chip,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import { useData } from '../../contexts/DataContext';
import { apiService } from '../../services/api';
import type { Turno } from '../../types';

const PortalTurnos: React.FC = () => {
  const { currentUser } = useData();
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [loading, setLoading] = useState(true);
  const pacienteId = currentUser?.paciente?.id;

  useEffect(() => {
    apiService
      .getTurnos()
      .then((res) => setTurnos(res.results || []))
      .catch(() => setTurnos([]))
      .finally(() => setLoading(false));
  }, []);

  const mine = useMemo(
    () =>
      turnos.filter(
        (t) => t.paciente_id === pacienteId || t.paciente?.id === pacienteId,
      ),
    [turnos, pacienteId],
  );

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
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Mis turnos
      </Typography>
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
              secondary={t.motivo_reserva || t.recurso?.nombre || 'Turno'}
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
              secondary={t.motivo_reserva || t.recurso?.nombre || 'Turno'}
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

export default PortalTurnos;
