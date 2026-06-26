import React, { useCallback, useEffect, useState } from 'react';
import { Alert, Box, Button, CircularProgress, Tab, Tabs, Typography } from '@mui/material';
import { useNavigate, useParams } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { EstudioMicrobiologia } from '../../types/lims';
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
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import {
  canAccessMicrobiologia,
  canMarcarMicroEstudioInformado,
  canOperateMicroEstudioTecnico,
  canValidarInformeMicro,
  isMicroEstudioCerrado,
} from '../../utils/limsAccess';
import EstudioMicroResumenTab from '../../components/lims/micro/EstudioMicroResumenTab';
import SiembrasLecturasPanel from '../../components/lims/micro/SiembrasLecturasPanel';
import AisladosIdentificacionPanel from '../../components/lims/micro/AisladosIdentificacionPanel';
import AntibiogramaPanel from '../../components/lims/micro/AntibiogramaPanel';
import InformesMicrobiologiaPanel from '../../components/lims/micro/InformesMicrobiologiaPanel';
import { MotivoDialog, useMotivoDialog } from '../../components/lims/micro/MotivoDialog';

const MicrobiologiaEstudioDetalle: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [tab, setTab] = useState(0);
  const [estudio, setEstudio] = useState<EstudioMicrobiologia | null>(null);
  const [loading, setLoading] = useState(true);
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

  const allowed = canAccessMicrobiologia(currentUser);
  const canVal = canValidarInformeMicro(currentUser);
  const estudioCerrado = estudio ? isMicroEstudioCerrado(estudio.estado) : false;
  const canOpEstudio = canOperateMicroEstudioTecnico(currentUser, estudio?.estado);
  const canMarcarInformado = canMarcarMicroEstudioInformado(currentUser, estudio?.estado);

  const estudioId = Number(id);
  const { openMotivoDialog, dialogProps } = useMotivoDialog();

  const loadAll = useCallback(async () => {
    if (!allowed || Number.isNaN(estudioId)) return;
    setLoading(true);
    try {
      const filterParams = { estudio_id: estudioId };
      const [est, siembras, lecturas, aislados, identificaciones, antibiogramas, resultados, informes, medios, microorganismos, antibioticos] =
        await Promise.all([
          getEstudioMicrobiologia(estudioId),
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
      setEstudio(est);
      setBundle({
        siembras,
        lecturas,
        aislados,
        identificaciones,
        antibiogramas,
        resultados,
        informes,
        medios,
        microorganismos,
        antibioticos,
      });
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarEstudio));
      setEstudio(null);
    } finally {
      setLoading(false);
    }
  }, [allowed, estudioId]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const runEstudio = async (fn: () => Promise<EstudioMicrobiologia>) => {
    try {
      const est = await fn();
      setEstudio(est);
      toast.success('Estudio actualizado');
      await loadAll();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarEstudioMicro));
    }
  };

  const onCancelar = () => {
    openMotivoDialog({
      title: 'Cancelar estudio microbiológico',
      label: 'Motivo de cancelación',
      confirmLabel: 'Cancelar estudio',
      onConfirm: async (motivo) => {
        try {
          const est = await cancelarEstudioMicrobiologia(estudioId, motivo);
          setEstudio(est);
          toast.success('Estudio actualizado');
          await loadAll();
        } catch (e) {
          const msg = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCancelarEstudioMicro);
          toast.error(msg);
          throw new Error(msg);
        }
      },
    });
  };

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>Sin acceso.</Typography>
      </Box>
    );
  }

  if (loading || !estudio) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Button size="small" onClick={() => navigate('/laboratorio/microbiologia/estudios')} sx={{ mb: 1 }}>
        ← Estudios microbiología
      </Button>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Resumen" />
        <Tab label="Siembras y lecturas" />
        <Tab label="Aislados" />
        <Tab label="Antibiograma" />
        <Tab label="Informes" />
      </Tabs>

      {estudioCerrado && (
        <Alert severity="info" sx={{ mb: 2 }}>
          El estudio microbiológico está cerrado. Las operaciones técnicas están bloqueadas.
        </Alert>
      )}

      {tab === 0 && (
        <EstudioMicroResumenTab
          estudio={estudio}
          canOperateTecnico={canOpEstudio}
          canMarcarInformado={canMarcarInformado}
          onIniciar={() => runEstudio(() => iniciarEstudioMicrobiologia(estudioId))}
          onCancelar={onCancelar}
          onMarcarInformado={() => runEstudio(() => marcarEstudioMicrobiologiaInformado(estudioId))}
        />
      )}
      {tab === 1 && (
        <SiembrasLecturasPanel
          estudioId={estudioId}
          siembras={bundle.siembras}
          lecturas={bundle.lecturas}
          medios={bundle.medios}
          canOperate={canOpEstudio}
          onRefresh={loadAll}
        />
      )}
      {tab === 2 && (
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
      {tab === 3 && (
        <AntibiogramaPanel
          aislados={bundle.aislados}
          antibiogramas={bundle.antibiogramas}
          resultados={bundle.resultados}
          antibioticos={bundle.antibioticos}
          canOperate={canOpEstudio}
          onRefresh={loadAll}
        />
      )}
      {tab === 4 && (
        <InformesMicrobiologiaPanel
          estudio={estudio}
          informes={bundle.informes}
          canOperate={canOpEstudio}
          canValidar={canVal}
          onRefresh={loadAll}
        />
      )}
      <MotivoDialog {...dialogProps} />
    </Box>
  );
};

export default MicrobiologiaEstudioDetalle;
