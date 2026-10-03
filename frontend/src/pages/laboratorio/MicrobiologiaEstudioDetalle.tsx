import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Box, Button, Chip, CircularProgress, Paper, Tab, Tabs, Typography } from '@mui/material';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { EstudioMicrobiologia } from '../../types/lims';
import { readNavBackState } from '../../utils/navBack';
import {
  cancelarEstudioMicrobiologia,
  getEstudioMicrobiologia,
  iniciarEstudioMicrobiologia,
  listAisladosMicrobiologicos,
  listAntibiogramas,
  listAntibioticos,
  listIdentificacionesMicroorganismo,
  listInformesMicrobiologia,
  listLecturasCultivo,
  listMediosCultivo,
  listMicroorganismos,
  listResultadosAntibiotico,
  listSiembrasMicrobiologia,
  marcarEstudioMicrobiologiaInformado,
  downloadInformeMicroPdf,
} from '../../services/limsApi';
import { printTalonEstudioMicro, patchEstadoObraSocialEstudio } from '../../services/limsMicroApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import {
  canAccessMicrobiologiaLectura,
  canDownloadInformeMicroPdf,
  canEnviarInformeMicro,
  canMarcarMicroEstudioInformado,
  canOperateInformeMicro,
  canOperateMicrobiologia,
  canOperateMicroEstudioTecnico,
  canValidarInformeMicro,
  isMicroEstudioCerrado,
  isSecretariaEntregaLab,
} from '../../utils/limsAccess';
import EstudioMicroPedidoRecepcionPanel from '../../components/lims/micro/EstudioMicroPedidoRecepcionPanel';
import ImprimirPedidoMicroDialog from '../../components/lims/micro/ImprimirPedidoMicroDialog';
import EstudioMicroResumenTab from '../../components/lims/micro/EstudioMicroResumenTab';
import SiembrasLecturasPanel from '../../components/lims/micro/SiembrasLecturasPanel';
import AisladosIdentificacionPanel from '../../components/lims/micro/AisladosIdentificacionPanel';
import AntibiogramaPanel from '../../components/lims/micro/AntibiogramaPanel';
import InformesMicrobiologiaPanel from '../../components/lims/micro/InformesMicrobiologiaPanel';
import EstudioMicroExamenOrinaTab from '../../components/lims/micro/EstudioMicroExamenOrinaTab';
import EnviarInformeMicroDialog from '../../components/lims/EnviarInformeMicroDialog';
import { MotivoDialog, useMotivoDialog } from '../../components/lims/micro/MotivoDialog';
import EstadoObraSocialDialog from '../../components/lims/EstadoObraSocialDialog';
import { ordenPuedeValidarObraSocial } from '../../utils/limsObraSocial';
import { formatLimsPdfDownloadError } from '../../utils/limsDownload';
import { labelEstadoOrdenLims } from '../../utils/limsEstadosOrden';
import { estudioAdmiteExamenOrina } from '../../utils/limsExamenOrinaMicro';
import { todasLecturasSinDesarrollo } from '../../utils/limsMicroCultivoNegativo';

type DetalleTab = 'resumen' | 'orina' | 'siembras' | 'aislados' | 'antibiograma' | 'informes';

