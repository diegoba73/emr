import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  Paper,
  Stack,
  TextField,
  Typography,
  CircularProgress,
} from '@mui/material';
import { Add } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { SolicitudExamenLims } from '../../types/lims';
import { listSolicitudesExamen } from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canAccessLimsPendientes, canOperateLims } from '../../utils/limsAccess';
import OrdenesLimsTabla from '../../components/lims/OrdenesLimsTabla';
import NuevaOrdenLimsDialog from '../../components/lims/NuevaOrdenLimsDialog';

const OrdenesLimsPendientes: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<SolicitudExamenLims[]>([]);
  const [loading, setLoading] = useState(true);
  const [busqueda, setBusqueda] = useState('');
  const [nuevaOrdenOpen, setNuevaOrdenOpen] = useState(false);

  const allowed = canAccessLimsPendientes(currentUser);
  const puedeCrear = canOperateLims(currentUser);
  const puedeTomar = canOperateLims(currentUser);

  const load = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    try {
      const data = await listSolicitudesExamen({ estado: 'PENDIENTE' });
      setRows(data);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
    } finally {
      setLoading(false);
    }
  }, [allowed]);

  useEffect(() => {
    load();
  }, [load]);

  const filtradas = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const n = (r.numero || '').toLowerCase();
      const pn = (r.paciente_nombre || '').toLowerCase();
      const pd = (r.paciente_dni || '').toLowerCase();
      return n.includes(q) || pn.includes(q) || pd.includes(q);
    });
  }, [rows, busqueda]);

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>No tiene permisos para acceder al módulo LIMS.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h5" gutterBottom>
            Pendientes
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Órdenes esperando extracción de muestra. Al tomar la muestra, la orden pasa a la bandeja diaria de{' '}
            <strong>Órdenes LIMS</strong> según el día de la toma.
          </Typography>
        </Box>
        {puedeCrear && (
          <Button variant="contained" startIcon={<Add />} onClick={() => setNuevaOrdenOpen(true)}>
            Nueva orden
          </Button>
        )}
      </Stack>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
          <TextField
            size="small"
            label="Buscar (nº, paciente, DNI)"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            sx={{ minWidth: 220 }}
          />
          <Button variant="outlined" onClick={load} disabled={loading}>
            Actualizar
          </Button>
          <Chip size="small" label={`${filtradas.length} pendiente(s)`} color="warning" variant="outlined" />
        </Box>
      </Paper>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Paper>
          <OrdenesLimsTabla
            rows={filtradas}
            emptyMessage="No hay órdenes pendientes de toma de muestra."
            columnaFecha="solicitud"
            accionLabel={puedeTomar ? 'Tomar muestra' : 'Ver'}
            onVer={(id) => navigate(`/laboratorio/ordenes/${id}`)}
          />
        </Paper>
      )}

      <NuevaOrdenLimsDialog
        open={nuevaOrdenOpen}
        onClose={() => setNuevaOrdenOpen(false)}
        onCreated={(id) => {
          load();
          navigate(`/laboratorio/ordenes/${id}`);
        }}
      />
    </Box>
  );
};

export default OrdenesLimsPendientes;
