import React, { useEffect, useMemo, useState } from 'react';
import { Box, Chip, CircularProgress, List, ListItem, ListItemText, Typography } from '@mui/material';
import { useData } from '../../contexts/DataContext';
import { apiClient } from '../../services/apiClient';

interface EstudioRow {
  id: number;
  estado: string;
  modalidad?: string;
  tipo_estudio_nombre?: string;
  fecha_solicitud?: string;
}

const PortalDocumentos: React.FC = () => {
  const { currentUser, archivosMedicos, loadArchivosMedicos } = useData();
  const [estudios, setEstudios] = useState<EstudioRow[]>([]);
  const [loading, setLoading] = useState(true);
  const pacienteId = currentUser?.paciente?.id;

  useEffect(() => {
    loadArchivosMedicos();
  }, [loadArchivosMedicos]);

  useEffect(() => {
    apiClient
      .get('/estudios-complementarios/', { params: { page_size: 100 } })
      .then((res) => {
        const rows = res.data?.results || res.data || [];
        setEstudios(
          (rows as EstudioRow[]).filter((e) => e.estado === 'ENTREGADO'),
        );
      })
      .catch(() => setEstudios([]))
      .finally(() => setLoading(false));
  }, []);

  const archivos = useMemo(
    () => archivosMedicos.filter((a) => a.paciente_id === pacienteId),
    [archivosMedicos, pacienteId],
  );

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Mis documentos
      </Typography>
      {loading && <CircularProgress size={24} />}
      <Typography variant="subtitle1" sx={{ mt: 2 }}>
        Archivos médicos
      </Typography>
      <List dense>
        {archivos.length === 0 && (
          <ListItem>
            <ListItemText primary="Sin archivos" />
          </ListItem>
        )}
        {archivos.map((a) => (
          <ListItem key={a.id}>
            <ListItemText primary={a.titulo} secondary={a.tipo_archivo} />
          </ListItem>
        ))}
      </List>
      <Typography variant="subtitle1" sx={{ mt: 2 }}>
        Estudios complementarios entregados
      </Typography>
      <List dense>
        {estudios.map((e) => (
          <ListItem key={e.id} secondaryAction={<Chip size="small" label={e.estado} />}>
            <ListItemText
              primary={e.tipo_estudio_nombre || e.modalidad || `Estudio #${e.id}`}
              secondary={
                e.fecha_solicitud
                  ? new Date(e.fecha_solicitud).toLocaleDateString('es-AR')
                  : undefined
              }
            />
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

export default PortalDocumentos;
