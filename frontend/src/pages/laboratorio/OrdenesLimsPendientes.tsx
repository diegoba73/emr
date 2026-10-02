import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
  CircularProgress,
} from '@mui/material';
import { Add } from '@mui/icons-material';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { withNavBack } from '../../utils/navBack';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { SolicitudExamenLims } from '../../types/lims';
import { listSolicitudesExamen } from '../../services/limsApi';
import {
  listEstudiosMicrobiologia,
} from '../../services/limsMicroApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canAccessLimsPendientes, canOperateLims } from '../../utils/limsAccess';
import {
  mapLabToPendiente,
  mapMicroToPendiente,
  sortPedidosPorNumero,
  type PendientePedidoRow,
} from '../../utils/limsPendientesUnificados';
import { attachIqcStatusToRows } from '../../utils/limsIqcPrecheck';
import OrdenesLimsTabla from '../../components/lims/OrdenesLimsTabla';
import NuevaOrdenLimsDialog from '../../components/lims/NuevaOrdenLimsDialog';
import TomarMuestraOrdenDialog from '../../components/lims/TomarMuestraOrdenDialog';
import EtiquetasMuestrasZplOrdenDialog from '../../components/lims/EtiquetasMuestrasZplOrdenDialog';
import ImprimirPedidoMicroDialog from '../../components/lims/micro/ImprimirPedidoMicroDialog';

type TabPendiente = 'sin_etiquetas' | 'esperando_recepcion';
type VistaExtraccion = 'hoy' | 'programadas';

function parseTabParam(raw: string | null): TabPendiente | null {
  if (raw === 'sin_etiquetas' || raw === 'esperando_recepcion') return raw;
  return null;
}

function parseVistaParam(raw: string | null): VistaExtraccion | null {
  if (raw === 'hoy' || raw === 'programadas') return raw;
  return null;
}

