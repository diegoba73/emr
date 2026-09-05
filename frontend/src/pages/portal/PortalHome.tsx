import React, { useEffect, useState } from 'react';
import { Box, Card, CardActionArea, CardContent, CircularProgress, Stack, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useData } from '../../contexts/DataContext';
import { apiService } from '../../services/api';
import type { PortalResumen } from '../../types/bi';

const PortalHome: React.FC = () => {
  const { currentUser } = useData();
  const navigate = useNavigate();
  const [resumen, setResumen] = useState<PortalResumen | null>(null);
  const [loading, setLoading] = useState(true);
  const pacienteId = currentUser?.paciente?.id || (currentUser as { paciente_id?: number })?.paciente_id;

  useEffect(() => {
    if (!pacienteId) {
      setLoading(false);
      return;
    }
    apiService
      .getPortalResumen(pacienteId)
      .then(setResumen)
      .catch(() => setResumen(null))
      .finally(() => setLoading(false));
  }, [pacienteId]);

  const tiles = [
    { title: 'Mis turnos', path: '/portal/turnos', value: resumen?.proximos_turnos },
    { title: 'Resultados de laboratorio', path: '/portal/resultados', value: resumen?.resultados_laboratorio_listos },
    { title: 'Documentos', path: '/portal/documentos', value: resumen?.documentos_total },
    { title: 'Mi historia', path: '/portal/historia', value: undefined },
  ];

  return (
    <Box sx={{ p: 2 }} data-demo="page-portal">
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Portal del paciente
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Consultá turnos, resultados liberados y documentos.
      </Typography>
      {loading && <CircularProgress size={24} />}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' },
          gap: 2,
        }}
      >
        {tiles.map((t) => (
          <Card key={t.path} variant="outlined">
            <CardActionArea onClick={() => navigate(t.path)}>
              <CardContent>
                <Typography variant="h6">{t.title}</Typography>
                {t.value != null && (
                  <Typography variant="h4" color="primary">
                    {t.value}
                  </Typography>
                )}
              </CardContent>
            </CardActionArea>
          </Card>
        ))}
      </Box>
      <Stack sx={{ mt: 3 }}>
        <Typography variant="caption" color="text.secondary">
          Usuario: {currentUser?.username}
        </Typography>
      </Stack>
    </Box>
  );
};

export default PortalHome;
