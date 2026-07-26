import React, { useEffect, useState } from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';
import { useData } from '../../contexts/DataContext';
import { apiService } from '../../services/api';
import Timeline, { TimelineItem, TimelineItemType } from '../../components/patient360/Timeline';
import type { PacienteTimelineEvent } from '../../types';

const PortalHistoria: React.FC = () => {
  const { currentUser } = useData();
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
            .map((ev) => {
              const date = ev.date ? new Date(ev.date) : new Date(0);
              if (Number.isNaN(date.getTime())) return null;
              return {
                id: ev.id,
                type: (ev.type || 'otro') as TimelineItemType,
                title: ev.title,
                subtitle: ev.subtitle || undefined,
                date,
                critical: Boolean(ev.critical),
                nested: Boolean(ev.nested),
                episodeGroupId: ev.episode_group_id || undefined,
                episodeGroupTitle: ev.episode_group_title || undefined,
              } as TimelineItem;
            })
            .filter((x): x is TimelineItem => Boolean(x)),
        );
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [pacienteId]);

  return (
    <Box sx={{ p: 2 }}>
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