const OrdenesLimsPendientes: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { currentUser } = useData();
  const [rows, setRows] = useState<PendientePedidoRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [busqueda, setBusqueda] = useState('');
  const [tab, setTab] = useState<TabPendiente>(
    () => parseTabParam(searchParams.get('tab')) || 'sin_etiquetas'
  );
  const [vistaExtraccion, setVistaExtraccion] = useState<VistaExtraccion>(
    () => parseVistaParam(searchParams.get('vista')) || 'hoy'
  );
  const [nuevaOrdenOpen, setNuevaOrdenOpen] = useState(false);
  const [ordenEtiquetas, setOrdenEtiquetas] = useState<SolicitudExamenLims | null>(null);
  const [ordenZplReimprimir, setOrdenZplReimprimir] = useState<SolicitudExamenLims | null>(null);
  const [ordenAgregar, setOrdenAgregar] = useState<SolicitudExamenLims | null>(null);
  const [microImprimir, setMicroImprimir] = useState<PendientePedidoRow | null>(null);

  const allowed = canAccessLimsPendientes(currentUser);
  const puedeCrear = canOperateLims(currentUser);
  const puedeImprimir = canOperateLims(currentUser);
  const puedeAgregar = canOperateLims(currentUser);

  const goTab = useCallback(
    (next: TabPendiente) => {
      setTab(next);
      const params = new URLSearchParams(searchParams);
      params.set('tab', next);
      setSearchParams(params, { replace: true });
    },
    [searchParams, setSearchParams]
  );

  const goVista = useCallback(
    (next: VistaExtraccion) => {
      setVistaExtraccion(next);
      const params = new URLSearchParams(searchParams);
      params.set('vista', next);
      setSearchParams(params, { replace: true });
    },
    [searchParams, setSearchParams]
  );

  const load = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    try {
      const labs = await listSolicitudesExamen({
        estado: 'PENDIENTE',
        vista_extraccion: vistaExtraccion,
      });
      let micros: Awaited<ReturnType<typeof listEstudiosMicrobiologia>> = [];
      try {
        micros = await listEstudiosMicrobiologia({
          estado: 'PENDIENTE',
          vista_extraccion: vistaExtraccion,
        });
      } catch {
        micros = [];
      }
      const merged = sortPedidosPorNumero([
        ...labs.map(mapLabToPendiente),
        ...micros.map(mapMicroToPendiente),
      ]);
      setRows(await attachIqcStatusToRows(merged));
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
    } finally {
      setLoading(false);
    }
  }, [allowed, vistaExtraccion]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const fromUrl = parseTabParam(searchParams.get('tab'));
    if (fromUrl && fromUrl !== tab) setTab(fromUrl);
    const vistaUrl = parseVistaParam(searchParams.get('vista'));
    if (vistaUrl && vistaUrl !== vistaExtraccion) setVistaExtraccion(vistaUrl);
    // Solo sincronizar desde URL (p. ej. deep-link), no al cambiar tab local.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

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
    const porTab = rows.filter((r) =>
      tab === 'esperando_recepcion' ? r.esperando_recepcion : r.sin_etiquetas
    );
    if (!q) return porTab;
    return porTab.filter((r) => {
      const n = (r.numero || '').toLowerCase();
      const pn = (r.paciente_nombre || '').toLowerCase();
      const pd = (r.paciente_dni || '').toLowerCase();
      const cult = (r.cultivo_nombre || '').toLowerCase();
      return n.includes(q) || pn.includes(q) || pd.includes(q) || cult.includes(q);
    });
  }, [rows, busqueda, tab]);

  const countSinEtiquetas = useMemo(
    () => rows.filter((r) => r.sin_etiquetas).length,
    [rows]
  );
  const countEsperando = useMemo(
    () => rows.filter((r) => r.esperando_recepcion).length,
    [rows]
  );

  const handleVer = (row: PendientePedidoRow) => {
    const back = withNavBack('/laboratorio/pendientes', '← Volver a pendientes');
    if (row.tipo === 'MICROBIOLOGIA') {
      navigate(`/laboratorio/microbiologia/estudios/${row.id}`, back);
    } else {
      navigate(`/laboratorio/ordenes/${row.id}`, back);
    }
  };

  /** Primera impresión (crea tubos lab) o reimpresión ZPL; micro ZPL (primera o reimpresión). */
  const handleAccionEtiquetas = async (row: PendientePedidoRow) => {
    if (row.tipo === 'LAB_CLINICO' && row.labOrden) {
      if (tab === 'esperando_recepcion') {
        setOrdenZplReimprimir(row.labOrden);
        return;
      }
      setOrdenEtiquetas(row.labOrden);
      return;
    }

    if (row.tipo === 'MICROBIOLOGIA') {
      setMicroImprimir(row);
    }
  };

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>No tiene permisos para acceder al módulo LIMS.</Typography>
      </Box>
    );
  }

  const esperandoRecepcion = tab === 'esperando_recepcion';

  return (
    <Box data-demo="page-lims-pendientes" sx={{ p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h5" gutterBottom>
            Pendientes
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Por defecto ves lo que hay que sacar <strong>hoy</strong> (incluye vencidas). Las de
            mañana u otro día están en <strong>Programadas</strong>. Flujo: Sin etiquetas → imprimís →
            Esperando recepción.
          </Typography>
        </Box>
        {puedeCrear && (
          <Button variant="contained" startIcon={<Add />} onClick={() => setNuevaOrdenOpen(true)}>
            Nueva orden
          </Button>
        )}
      </Stack>

      <Paper sx={{ px: 2, pt: 1, mb: 2 }}>
        <Tabs
          value={vistaExtraccion}
          onChange={(_, v: VistaExtraccion) => goVista(v)}
          variant="scrollable"
          allowScrollButtonsMobile
          sx={{ mb: 0.5 }}
        >
          <Tab value="hoy" label="Para hoy" />
          <Tab value="programadas" label="Programadas" />
        </Tabs>
        <Tabs
          value={tab}
          onChange={(_, v: TabPendiente) => goTab(v)}
          variant="scrollable"
          allowScrollButtonsMobile
        >
          <Tab value="sin_etiquetas" label={`Sin etiquetas (${countSinEtiquetas})`} />
          <Tab value="esperando_recepcion" label={`Esperando recepción (${countEsperando})`} />
        </Tabs>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', py: 2 }}>
          <TextField
            size="small"
            label="Buscar (nº, paciente, DNI, cultivo)"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            sx={{ minWidth: 240 }}
          />
          <Button variant="outlined" onClick={load} disabled={loading}>
            Actualizar
          </Button>
          <Chip
            size="small"
            label={`${filtradas.length} en esta vista`}
            color="warning"
            variant="outlined"
          />
        </Box>
        {vistaExtraccion === 'programadas' && (
          <Alert severity="info" sx={{ mb: 2 }}>
            Pedidos con extracción futura. No se mezclan con urgencias ni controles del día.
          </Alert>
        )}
        {esperandoRecepcion && (
          <Alert severity="info" sx={{ mb: 2 }}>
            Pedidos con etiquetas impresas, pendientes de recepción en laboratorio. Si se pierden
            las etiquetas, usá <strong>Reimprimir etiquetas</strong>.
          </Alert>
        )}
      </Paper>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Paper>
          <OrdenesLimsTabla
            rows={filtradas}
            emptyMessage={
              vistaExtraccion === 'programadas'
                ? esperandoRecepcion
                  ? 'No hay pedidos programados esperando recepción.'
                  : 'No hay pedidos programados sin etiquetas.'
                : esperandoRecepcion
                  ? 'No hay pedidos esperando recepción para hoy.'
                  : 'No hay pedidos pendientes sin etiquetas para hoy.'
            }
            columnaFecha="solicitud"
            accionLabel={
              !puedeImprimir
                ? 'Ver'
                : esperandoRecepcion
                  ? 'Reimprimir etiquetas'
                  : 'Imprimir etiquetas'
            }
            onVer={handleVer}
            onAgregarExamenes={
              puedeAgregar ? (orden) => setOrdenAgregar(orden) : undefined
            }
            onAccion={puedeImprimir ? handleAccionEtiquetas : undefined}
            puedeObraSocial={puedeImprimir}
            onObraSocialSaved={load}
          />
        </Paper>
      )}

      <NuevaOrdenLimsDialog
        open={nuevaOrdenOpen}
        onClose={() => setNuevaOrdenOpen(false)}
        onCreated={() => {
          load();
        }}
        onCreatedMicro={() => {
          load();
        }}
      />

      <NuevaOrdenLimsDialog
        open={!!ordenAgregar}
        onClose={() => setOrdenAgregar(null)}
        agregarAOrdenId={ordenAgregar?.id ?? null}
        agregarAOrdenNumero={ordenAgregar?.numero ?? null}
        pacienteId={ordenAgregar?.paciente ?? null}
        onCreated={() => {
          setOrdenAgregar(null);
          load();
        }}
      />

      {ordenEtiquetas && (
        <TomarMuestraOrdenDialog
          open={!!ordenEtiquetas}
          orden={ordenEtiquetas}
          muestrasExistentes={[]}
          origenOrden={{
            origen_solicitud: ordenEtiquetas.origen_solicitud,
            origen_solicitud_display: ordenEtiquetas.origen_solicitud_display,
            procedencia_display: ordenEtiquetas.procedencia_display,
          }}
          onClose={() => setOrdenEtiquetas(null)}
          onSuccess={() => {
            load();
            goTab('esperando_recepcion');
          }}
        />
      )}

      {ordenZplReimprimir && (
        <EtiquetasMuestrasZplOrdenDialog
          open={!!ordenZplReimprimir}
          solicitudId={ordenZplReimprimir.id}
          solicitudNumero={ordenZplReimprimir.numero}
          origenOrden={{
            origen_solicitud: ordenZplReimprimir.origen_solicitud,
            origen_solicitud_display: ordenZplReimprimir.origen_solicitud_display,
            procedencia_display: ordenZplReimprimir.procedencia_display,
          }}
          onClose={() => setOrdenZplReimprimir(null)}
          onUpdated={load}
        />
      )}

      {microImprimir && (
        <ImprimirPedidoMicroDialog
          open={!!microImprimir}
          estudioId={microImprimir.id}
          estudioNumero={microImprimir.numero}
          reimpresion={tab === 'esperando_recepcion'}
          onClose={() => setMicroImprimir(null)}
          onEtiquetasOk={() => {
            load();
            goTab('esperando_recepcion');
          }}
        />
      )}
    </Box>
  );
};

export default OrdenesLimsPendientes;
