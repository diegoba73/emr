import React, { useCallback, useEffect, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  Paper,
  Tab,
  Tabs,
  Typography,
  CircularProgress,
  Divider,
} from '@mui/material';
import { useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { MuestraTransaccional, SolicitudExamenLims } from '../../types/lims';
import {
  downloadInformeLimsPdf,
  getSolicitudExamen,
  listMuestrasPorSolicitud,
  postCancelarOrden,
  postMarcarEntregado,
  postTomarMuestraOrden,
  postValidarOrden,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import {
  canAccessLimsModule,
  canDownloadInformeLimsPdf,
  canOperateLims,
  canValidarOrdenLims,
} from '../../utils/limsAccess';
import { formatLimsPdfDownloadError } from '../../utils/limsDownload';
import MuestrasOrdenPanel from '../../components/lims/MuestrasOrdenPanel';
import CargaResultadosLims from '../../components/lims/CargaResultadosLims';
import ResultadosOrdenLista from '../../components/lims/ResultadosOrdenLista';

const OrdenLimsDetalle: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [tab, setTab] = useState(0);
  const [orden, setOrden] = useState<SolicitudExamenLims | null>(null);
  const [muestras, setMuestras] = useState<MuestraTransaccional[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  const allowed = canAccessLimsModule(currentUser);
  const canOp = canOperateLims(currentUser);
  const canVal = canValidarOrdenLims(currentUser);
  const canPdf = canDownloadInformeLimsPdf(currentUser);

  const bump = () => setReloadToken((x) => x + 1);

  const loadAll = useCallback(async () => {
    if (!allowed) {
      setLoading(false);
      return;
    }
    if (!id) {
      setLoading(false);
      setOrden(null);
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
      const o = await getSolicitudExamen(oid);
      const m = await listMuestrasPorSolicitud(oid, o.numero);
      setOrden(o);
      setMuestras(m);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrden));
      setOrden(null);
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [id, allowed]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const refreshMuestras = async (oid: number, numero?: string | null) => {
    const m = await listMuestrasPorSolicitud(oid, numero ?? undefined);
    setMuestras(m);
    bump();
  };

  const runOrden = async (fn: () => Promise<SolicitudExamenLims>) => {
    try {
      const o = await fn();
      setOrden(o);
      await refreshMuestras(o.id, o.numero);
      toast.success('Orden actualizada');
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarOrden));
    }
  };

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
        <Typography>Sin acceso al módulo LIMS.</Typography>
      </Box>
    );
  }

  if (!loading && !orden && allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Button size="small" onClick={() => navigate('/laboratorio/ordenes')} sx={{ mb: 1 }}>
          ← Volver al listado
        </Button>
        <Typography>{loadError ? 'No se pudo cargar la orden.' : 'Orden no encontrada.'}</Typography>
      </Box>
    );
  }

  if (loading || !orden) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const e = orden.estado;

  return (
    <Box sx={{ p: 2 }}>
      <Button size="small" onClick={() => navigate('/laboratorio/ordenes')} sx={{ mb: 1 }}>
        ← Volver al listado
      </Button>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2, mb: 2 }}>
        <Typography variant="h5">Orden {orden.numero || orden.id}</Typography>
        <Chip label={orden.estado} color="primary" />
        <Typography variant="body2" color="text.secondary">
          Origen: {orden.origen_solicitud}
        </Typography>
      </Box>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Acciones de orden
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {canOp && e === 'PENDIENTE' && (
            <Button variant="outlined" onClick={() => runOrden(() => postTomarMuestraOrden(orden.id))}>
              Tomar muestra (orden)
            </Button>
          )}
          {canOp && ['PENDIENTE', 'TOMA_MUESTRA', 'EN_PROCESO'].includes(e) && (
            <Button color="error" variant="outlined" onClick={() => runOrden(() => postCancelarOrden(orden.id))}>
              Cancelar orden
            </Button>
          )}
          {canVal && e === 'EN_PROCESO' && (
            <Button color="success" variant="contained" onClick={() => runOrden(() => postValidarOrden(orden.id))}>
              Validar orden
            </Button>
          )}
          {canOp && e === 'VALIDADO' && (
            <Button variant="contained" onClick={() => runOrden(() => postMarcarEntregado(orden.id))}>
              Marcar entregado
            </Button>
          )}
          {canPdf && (
            <Button
              variant="outlined"
              disabled={downloadingPdf}
              onClick={handleDownloadPdf}
            >
              {downloadingPdf ? 'Descargando…' : 'Descargar informe PDF'}
            </Button>
          )}
        </Box>
        {canPdf && !['VALIDADO', 'ENTREGADO'].includes(e) && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Informe PDF básico (vista derivada; puede incluir resultados en curso).
          </Typography>
        )}
        {!canOp && (
          <Typography variant="caption" color="text.secondary">
            Solo lectura: las acciones de orden requieren rol laboratorio o administrador.
          </Typography>
        )}
      </Paper>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Resumen" />
        <Tab label="Muestras" />
        <Tab label="Resultados" />
      </Tabs>

      {tab === 0 && (
        <Paper sx={{ p: 2 }}>
          <Typography>
            <strong>Paciente:</strong> {orden.paciente_nombre || orden.paciente}{' '}
            {orden.paciente_dni ? `(DNI ${orden.paciente_dni})` : ''}
          </Typography>
          <Typography sx={{ mt: 1 }}>
            <strong>Médico:</strong> {orden.medico_display || orden.medico_interno_nombre || '—'}
          </Typography>
          <Typography sx={{ mt: 1 }}>
            <strong>Tipos:</strong> {(orden.tipos_examen_nombres || []).join(', ') || '—'}
          </Typography>
          <Typography sx={{ mt: 1 }}>
            <strong>Paneles:</strong> {(orden.paneles_nombres || []).join(', ') || '—'}
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Typography variant="body2" color="text.secondary">
            {orden.observaciones || 'Sin observaciones.'}
          </Typography>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle1" gutterBottom>
            Resultados
          </Typography>
          <ResultadosOrdenLista resultados={orden.resultados || []} muestras={muestras} />
        </Paper>
      )}

      {tab === 1 && (
        <MuestrasOrdenPanel
          solicitudId={orden.id}
          solicitudNumero={orden.numero}
          canOperate={canOp}
          reloadToken={reloadToken}
        />
      )}

      {tab === 2 && (
        <Box>
          <CargaResultadosLims
            orden={orden}
            muestras={muestras}
            canOperate={canOp}
            onGuardado={async (o) => {
              setOrden(o);
              await refreshMuestras(o.id, o.numero);
              try {
                const fresh = await getSolicitudExamen(o.id);
                setOrden(fresh);
              } catch {
                /* respuesta de cargar-resultados ya trae snapshots */
              }
            }}
          />
        </Box>
      )}
    </Box>
  );
};

export default OrdenLimsDetalle;
