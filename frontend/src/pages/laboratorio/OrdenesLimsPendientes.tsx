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
import { downloadEtiquetasOrdenMuestras, listSolicitudesExamen } from '../../services/limsApi';
import {
  downloadEtiquetasEstudioMicro,
  listEstudiosMicrobiologia,
} from '../../services/limsMicroApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canAccessLimsPendientes, canOperateLims } from '../../utils/limsAccess';
import {
  mapLabToPendiente,
  mapMicroToPendiente,
  type PendientePedidoRow,
} from '../../utils/limsPendientesUnificados';
import { attachIqcStatusToRows } from '../../utils/limsIqcPrecheck';
import OrdenesLimsTabla from '../../components/lims/OrdenesLimsTabla';
import NuevaOrdenLimsDialog from '../../components/lims/NuevaOrdenLimsDialog';
import TomarMuestraOrdenDialog from '../../components/lims/TomarMuestraOrdenDialog';

type TabPendiente = 'sin_etiquetas' | 'esperando_recepcion';

function parseTabParam(raw: string | null): TabPendiente | null {
  if (raw === 'sin_etiquetas' || raw === 'esperando_recepcion') return raw;
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
  const [nuevaOrdenOpen, setNuevaOrdenOpen] = useState(false);
  const [ordenEtiquetas, setOrdenEtiquetas] = useState<SolicitudExamenLims | null>(null);
  const [ordenAgregar, setOrdenAgregar] = useState<SolicitudExamenLims | null>(null);
  const [imprimiendo, setImprimiendo] = useState(false);

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

  const load = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    try {
      const labs = await listSolicitudesExamen({ estado: 'PENDIENTE' });
      let micros: Awaited<ReturnType<typeof listEstudiosMicrobiologia>> = [];
      try {
        micros = await listEstudiosMicrobiologia({ estado: 'PENDIENTE' });
      } catch {
        micros = [];
      }
      const merged = [
        ...labs.map(mapLabToPendiente),
        ...micros.map(mapMicroToPendiente),
      ].sort((a, b) => {
        const ta = a.fecha_solicitud ? new Date(a.fecha_solicitud).getTime() : 0;
        const tb = b.fecha_solicitud ? new Date(b.fecha_solicitud).getTime() : 0;
        return tb - ta;
      });
      setRows(await attachIqcStatusToRows(merged));
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
    const fromUrl = parseTabParam(searchParams.get('tab'));
    if (fromUrl && fromUrl !== tab) setTab(fromUrl);
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

  /** Primera impresión (crea tubos lab / marca micro) o reimpresión PDF. */
  const handleAccionEtiquetas = async (row: PendientePedidoRow) => {
    if (row.tipo === 'LAB_CLINICO' && row.labOrden) {
      if (tab === 'esperando_recepcion') {
        setImprimiendo(true);
        try {
          await downloadEtiquetasOrdenMuestras(row.id, row.numero);
          toast.success('Etiquetas reimpresas. Podés volver a pegarlas en los tubos.');
        } catch (e) {
          toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
        } finally {
          setImprimiendo(false);
        }
        return;
      }
      setOrdenEtiquetas(row.labOrden);
      return;
    }

    if (row.tipo === 'MICROBIOLOGIA') {
      setImprimiendo(true);
      try {
        await downloadEtiquetasEstudioMicro(row.id);
        toast.success(
          tab === 'esperando_recepcion'
            ? 'Etiqueta reimpresa.'
            : 'Etiqueta generada. El pedido pasó a «Esperando recepción».'
        );
        await load();
        goTab('esperando_recepcion');
      } catch (e) {
        toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
      } finally {
        setImprimiendo(false);
      }
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
    <Box sx={{ p: 2 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h5" gutterBottom>
            Pendientes
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Flujo: <strong>Sin etiquetas</strong> → imprimís →{' '}
            <strong>Esperando recepción</strong> (acá sigue visible hasta que lab recibe la muestra;
            podés reimprimir si se pierden). Órdenes LIMS es para pedidos ya recibidos / en proceso.
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
          <Button variant="outlined" onClick={load} disabled={loading || imprimiendo}>
            Actualizar
          </Button>
          <Chip
            size="small"
            label={`${filtradas.length} en esta vista`}
            color="warning"
            variant="outlined"
          />
        </Box>
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
              esperandoRecepcion
                ? 'No hay pedidos esperando recepción.'
                : 'No hay pedidos pendientes sin etiquetas.'
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
          onClose={() => setOrdenEtiquetas(null)}
          onSuccess={() => {
            setOrdenEtiquetas(null);
            load();
            goTab('esperando_recepcion');
          }}
        />
      )}
    </Box>
  );
};

export default OrdenesLimsPendientes;
