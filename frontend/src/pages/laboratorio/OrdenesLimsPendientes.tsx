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
import { useNavigate, useSearchParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { SolicitudExamenLims } from '../../types/lims';
import { listSolicitudesExamen } from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canAccessLimsPendientes, canOperateLims } from '../../utils/limsAccess';
import OrdenesLimsTabla from '../../components/lims/OrdenesLimsTabla';
import NuevaOrdenLimsDialog from '../../components/lims/NuevaOrdenLimsDialog';
import TomarMuestraOrdenDialog from '../../components/lims/TomarMuestraOrdenDialog';

const OrdenesLimsPendientes: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { currentUser } = useData();
  const [rows, setRows] = useState<SolicitudExamenLims[]>([]);
  const [loading, setLoading] = useState(true);
  const [busqueda, setBusqueda] = useState('');
  const [nuevaOrdenOpen, setNuevaOrdenOpen] = useState(false);
  const [ordenEtiquetas, setOrdenEtiquetas] = useState<SolicitudExamenLims | null>(null);

  const allowed = canAccessLimsPendientes(currentUser);
  const puedeCrear = canOperateLims(currentUser);
  const puedeImprimir = canOperateLims(currentUser);

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

  useEffect(() => {
    if (!puedeCrear) return;
    if (searchParams.get('action') !== 'nueva') return;
    setNuevaOrdenOpen(true);
    const next = new URLSearchParams(searchParams);
    next.delete('action');
    setSearchParams(next, { replace: true });
  }, [puedeCrear, searchParams, setSearchParams]);

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
            Órdenes esperando impresión de etiquetas y recepción. Imprimí las etiquetas, pegá en los
            tubos y confirmá el ingreso escaneando en <strong>Recepción</strong>.
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
            emptyMessage="No hay órdenes pendientes de etiquetas / recepción."
            columnaFecha="solicitud"
            accionLabel={puedeImprimir ? 'Imprimir etiquetas' : 'Ver'}
            onVer={(id) => navigate(`/laboratorio/ordenes/${id}`)}
            onAccion={
              puedeImprimir
                ? (orden) => setOrdenEtiquetas(orden)
                : undefined
            }
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

      {ordenEtiquetas && (
        <TomarMuestraOrdenDialog
          open={!!ordenEtiquetas}
          orden={ordenEtiquetas}
          muestrasExistentes={[]}
          onClose={() => setOrdenEtiquetas(null)}
          onSuccess={() => {
            setOrdenEtiquetas(null);
            load();
          }}
        />
      )}
    </Box>
  );
};

export default OrdenesLimsPendientes;
