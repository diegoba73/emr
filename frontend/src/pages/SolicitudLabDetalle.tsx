import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import OrdenLimsResumenPanel from '../components/lims/OrdenLimsResumenPanel';
import { useData } from '../contexts/DataContext';
import { downloadInformeLimsPdf, getSolicitudExamen } from '../services/limsApi';
import type { SolicitudExamenLims } from '../types/lims';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../utils/apiError';
import { canAccessAnalisisClinicoLab, canDownloadInformeClinicoPdf } from '../utils/limsAccess';
import { formatLimsPdfDownloadError } from '../utils/limsDownload';
import {
  estadoOrdenColor,
  labelEstadoOrdenLims,
  ordenEsFinalizada,
} from '../utils/limsEstadosOrden';

const SolicitudLabDetalle: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [orden, setOrden] = useState<SolicitudExamenLims | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const allowed = canAccessAnalisisClinicoLab(currentUser);
  const canPdf = canDownloadInformeClinicoPdf(currentUser);

  const load = useCallback(async () => {
    if (!allowed || !id) {
      setLoading(false);
      return;
    }
    setLoadError(false);
    setLoading(true);
    try {
      const oid = Number(id);
      if (Number.isNaN(oid)) {
        setOrden(null);
        setLoadError(true);
        return;
      }
      const data = await getSolicitudExamen(oid);
      setOrden(data);
    } catch (e) {
      setOrden(null);
      setLoadError(true);
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrden));
    } finally {
      setLoading(false);
    }
  }, [allowed, id]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDownloadPdf = async () => {
    if (!orden) return;
    setDownloadingPdf(true);
    try {
      await downloadInformeLimsPdf(orden.id);
      toast.success('Informe PDF descargado');
    } catch (e) {
      toast.error(formatLimsPdfDownloadError(e));
    } finally {
      setDownloadingPdf(false);
    }
  };

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">No tiene acceso a este análisis.</Alert>
      </Box>
    );
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!orden) {
    return (
      <Box sx={{ p: 3 }}>
        <Button size="small" onClick={() => navigate('/solicitudes')} sx={{ mb: 2 }}>
          ← Volver al listado
        </Button>
        <Alert severity={loadError ? 'error' : 'info'}>
          {loadError ? 'No se pudo cargar la orden.' : 'Orden no encontrada.'}
        </Alert>
      </Box>
    );
  }

  const resultados = orden.resultados ?? [];
  const puedePdf =
    canPdf &&
    (orden.estado === 'INFORMADO_PARCIAL' || ordenEsFinalizada(orden.estado));

  return (
    <Box sx={{ p: 3 }}>
      <Button size="small" onClick={() => navigate('/solicitudes')} sx={{ mb: 2 }}>
        ← Volver al listado
      </Button>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2, mb: 2 }}>
        <Typography variant="h5">
          Orden {orden.numero || `#${orden.id}`}
        </Typography>
        <Chip label={labelEstadoOrdenLims(orden.estado)} color={estadoOrdenColor(orden.estado)} />
        {puedePdf && (
          <Button variant="outlined" disabled={downloadingPdf} onClick={handleDownloadPdf}>
            {downloadingPdf ? 'Descargando…' : 'Descargar informe PDF'}
          </Button>
        )}
      </Box>

      <Box sx={{ mb: 2 }}>
        <OrdenLimsResumenPanel orden={orden} />
      </Box>

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Resultados
        </Typography>
        {resultados.length === 0 ? (
          <Typography color="text.secondary">Resultados pendientes.</Typography>
        ) : (
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Examen</TableCell>
                <TableCell>Resultado</TableCell>
                <TableCell>Referencia</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {resultados.map((res) => (
                <TableRow key={res.id}>
                  <TableCell>{res.tipo_examen_nombre || '—'}</TableCell>
                  <TableCell>
                    {res.valor_obtenido || '—'}
                    {res.unidad ? ` ${res.unidad}` : ''}
                    {res.es_patologico ? (
                      <Chip label="Patológico" size="small" color="warning" sx={{ ml: 1 }} />
                    ) : null}
                  </TableCell>
                  <TableCell>{res.rango_referencia_snapshot || res.tipo_examen_rango_referencia || '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </Paper>
    </Box>
  );
};

export default SolicitudLabDetalle;