const MicrobiologiaEstudioDetalle: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { currentUser } = useData();
  const [tab, setTab] = useState<DetalleTab>('resumen');
  const [estudio, setEstudio] = useState<EstudioMicrobiologia | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloadingTalon, setDownloadingTalon] = useState(false);
  const [confirmingRecepcion, setConfirmingRecepcion] = useState(false);
  const [openImprimirEtiqueta, setOpenImprimirEtiqueta] = useState(false);
  const [openObraSocial, setOpenObraSocial] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [openEnviarInforme, setOpenEnviarInforme] = useState(false);
  const [bundle, setBundle] = useState({
    siembras: [] as Awaited<ReturnType<typeof listSiembrasMicrobiologia>>,
    lecturas: [] as Awaited<ReturnType<typeof listLecturasCultivo>>,
    aislados: [] as Awaited<ReturnType<typeof listAisladosMicrobiologicos>>,
    identificaciones: [] as Awaited<ReturnType<typeof listIdentificacionesMicroorganismo>>,
    antibiogramas: [] as Awaited<ReturnType<typeof listAntibiogramas>>,
    resultados: [] as Awaited<ReturnType<typeof listResultadosAntibiotico>>,
    informes: [] as Awaited<ReturnType<typeof listInformesMicrobiologia>>,
    medios: [] as Awaited<ReturnType<typeof listMediosCultivo>>,
    microorganismos: [] as Awaited<ReturnType<typeof listMicroorganismos>>,
    antibioticos: [] as Awaited<ReturnType<typeof listAntibioticos>>,
  });

  const allowed = canAccessMicrobiologiaLectura(currentUser);
  const modoEntrega = isSecretariaEntregaLab(currentUser);
  const canOp = canOperateMicrobiologia(currentUser);
  const canVal = canValidarInformeMicro(currentUser);
  const canOpInforme = canOperateInformeMicro(currentUser);
  const estudioCerrado = estudio ? isMicroEstudioCerrado(estudio.estado) : false;
  const canOpEstudio = canOperateMicroEstudioTecnico(currentUser, estudio?.estado);
  const canMarcarInformado = canMarcarMicroEstudioInformado(currentUser, estudio?.estado);
  const modoPedidoPendiente = estudio?.estado === 'PENDIENTE';
  const admiteOrina = estudio ? estudioAdmiteExamenOrina(estudio) : false;
  const cultivoSinDesarrollo = todasLecturasSinDesarrollo(bundle.lecturas);

  const estudioId = Number(id);
  const { openMotivoDialog, dialogProps } = useMotivoDialog();

  useEffect(() => {
    if (!admiteOrina && tab === 'orina') {
      setTab('resumen');
    }
  }, [admiteOrina, tab]);

  const loadAll = useCallback(async () => {
    if (!allowed || Number.isNaN(estudioId)) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const filterParams = { estudio_id: estudioId };
      const est = await getEstudioMicrobiologia(estudioId);
      setEstudio(est);

      // Secretaría: solo identificación + informe. PENDIENTE: vista de recepción.
      if (modoEntrega || est.estado === 'PENDIENTE') {
        return;
      }

      const settled = await Promise.allSettled([
        listSiembrasMicrobiologia(filterParams),
        listLecturasCultivo(filterParams),
        listAisladosMicrobiologicos(filterParams),
        listIdentificacionesMicroorganismo(filterParams),
        listAntibiogramas(filterParams),
        listResultadosAntibiotico(filterParams),
        listInformesMicrobiologia(filterParams),
        listMediosCultivo(),
        listMicroorganismos(),
        listAntibioticos(),
      ]);
      const val = <T,>(i: number, fallback: T): T =>
        settled[i].status === 'fulfilled' ? (settled[i] as PromiseFulfilledResult<T>).value : fallback;

      setBundle({
        siembras: val(0, []),
        lecturas: val(1, []),
        aislados: val(2, []),
        identificaciones: val(3, []),
        antibiogramas: val(4, []),
        resultados: val(5, []),
        informes: val(6, []),
        medios: val(7, []),
        microorganismos: val(8, []),
        antibioticos: val(9, []),
      });
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarEstudio));
      setEstudio(null);
    } finally {
      setLoading(false);
    }
  }, [allowed, estudioId, modoEntrega]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const runEstudio = async (fn: () => Promise<EstudioMicrobiologia>, okMsg = 'Estudio actualizado') => {
    try {
      const est = await fn();
      setEstudio(est);
      toast.success(okMsg);
      await loadAll();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarEstudioMicro));
    }
  };

  const onCancelar = () => {
    openMotivoDialog({
      title: 'Cancelar pedido microbiológico',
      label: 'Motivo de cancelación',
      confirmLabel: 'Cancelar pedido',
      onConfirm: async (motivo) => {
        try {
          const est = await cancelarEstudioMicrobiologia(estudioId, motivo);
          setEstudio(est);
          toast.success('Pedido cancelado');
          await loadAll();
        } catch (e) {
          const msg = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCancelarEstudioMicro);
          toast.error(msg);
          throw new Error(msg);
        }
      },
    });
  };

  const onReimprimir = () => {
    setOpenImprimirEtiqueta(true);
  };

  const onImprimirTalon = async () => {
    setDownloadingTalon(true);
    try {
      await printTalonEstudioMicro(estudioId);
      toast.success('Diálogo de impresión abierto — elegí una impresora común.');
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
    } finally {
      setDownloadingTalon(false);
    }
  };

  const onConfirmarRecepcion = async () => {
    setConfirmingRecepcion(true);
    try {
      const est = await iniciarEstudioMicrobiologia(estudioId);
      setEstudio(est);
      toast.success('Recepción confirmada. Ya podés trabajar el estudio.');
      await loadAll();
      setTab('resumen');
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarEstudioMicro));
    } finally {
      setConfirmingRecepcion(false);
    }
  };

  const handleVolver = () => {
    const { from } = readNavBackState(location.state);
    if (from) {
      navigate(from);
      return;
    }
    if (canOperateMicrobiologia(currentUser)) {
      if (modoPedidoPendiente) {
        const tabPend =
          estudio?.etiquetas_impresas_at || estudio?.codigo_barra
            ? 'esperando_recepcion'
            : 'sin_etiquetas';
        navigate(`/laboratorio/pendientes?tab=${tabPend}`);
        return;
      }
      navigate('/laboratorio/microbiologia/estudios');
      return;
    }
    navigate('/solicitudes');
  };

  const handleDownloadPdf = async () => {
    if (!estudio) return;
    setDownloadingPdf(true);
    try {
      await downloadInformeMicroPdf(estudio.id);
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
        <Typography>Sin acceso.</Typography>
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

  if (!estudio) {
    return (
      <Box sx={{ p: 3 }}>
        <Button size="small" onClick={handleVolver} sx={{ mb: 1 }}>
          ← Volver
        </Button>
        <Alert severity="error">No se pudo cargar el estudio de microbiología.</Alert>
      </Box>
    );
  }

  if (modoEntrega) {
    const puedePdf = canDownloadInformeMicroPdf(currentUser, estudio.estado);
    const puedeEnviar = canEnviarInformeMicro(currentUser, estudio.estado);
    return (
      <Box sx={{ p: 3 }}>
        <Button size="small" onClick={handleVolver} sx={{ mb: 2 }}>
          ← Volver
        </Button>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 2, mb: 2 }}>
          <Typography variant="h5">
            Estudio {estudio.numero || `#${estudio.id}`}
          </Typography>
          <Chip label={labelEstadoOrdenLims(estudio.estado)} />
          {puedeEnviar && (
            <Button variant="contained" onClick={() => setOpenEnviarInforme(true)}>
              Enviar informe
            </Button>
          )}
          {puedePdf && (
            <Button variant="outlined" disabled={downloadingPdf} onClick={() => void handleDownloadPdf()}>
              {downloadingPdf ? 'Descargando…' : 'Descargar informe PDF'}
            </Button>
          )}
        </Box>
        <Paper sx={{ p: 2 }}>
          <Typography variant="overline" color="text.secondary" display="block">
            Paciente
          </Typography>
          <Typography fontWeight={600}>
            {estudio.paciente_nombre || `ID ${estudio.paciente}`}
          </Typography>
          {estudio.paciente_dni && (
            <Typography variant="body2" color="text.secondary">
              DNI {estudio.paciente_dni}
            </Typography>
          )}
          {estudio.medico_display ? (
            <Typography variant="body2" sx={{ mt: 1 }}>
              Médico: {estudio.medico_display}
            </Typography>
          ) : null}
          {!puedePdf && !puedeEnviar ? (
            <Alert severity="info" sx={{ mt: 2 }}>
              El informe estará disponible para enviar o descargar cuando esté validado.
            </Alert>
          ) : (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Informe validado. Podés enviarlo o descargar el PDF.
            </Typography>
          )}
        </Paper>
        <EnviarInformeMicroDialog
          open={openEnviarInforme}
          estudio={estudio}
          onClose={() => setOpenEnviarInforme(false)}
          onSuccess={() => {
            setOpenEnviarInforme(false);
            void loadAll();
          }}
        />
      </Box>
    );
  }

  if (modoPedidoPendiente) {
    return (
      <Box sx={{ p: 2 }}>
        <Button size="small" onClick={handleVolver} sx={{ mb: 1 }}>
          ← Volver a pendientes
        </Button>
        <EstudioMicroPedidoRecepcionPanel
          estudio={estudio}
          canOperate={canOp}
          downloadingTalon={downloadingTalon}
          confirmingRecepcion={confirmingRecepcion}
          onReimprimirEtiquetas={onReimprimir}
          onImprimirTalon={() => void onImprimirTalon()}
          onConfirmarRecepcion={() => void onConfirmarRecepcion()}
          onCancelar={onCancelar}
          onObraSocial={canOp ? () => setOpenObraSocial(true) : undefined}
        />
        <ImprimirPedidoMicroDialog
          open={openImprimirEtiqueta}
          estudioId={estudioId}
          estudioNumero={estudio.numero}
          reimpresion={Boolean(estudio.etiquetas_impresas_at || estudio.codigo_barra)}
          onClose={() => setOpenImprimirEtiqueta(false)}
          onEtiquetasOk={() => {
            void loadAll();
          }}
        />
        <MotivoDialog {...dialogProps} />
        {estudio && (
          <EstadoObraSocialDialog
            open={openObraSocial}
            numero={estudio.numero}
            value={estudio.estado_obra_social}
            onClose={() => setOpenObraSocial(false)}
            onSave={async (estado) => {
              const fresh = await patchEstadoObraSocialEstudio(estudio.id, estado);
              setEstudio(fresh);
            }}
          />
        )}
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Button size="small" onClick={handleVolver} sx={{ mb: 1 }}>
        ← Volver
      </Button>
      <Tabs
        value={tab}
        onChange={(_, v: DetalleTab) => setTab(v)}
        sx={{ mb: 2 }}
        variant="scrollable"
        allowScrollButtonsMobile
      >
        <Tab value="resumen" label="Resumen" />
        {admiteOrina && <Tab value="orina" label="Tira y sedimento" />}
        <Tab value="siembras" label="Siembras y lecturas" />
        <Tab value="aislados" label="Aislados" />
        <Tab value="antibiograma" label="Antibiograma" />
        <Tab value="informes" label="Informes" />
      </Tabs>

      {estudioCerrado && (
        <Alert severity="info" sx={{ mb: 2 }}>
          El estudio microbiológico está cerrado. Las operaciones técnicas están bloqueadas.
        </Alert>
      )}
      {!ordenPuedeValidarObraSocial(estudio) &&
        estudio.estado !== 'VALIDADO' &&
        estudio.estado !== 'INFORMADO' && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            En órdenes ambulatorias la obra social tiene que estar <strong>Autorizada</strong> para
            validar y emitir el informe. Usá <strong>Obra social</strong> y elegí Autorizado.
          </Alert>
        )}

      {cultivoSinDesarrollo && !estudioCerrado && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Cultivo <strong>sin desarrollo</strong>: no hace falta aislamiento ni antibiograma.
          {canOpInforme
            ? ' En Informes podés crear el informe final («No se obtuvo desarrollo bacteriano»).'
            : ' El bioquímico puede emitir el informe final en la pestaña Informes.'}
        </Alert>
      )}

      {tab === 'resumen' && (
        <EstudioMicroResumenTab
          estudio={estudio}
          canOperateTecnico={canOpEstudio}
          canMarcarInformado={canMarcarInformado}
          onIniciar={() =>
            void runEstudio(() => iniciarEstudioMicrobiologia(estudioId), 'Estudio iniciado')
          }
          onCancelar={onCancelar}
          onMarcarInformado={() =>
            void runEstudio(() => marcarEstudioMicrobiologiaInformado(estudioId))
          }
          canEditarObraSocial={canOp}
          onObraSocial={() => setOpenObraSocial(true)}
          onReimprimirEtiquetas={canOp ? onReimprimir : undefined}
          onImprimirTalon={canOp ? () => void onImprimirTalon() : undefined}
          downloadingTalon={downloadingTalon}
        />
      )}
      {tab === 'orina' && admiteOrina && (
        <EstudioMicroExamenOrinaTab
          estudio={estudio}
          canOperate={canOpEstudio}
          onSaved={(fresh) => setEstudio(fresh)}
        />
      )}
      {tab === 'siembras' && (
        <SiembrasLecturasPanel
          estudioId={estudioId}
          siembras={bundle.siembras}
          lecturas={bundle.lecturas}
          medios={bundle.medios}
          canOperate={canOpEstudio}
          onRefresh={loadAll}
          onIrAInformes={() => setTab('informes')}
        />
      )}
      {tab === 'aislados' && (
        <AisladosIdentificacionPanel
          estudioId={estudioId}
          lecturas={bundle.lecturas}
          aislados={bundle.aislados}
          identificaciones={bundle.identificaciones}
          microorganismos={bundle.microorganismos}
          canOperate={canOpEstudio}
          onRefresh={loadAll}
        />
      )}
      {tab === 'antibiograma' && (
        <AntibiogramaPanel
          aislados={bundle.aislados}
          antibiogramas={bundle.antibiogramas}
          resultados={bundle.resultados}
          antibioticos={bundle.antibioticos}
          microorganismos={bundle.microorganismos}
          canOperate={canOpEstudio}
          onRefresh={loadAll}
          cultivoSinDesarrollo={cultivoSinDesarrollo}
        />
      )}
      {tab === 'informes' && (
        <InformesMicrobiologiaPanel
          estudio={estudio}
          informes={bundle.informes}
          lecturas={bundle.lecturas}
          aislados={bundle.aislados}
          canOperate={canOpInforme && !estudioCerrado}
          canValidar={canVal}
          canDownloadPdf={canDownloadInformeMicroPdf(currentUser, estudio.estado)}
          canEnviar={canEnviarInformeMicro(currentUser, estudio.estado)}
          onRefresh={loadAll}
        />
      )}
      <ImprimirPedidoMicroDialog
        open={openImprimirEtiqueta}
        estudioId={estudioId}
        estudioNumero={estudio.numero}
        reimpresion={Boolean(estudio.etiquetas_impresas_at || estudio.codigo_barra)}
        onClose={() => setOpenImprimirEtiqueta(false)}
        onEtiquetasOk={() => {
          void loadAll();
        }}
      />
      <MotivoDialog {...dialogProps} />
      <EstadoObraSocialDialog
        open={openObraSocial}
        numero={estudio.numero}
        value={estudio.estado_obra_social}
        onClose={() => setOpenObraSocial(false)}
        onSave={async (estado) => {
          const fresh = await patchEstadoObraSocialEstudio(estudio.id, estado);
          setEstudio(fresh);
        }}
      />
    </Box>
  );
};

export default MicrobiologiaEstudioDetalle;
