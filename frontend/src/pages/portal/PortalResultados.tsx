import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import { downloadInformeLimsPdf, listSolicitudesExamen } from '../../services/limsApi';
import type { SolicitudExamenLims } from '../../types/lims';

const LISTOS = new Set(['FINALIZADO']);

const PortalResultados: React.FC = () => {
  const { currentUser } = useData();
  const [ordenes, setOrdenes] = useState<SolicitudExamenLims[]>([]);
  const [loading, setLoading] = useState(true);
  const pacienteId = currentUser?.paciente?.id;

  useEffect(() => {
    if (!pacienteId) {
      setLoading(false);
      return;
    }
    listSolicitudesExamen({ paciente: pacienteId })
      .then((all) => setOrdenes(all.filter((o) => LISTOS.has(o.estado))))
      .catch(() => setOrdenes([]))
      .finally(() => setLoading(false));
  }, [pacienteId]);

  const onPdf = async (id: number) => {
    try {
      await downloadInformeLimsPdf(id);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'No se pudo descargar el PDF');
    }
  };

  return (
    <Box sx={{ p: 2 }} data-demo="page-portal-resultados">
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Resultados de laboratorio
      </Typography>
      {loading && <CircularProgress size={24} />}
      <List>
        {ordenes.length === 0 && !loading && (
          <ListItem>
            <ListItemText primary="No hay resultados liberados" />
          </ListItem>
        )}
        {ordenes.map((o) => (
          <ListItem
            key={o.id}
            secondaryAction={
              <Button size="small" variant="outlined" onClick={() => onPdf(o.id)}>
                PDF
              </Button>
            }
          >
            <ListItemText
              primary={o.numero || `Orden #${o.id}`}
              secondary={
                o.fecha_solicitud
                  ? new Date(o.fecha_solicitud).toLocaleString('es-AR')
                  : undefined
              }
            />
            <Chip size="small" label={o.estado} sx={{ mr: 8 }} />
          </ListItem>
        ))}
      </List>
    </Box>
  );
};

export default PortalResultados;
