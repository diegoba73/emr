import React, { useEffect, useState } from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';
import { useData } from '../../contexts/DataContext';
import { apiService } from '../../services/api';
import { useNavigate } from 'react-router-dom';
import Timeline, { TimelineItem } from '../../components/patient360/Timeline';
import type { PacienteTimelineEvent } from '../../types';
import { mapTimelineEvent } from './portalTimelineUtils';

const PortalHistoria: React.FC = () => {
  const { currentUser } = useData();
  const navigate = useNavigate();
  const [items, setItems] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(true);
  const pacienteId = currentUser?.paciente?.id;

  useEffect(() => {
    if (!pacienteId) {
      setLoading(false);
      return;
    }
    apiService
      .getPacienteTimeline(pacienteId)
      .then((events: PacienteTimelineEvent[]) => {
        setItems(
          events
            .map((ev) => mapTimelineEvent(ev, navigate))
            .filter((x): x is TimelineItem => Boolean(x)),
        );
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [pacienteId, navigate]);

  return (
    <Box sx={{ p: 2 }} data-demo="page-portal-historia">
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Mi historia clínica
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Línea de tiempo de solo lectura.
      </Typography>
      {loading ? <CircularProgress size={24} /> : <Timeline items={items} />}
    </Box>
  );
};

export default PortalHistoria;
