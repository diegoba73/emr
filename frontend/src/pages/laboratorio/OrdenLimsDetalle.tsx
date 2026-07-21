import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Tab,
  Tabs,
  Typography,
  CircularProgress,
} from '@mui/material';
import { useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { MuestraTransaccional, SolicitudExamenLims } from '../../types/lims';
import {
  downloadInformeLimsPdf,
  getSolicitudExamen,
  listMuestrasPorSolicitud,
  postValidarSolicitud,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import {
  canAccessLimsModule,
  canAccessLimsOrdenDetalle,
  canDownloadInformeLimsPdf,
  canEnviarInformeLims,
  canOperateLims,
  canValidarOrdenLims,
} from '../../utils/limsAccess';
import { formatLimsPdfDownloadError } from '../../utils/limsDownload';
import {
  estadoOrdenColor,
  labelEstadoOrdenLims,
  ordenListaParaValidar,
  ordenPuedeCargarResultados,
  ordenPuedeEnviarInforme,
} from '../../utils/limsEstadosOrden';
import { countResultadosConValor, ordenResultadosCompletos } from '../../utils/limsOrdenResultados';
import CargaResultadosLims from '../../components/lims/CargaResultadosLims';
import MuestrasOrdenPanel from '../../components/lims/MuestrasOrdenPanel';
import OrdenLimsResumenPanel from '../../components/lims/OrdenLimsResumenPanel';
import TomarMuestraOrdenDialog from '../../components/lims/TomarMuestraOrdenDialog';
import EnviarInformeOrdenDialog from '../../components/lims/EnviarInformeOrdenDialog';

const OrdenLimsDetalle: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [tab, setTab] = useState(0);
  const [orden, setOrden] = useState<SolicitudExamenLims | null>(null);
  const [muestras, setMuestras] = useState<MuestraTransaccional[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [validando, setValidando] = useState(false);
  const [openTomarMuestra, setOpenTomarMuestra] = useState(false);
  const [openEnviarInforme, setOpenEnviarInforme] = useState(false);
  const [muestrasReloadToken, setMuestrasReloadToken] = useState(0);

  const allowed = canAccessLimsModule(currentUser);
  const canVerOrden = orden ? canAccessLimsOrdenDetalle(currentUser, orden.estado) : true;
  const canOp = canOperateLims(currentUser);
  const canValidar = canValidarOrdenLims(currentUser);
  const canEnviar = canEnviarInformeLims(currentUser);
  const canPdf = canDownloadInformeLimsPdf(currentUser, orden?.estado);

  const refreshMuestras = async (oid: number, numero?: string | null) => {
    const m = await listMuestrasPorSolicitud(oid, numero ?? undefined);
    setMuestras(m);
  };

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

  const handleValidar = async () => {
    if (!orden) return;
    const resultados = orden.resultados || [];
    const tieneAlertas = resultados.some((r) => r.es_patologico || r.es_critico);
    if (tieneAlertas) {
      const ok = window.confirm(
        'Hay resultados patológicos o críticos. ¿Confirmás la validación y liberación del informe?'
      );
      if (!ok) return;
    }
    setValidando(true);
    try {
      const updated = await postValidarSolicitud(orden.id, {
        confirmar_criticos: tieneAlertas,
      });
      setOrden(updated);
      toast.success('Orden validada y liberada');
      try {
        const fresh = await getSolicitudExamen(updated.id);
        setOrden(fresh);
      } catch {
        /* keep updated */
      }
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarResultado));
    } finally {
      setValidando(false);
    }
  };

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>Sin acceso al módulo LIMS.</Typography>
      </Box>
    );
  }

  if (!loading && orden && !canVerOrden) {
    return (
      <Box sx={{ p: 3 }}>
        <Button size="small" onClick={() => navigate('/laboratorio/ordenes')} sx={{ mb: 1 }}>
          ← Volver al listado
        </Button>
        <Typography>No tiene permisos para ver esta orden en su estado actual.</Typography>
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
  const resultadosCompletos = ordenResultadosCompletos(orden);
  const progreso = countResultadosConValor(orden);
  const enProceso = ordenPuedeCargarResultados(e);
  const informadoParcial = e === 'INFORMADO_PARCIAL';
  const finalizada = e === 'FINALIZADO';
  const listaParaValidar = ordenListaParaValidar(e, resultadosCompletos);
  const puedeEnviarInforme = ordenPuedeEnviarInforme(e) && progreso.conValor > 0;
  const informeEnviado = Boolean(orden.fecha_informe_enviado);
  const validadorInfo = (orden.resultados || []).find(
    (r) => r.validado_por_nombre || r.fecha_validacion
  );

  return (
    <Box sx={{ p: 2 }}>
      <Button size="small" onClick={() => navigate(-1)} sx={{ mb: 1 }}>
        ← Volver
      </Button>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2, mb: 2 }}>
        <Typography variant="h5">Orden {orden.numero || orden.id}</Typography>
        <Chip label={labelEstadoOrdenLims(e)} color={estadoOrdenColor(e)} />
        {!resultadosCompletos && progreso.conValor > 0 && (
          <Chip
            size="small"
            label={`${progreso.conValor}/${progreso.total} resultados`}
            variant="outlined"
          />
        )}
        {informeEnviado && (
          <Chip size="small" label="Informe enviado" color="info" variant="outlined" />
        )}
        {finalizada && validadorInfo?.validado_por_nombre && (
          <Chip
            size="small"
            color="success"
            variant="outlined"
            label={`Validado por ${validadorInfo.validado_por_nombre}`}
          />
        )}
        {orden.procedencia_display && (
          <Typography variant="body2" color="text.secondary">
            {orden.procedencia_display}
          </Typography>
        )}
      </Box>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Acciones de orden
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
          {canOp && e === 'PENDIENTE' && (
            <Button variant="outlined" onClick={() => setOpenTomarMuestra(true)}>
              Imprimir etiquetas
            </Button>
          )}
          {(enProceso || informadoParcial) && canOp && !resultadosCompletos && (
            <Button variant="contained" onClick={() => setTab(2)}>
              Cargar resultados
            </Button>
          )}
          {listaParaValidar && canValidar && (
            <Button
              variant="contained"
              color="success"
              disabled={validando}
              onClick={() => void handleValidar()}
            >
              {validando ? 'Validando…' : 'Validar y liberar'}
            </Button>
          )}
          {listaParaValidar && !canValidar && canOp && (
            <Chip
              size="small"
              label="Resultados completos — pendiente de validación del bioquímico"
              color="warning"
              variant="outlined"
            />
          )}
          {puedeEnviarInforme && resultadosCompletos && canEnviar && (
            <Button variant="contained" color="primary" onClick={() => setOpenEnviarInforme(true)}>
              Enviar informe
            </Button>
          )}
          {puedeEnviarInforme && !resultadosCompletos && canEnviar && (
            <Button variant="contained" color="info" onClick={() => setOpenEnviarInforme(true)}>
              Enviar informe parcial
            </Button>
          )}
          {puedeEnviarInforme && canPdf && (
            <Button variant="outlined" disabled={downloadingPdf} onClick={handleDownloadPdf}>
              {downloadingPdf
                ? 'Descargando…'
                : informadoParcial
                  ? 'Descargar informe parcial PDF'
                  : 'Descargar informe PDF'}
            </Button>
          )}
        </Box>
        {canOp && e === 'PENDIENTE' && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Pendiente de recepción. <strong>Imprimir etiquetas</strong> genera los tubos con código de
            barras; confirmá el ingreso escaneando en <strong>Recepción</strong>.
          </Typography>
        )}
        {orden.tubos_pendientes_extraccion && orden.tubos_pendientes_extraccion.length > 0 && (
          <Alert severity="warning" sx={{ mt: 1.5 }}>
            Recepción incompleta. Faltan escanear:{' '}
            {orden.tubos_pendientes_extraccion
              .map(
                (t) =>
                  `${t.tipo_contenedor_codigo || 'Tubo'}${t.codigo_barra ? ` (${t.codigo_barra})` : ''}`
              )
              .join(', ')}
            . Podés cargar resultados de los exámenes cuyos tubos ya estén recibidos.
          </Alert>
        )}
        {(enProceso || informadoParcial) && !resultadosCompletos && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            {informadoParcial ? (
              <>
                Orden <strong>informada parcialmente</strong> ({progreso.conValor} de {progreso.total}{' '}
                resultados). El PDF refleja solo lo cargado. Seguí completando en Resultados; cuando
                estén todos, un bioquímico debe <strong>Validar y liberar</strong>.
              </>
            ) : (
              <>
                Podés guardar resultados de a poco en Resultados. Si el médico solicita anticipar la
                entrega, usá <strong>Guardar e informar parcialmente</strong> y luego{' '}
                <strong>Enviar informe parcial</strong>.
              </>
            )}
          </Typography>
        )}
        {listaParaValidar && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Resultados completos. La orden permanece en borrador hasta que un bioquímico use{' '}
            <strong>Validar y liberar</strong>.
          </Typography>
        )}
        {finalizada && resultadosCompletos && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Resultados validados y bloqueados
            {validadorInfo?.fecha_validacion
              ? ` (${new Date(validadorInfo.fecha_validacion).toLocaleString('es-AR')})`
              : ''}
            . Usá <strong>Enviar informe</strong> para entregar el PDF por email o WhatsApp.
          </Typography>
        )}
        {!canOp && (
          <Typography variant="caption" color="text.secondary">
            Solo lectura: las acciones de orden requieren rol laboratorio, bioquímico o administrador.
          </Typography>
        )}
      </Paper>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Resumen" />
        <Tab label="Muestras" />
        <Tab label="Resultados" />
      </Tabs>

      {tab === 0 && <OrdenLimsResumenPanel orden={orden} />}

      {tab === 1 && (
        <MuestrasOrdenPanel
          solicitudId={orden.id}
          solicitudNumero={orden.numero}
          ordenEstado={orden.estado}
          canOperate={canOp}
          reloadToken={muestrasReloadToken}
        />
      )}

      {tab === 2 && (
        <CargaResultadosLims
          orden={orden}
          muestras={muestras}
          canOperate={canOp}
          permitirEdicion={(enProceso || informadoParcial) && !finalizada}
          onGuardado={async (o) => {
            setOrden(o);
            await refreshMuestras(o.id, o.numero);
            setMuestrasReloadToken((t) => t + 1);
            try {
              const fresh = await getSolicitudExamen(o.id);
              setOrden(fresh);
            } catch {
              /* keep o */
            }
          }}
        />
      )}

      <TomarMuestraOrdenDialog
        open={openTomarMuestra}
        orden={orden}
        muestrasExistentes={muestras}
        onClose={() => setOpenTomarMuestra(false)}
        onSuccess={async (o) => {
          setOrden(o);
          await refreshMuestras(o.id, o.numero);
          setMuestrasReloadToken((t) => t + 1);
          try {
            const fresh = await getSolicitudExamen(o.id);
            setOrden(fresh);
          } catch {
            /* keep o */
          }
        }}
      />
      <EnviarInformeOrdenDialog
        open={openEnviarInforme}
        orden={orden}
        onClose={() => setOpenEnviarInforme(false)}
        onSuccess={(o) => setOrden(o)}
      />
    </Box>
  );
};

export default OrdenLimsDetalle;
