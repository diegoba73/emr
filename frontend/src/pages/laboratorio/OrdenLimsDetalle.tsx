import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Paper,
  Tab,
  Tabs,
  TextField,
  Typography,
  CircularProgress,
} from '@mui/material';
import { Navigate, useLocation, useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { MuestraTransaccional, SolicitudExamenLims } from '../../types/lims';
import { resolveNavBack } from '../../utils/navBack';
import {
  downloadInformeLimsPdf,
  getIqcPrecheck,
  getSolicitudExamen,
  listMuestrasPorSolicitud,
  postMarcarDerivacion,
  postValidarSolicitud,
  type IqcPrecheckResult,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import {
  canAccessAnalisisClinicoLab,
  canAccessLimsModule,
  canAccessLimsOrdenDetalle,
  canDownloadInformeLimsPdf,
  canEnviarInformeLims,
  canOperateLims,
  canValidarOrdenLims,
} from '../../utils/limsAccess';
import { normalizeRol } from '../../utils/permissions';
import { formatLimsPdfDownloadError } from '../../utils/limsDownload';
import {
  estadoOrdenColor,
  labelEstadoOrdenLims,
  ordenListaParaValidar,
  ordenPuedeAgregarExamenes,
  ordenPuedeCargarResultados,
  ordenPuedeEnviarInforme,
} from '../../utils/limsEstadosOrden';
import { countResultadosConValor, ordenResultadosCompletos } from '../../utils/limsOrdenResultados';
import CargaResultadosLims from '../../components/lims/CargaResultadosLims';
import MuestrasOrdenPanel from '../../components/lims/MuestrasOrdenPanel';
import OrdenLimsResumenPanel from '../../components/lims/OrdenLimsResumenPanel';
import TomarMuestraOrdenDialog from '../../components/lims/TomarMuestraOrdenDialog';
import EnviarInformeOrdenDialog from '../../components/lims/EnviarInformeOrdenDialog';
import NuevaOrdenLimsDialog from '../../components/lims/NuevaOrdenLimsDialog';

const OrdenLimsDetalle: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
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
  const [openAgregarExamenes, setOpenAgregarExamenes] = useState(false);
  const [muestrasReloadToken, setMuestrasReloadToken] = useState(0);
  const [iqcPrecheck, setIqcPrecheck] = useState<IqcPrecheckResult | null>(null);
  const [qcOverrideOpen, setQcOverrideOpen] = useState(false);
  const [qcOverrideMotivo, setQcOverrideMotivo] = useState('');
  const [pendingCriticos, setPendingCriticos] = useState(false);

  const allowed = canAccessLimsModule(currentUser);
  const canVerOrden = orden ? canAccessLimsOrdenDetalle(currentUser, orden.estado) : true;
  const canOp = canOperateLims(currentUser);
  const canValidar = canValidarOrdenLims(currentUser);
  const canQcOverride =
    Boolean(currentUser?.is_superuser) || normalizeRol(currentUser) === 'admin';
  const canEnviar = canEnviarInformeLims(currentUser, orden?.estado);
  const canPdf = canDownloadInformeLimsPdf(currentUser, orden?.estado);
  const back = resolveNavBack(location.state, {
    path: '/laboratorio/ordenes',
    label: '← Volver al listado',
  });
  const goBack = () => navigate(back.path);

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
      try {
        setIqcPrecheck(await getIqcPrecheck(oid));
      } catch {
        setIqcPrecheck(null);
      }
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

  const runValidar = async (opts: {
    confirmar_criticos?: boolean;
    confirmar_qc_override?: boolean;
    motivo_qc_override?: string;
  }) => {
    if (!orden) return;
    setValidando(true);
    try {
      const updated = await postValidarSolicitud(orden.id, opts);
      setOrden(updated);
      toast.success('Orden validada y liberada');
      setQcOverrideOpen(false);
      setQcOverrideMotivo('');
      try {
        const fresh = await getSolicitudExamen(updated.id);
        setOrden(fresh);
        setIqcPrecheck(await getIqcPrecheck(fresh.id));
      } catch {
        /* keep updated */
      }
    } catch (e) {
      const msg = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarResultado);
      if (canQcOverride && /control de calidad no vigente/i.test(msg)) {
        setPendingCriticos(Boolean(opts.confirmar_criticos));
        setQcOverrideOpen(true);
        toast.error(msg);
      } else {
        toast.error(msg);
      }
    } finally {
      setValidando(false);
    }
  };

  const handleValidar = async () => {
    if (!orden) return;
    const resultados = orden.resultados || [];
    const tieneAlertas = resultados.some((r) => r.es_patologico || r.es_critico);
    if (tieneAlertas) {
      const ok = window.confirm(
        'Hay resultados fuera de rango o críticos. ¿Confirmás la validación y liberación del informe?'
      );
      if (!ok) return;
    }
    await runValidar({ confirmar_criticos: tieneAlertas });
  };

  if (!allowed && canAccessAnalisisClinicoLab(currentUser) && id) {
    return <Navigate to={`/solicitudes/${id}`} replace state={location.state} />;
  }

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
        <Button size="small" onClick={goBack} sx={{ mb: 1 }}>
          {back.label}
        </Button>
        <Typography>No tiene permisos para ver esta orden en su estado actual.</Typography>
      </Box>
    );
  }

  if (!loading && !orden && allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Button size="small" onClick={goBack} sx={{ mb: 1 }}>
          {back.label}
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
      <Button size="small" onClick={goBack} sx={{ mb: 1 }}>
        {back.label}
      </Button>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2, mb: 2 }}>
        <Typography variant="h5">Orden {orden.numero || orden.id}</Typography>
        <Chip label={labelEstadoOrdenLims(e)} color={estadoOrdenColor(e)} />
        <Typography variant="body1" fontWeight={600}>
          {orden.paciente_nombre || `Paciente #${orden.paciente}`}
          {orden.paciente_dni ? (
            <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
              DNI {orden.paciente_dni}
            </Typography>
          ) : null}
        </Typography>
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

      {iqcPrecheck?.aplicable && !iqcPrecheck.ok && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          IQC no vigente
          {iqcPrecheck.equipos?.length
            ? ` (${iqcPrecheck.equipos.map((e) => e.codigo).join(', ')})`
            : iqcPrecheck.equipo
              ? ` (${iqcPrecheck.equipo.codigo})`
              : ''}
          : {iqcPrecheck.problemas.join('; ')}. Registrá corridas ACEPTADAS en el equipo
          correspondiente (Control de calidad) antes de cargar o liberar.
        </Alert>
      )}

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
          {canOp && ordenPuedeAgregarExamenes(orden) && (
            <Button variant="contained" color="secondary" onClick={() => setOpenAgregarExamenes(true)}>
              Agregar exámenes
            </Button>
          )}
          {enProceso && canOp && !resultadosCompletos && (
            <Button variant="contained" onClick={() => setTab(2)}>
              Cargar resultados
            </Button>
          )}
          {listaParaValidar && canOp && (
            <Button variant="outlined" onClick={() => setTab(2)}>
              Corregir resultados
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
              label="Listo para validar — pendiente del bioquímico"
              color="warning"
              variant="outlined"
            />
          )}
          {puedeEnviarInforme && finalizada && canEnviar && (
            <Button variant="contained" color="primary" onClick={() => setOpenEnviarInforme(true)}>
              Enviar informe
            </Button>
          )}
          {finalizada && canPdf && (
            <Button variant="outlined" disabled={downloadingPdf} onClick={handleDownloadPdf}>
              {downloadingPdf ? 'Descargando…' : 'Descargar informe PDF'}
            </Button>
          )}
        </Box>
        {canOp && ordenPuedeAgregarExamenes(orden) && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            <strong>Agregar exámenes</strong>: sin etiquetas, libre; con etiquetas impresas, solo si
            caben en los tubos ya generados (sin nueva extracción).
          </Typography>
        )}
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
        {orden.derivaciones_resumen && orden.derivaciones_resumen.length > 0 && (
          <Alert severity="info" sx={{ mt: 1.5 }}>
            <Typography variant="body2" fontWeight={600} gutterBottom>
              Exámenes derivados a laboratorio externo
            </Typography>
            <Box component="ul" sx={{ m: 0, pl: 2 }}>
              {orden.derivaciones_resumen.map((d) => (
                <li key={d.resultado_id}>
                  {d.tipo_examen_codigo} → {d.laboratorio_codigo || '—'} ({d.estado_derivacion})
                  {canOp && d.estado_derivacion === 'PENDIENTE_ENVIO' && (
                    <Button
                      size="small"
                      sx={{ ml: 1 }}
                      onClick={() => {
                        void (async () => {
                          try {
                            await postMarcarDerivacion(orden.id, {
                              resultado_id: d.resultado_id,
                              estado_derivacion: 'ENVIADO',
                            });
                            const fresh = await getSolicitudExamen(orden.id);
                            setOrden(fresh);
                            toast.success(`Enviado a ${d.laboratorio_codigo}`);
                          } catch (err) {
                            toast.error(
                              getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.limsGuardarResultado)
                            );
                          }
                        })();
                      }}
                    >
                      Marcar enviado
                    </Button>
                  )}
                </li>
              ))}
            </Box>
            <Typography variant="caption" display="block" sx={{ mt: 1 }}>
              Cuando el resultado llega por correo, cargalo manualmente en la pestaña Resultados.
            </Typography>
          </Alert>
        )}
        {enProceso && !resultadosCompletos && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            {informadoParcial ? (
              <>
                Orden <strong>informada parcialmente</strong> ({progreso.conValor} de {progreso.total}{' '}
                resultados). Seguí completando en Resultados; al completar todos pasa a{' '}
                <strong>Listo para validar</strong>. El PDF y el envío solo están disponibles tras la
                validación del bioquímico.
              </>
            ) : (
              <>
                Podés guardar resultados de a poco en Resultados. Si querés marcar avance interno,
                usá <strong>Guardar e informar parcialmente</strong>. Al completar todos, la orden
                pasa a <strong>Listo para validar</strong>. Descarga y envío del informe recién
                después de <strong>Validar y liberar</strong>.
              </>
            )}
          </Typography>
        )}
        {listaParaValidar && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Resultados completos — estado <strong>Listo para validar</strong>. Un bioquímico debe{' '}
            <strong>Validar y liberar</strong> para finalizar. Hasta entonces no se puede descargar ni
            enviar el informe.
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
      <NuevaOrdenLimsDialog
        open={openAgregarExamenes}
        onClose={() => setOpenAgregarExamenes(false)}
        agregarAOrdenId={orden.id}
        agregarAOrdenNumero={orden.numero}
        onCreated={async () => {
          try {
            const fresh = await getSolicitudExamen(orden.id);
            setOrden(fresh);
          } catch {
            /* ignore */
          }
        }}
      />
      <EnviarInformeOrdenDialog
        open={openEnviarInforme}
        orden={orden}
        onClose={() => setOpenEnviarInforme(false)}
        onSuccess={(o) => setOrden(o)}
      />

      <Dialog open={qcOverrideOpen} onClose={() => !validando && setQcOverrideOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>Forzar liberación sin IQC vigente</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Solo administrador. Indicá el motivo (queda auditado).
          </Typography>
          <TextField
            autoFocus
            fullWidth
            multiline
            minRows={2}
            label="Motivo del override"
            value={qcOverrideMotivo}
            onChange={(e) => setQcOverrideMotivo(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setQcOverrideOpen(false)} disabled={validando}>
            Cancelar
          </Button>
          <Button
            variant="contained"
            color="warning"
            disabled={validando || !qcOverrideMotivo.trim()}
            onClick={() =>
              void runValidar({
                confirmar_criticos: pendingCriticos,
                confirmar_qc_override: true,
                motivo_qc_override: qcOverrideMotivo.trim(),
              })
            }
          >
            {validando ? 'Validando…' : 'Forzar y liberar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default OrdenLimsDetalle;
