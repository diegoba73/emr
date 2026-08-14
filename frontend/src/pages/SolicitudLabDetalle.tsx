import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Typography,
} from '@mui/material';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import OrdenLimsResumenPanel from '../components/lims/OrdenLimsResumenPanel';
import ResultadosOrdenLista from '../components/lims/ResultadosOrdenLista';
import EnviarInformeOrdenDialog from '../components/lims/EnviarInformeOrdenDialog';
import { useData } from '../contexts/DataContext';
import { downloadInformeLimsPdf, getSolicitudExamen } from '../services/limsApi';
import type { SolicitudExamenLims } from '../types/lims';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../utils/apiError';
import {
  canAccessAnalisisClinicoLab,
  canDownloadInformeClinicoPdf,
  canEnviarInformeLims,
  canSeeResultadosClinicos,
} from '../utils/limsAccess';
import { formatLimsPdfDownloadError } from '../utils/limsDownload';
import {
  estadoOrdenColor,
  labelEstadoOrdenLims,
  ordenPuedeEnviarInforme,
} from '../utils/limsEstadosOrden';
import { resolveNavBack } from '../utils/navBack';

const SolicitudLabDetalle: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { currentUser } = useData();
  const [orden, setOrden] = useState<SolicitudExamenLims | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [openEnviarInforme, setOpenEnviarInforme] = useState(false);

  const allowed = canAccessAnalisisClinicoLab(currentUser);
  const back = resolveNavBack(location.state, {
    path: '/solicitudes',
    label: '← Volver al listado',
  });

  const goBack = () => navigate(back.path);

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
        <Button size="small" onClick={goBack} sx={{ mb: 2 }}>
          {back.label}
        </Button>
        <Alert severity={loadError ? 'error' : 'info'}>
          {loadError ? 'No se pudo cargar la orden.' : 'Orden no encontrada.'}
        </Alert>
      </Box>
    );
  }

  const resultados = orden.resultados ?? [];
  const puedeVerResultados = canSeeResultadosClinicos(currentUser, orden.estado);
  const puedePdf = canDownloadInformeClinicoPdf(currentUser, orden.estado);
  const puedeEnviar =
    ordenPuedeEnviarInforme(orden.estado) && canEnviarInformeLims(currentUser, orden.estado);

  return (
    <Box sx={{ p: 3 }}>
      <Button size="small" onClick={goBack} sx={{ mb: 2 }}>
        {back.label}
      </Button>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2, mb: 2 }}>
        <Typography variant="h5">
          Orden {orden.numero || `#${orden.id}`}
        </Typography>
        <Chip label={labelEstadoOrdenLims(orden.estado)} color={estadoOrdenColor(orden.estado)} />
        {puedeEnviar && (
          <Button variant="contained" onClick={() => setOpenEnviarInforme(true)}>
            Enviar informe
          </Button>
        )}
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
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Agrupados por perfil (hemograma, orina, ionograma, EAB, etc.)
        </Typography>
        {!puedeVerResultados ? (
          <Alert severity="info">
            No tiene permiso para ver los resultados de esta orden.
          </Alert>
        ) : resultados.length === 0 ? (
          <Typography color="text.secondary">Resultados pendientes.</Typography>
        ) : (
          <ResultadosOrdenLista
            resultados={resultados}
            orden={orden}
            observaciones={orden.observaciones}
            modo="clinico"
          />
        )}
      </Paper>

      <EnviarInformeOrdenDialog
        open={openEnviarInforme}
        orden={orden}
        onClose={() => setOpenEnviarInforme(false)}
        onSuccess={(updated) => {
          setOrden(updated);
          setOpenEnviarInforme(false);
        }}
      />
    </Box>
  );
};

export default SolicitudLabDetalle;
