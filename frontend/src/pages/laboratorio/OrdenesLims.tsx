import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
  CircularProgress,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import { getListadoOrdenesDiaPdfBlob, listSolicitudesExamen } from '../../services/limsApi';
import { formatLimsPdfDownloadError, printPdfBlob } from '../../utils/limsDownload';
import ImprimirPedidosDialog from '../../components/lims/ImprimirPedidosDialog';
import { listEstudiosMicrobiologia } from '../../services/limsMicroApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import {
  canAccessLimsOrdenes,
  canOperateLims,
  isLimsOperativaLimitada,
} from '../../utils/limsAccess';
import {
  addLocalDays,
  buildDiasLaboratorio,
  diasVisiblesParaIncluir,
  formatFechaLocal,
  labelDiaOrden,
  parseFechaLocal,
  startOfLocalDay,
} from '../../utils/limsOrdenesFecha';
import OrdenesLimsTabla from '../../components/lims/OrdenesLimsTabla';
import { ESTADOS_ORDEN_LIMS } from '../../utils/limsEstadosOrden';
import { withNavBack } from '../../utils/navBack';
import {
  estadosMicroDesdeFiltroLab,
  mapLabToPendiente,
  mapMicroToPendiente,
  sortPedidosPorNumero,
  type PendientePedidoRow,
} from '../../utils/limsPendientesUnificados';
import { attachIqcStatusToRows } from '../../utils/limsIqcPrecheck';
import { interpretarNumeroOrden } from '../../utils/limsBusquedaOrden';

/** Estados en bandeja diaria (muestra ya tomada). */
const ESTADOS_BANDEJA = ESTADOS_ORDEN_LIMS.filter((s) => s !== 'PENDIENTE');

/** A completar: abiertas (sin finalizadas ni canceladas). */
const ESTADOS_A_COMPLETAR = ESTADOS_BANDEJA.filter(
  (s) => s !== 'FINALIZADO' && s !== 'CANCELADO'
);

/** Roles restringidos: solo órdenes finalizadas en esta vista. */
const ESTADOS_BANDEJA_LIMITADA = ['FINALIZADO'] as const;

const DIAS_PESTANAS_INICIAL = 7;
const COLA_TAB = '__cola__';
const FINALIZADOS_TAB = '__finalizados__';

type ModoLista = 'dia' | 'completar' | 'finalizados';

const MICRO_EN_BANDEJA = new Set([
  'RECIBIDO',
  'SEMBRADO',
  'LECTURA_PRELIMINAR',
  'IDENTIFICACION',
  'ANTIBIOGRAMA',
  'LISTO_PARA_VALIDAR',
  'VALIDADO',
  'INFORMADO',
]);

/** Cola abierta micro: sin VALIDADO/INFORMADO (van a Finalizados). */
const MICRO_COLA = new Set([
  'RECIBIDO',
  'SEMBRADO',
  'LECTURA_PRELIMINAR',
  'IDENTIFICACION',
  'ANTIBIOGRAMA',
  'LISTO_PARA_VALIDAR',
]);

const MICRO_FINALIZADOS = ['VALIDADO', 'INFORMADO'] as const;

/** Ventana de listado en solapa Finalizados (hoy inclusive). */
const FINALIZADOS_DIAS = 15;

async function cargarMicrosConEstados(
  base: Parameters<typeof listEstudiosMicrobiologia>[0],
  microEstadosFiltro: string[] | null
): Promise<Awaited<ReturnType<typeof listEstudiosMicrobiologia>>> {
  if (microEstadosFiltro && microEstadosFiltro.length > 1) {
    const batches = await Promise.all(
      microEstadosFiltro.map((est) => listEstudiosMicrobiologia({ ...base, estado: est }))
    );
    const seen = new Set<number>();
    const out: Awaited<ReturnType<typeof listEstudiosMicrobiologia>> = [];
    for (const batch of batches) {
      for (const e of batch) {
        if (!seen.has(e.id)) {
          seen.add(e.id);
          out.push(e);
        }
      }
    }
    return out;
  }
  return listEstudiosMicrobiologia(
    microEstadosFiltro?.length === 1 ? { ...base, estado: microEstadosFiltro[0] } : base
  );
}

const OrdenesLims: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<PendientePedidoRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [filtroNumero, setFiltroNumero] = useState('');
  const [filtroNumeroDebounced, setFiltroNumeroDebounced] = useState('');
  const [filtroPaciente, setFiltroPaciente] = useState('');
  const [filtroPacienteDebounced, setFiltroPacienteDebounced] = useState('');
  const [diaSeleccionado, setDiaSeleccionado] = useState(() => startOfLocalDay());
  const [diasPestanas, setDiasPestanas] = useState(DIAS_PESTANAS_INICIAL);
  const [modoLista, setModoLista] = useState<ModoLista>(() =>
    isLimsOperativaLimitada(currentUser) ? 'finalizados' : 'dia'
  );
  const [imprimiendoListado, setImprimiendoListado] = useState(false);
  const [dialogPedidosOpen, setDialogPedidosOpen] = useState(false);

  const allowed = canAccessLimsOrdenes(currentUser);
  const vistaLimitada = isLimsOperativaLimitada(currentUser);
  const puedeObraSocial = canOperateLims(currentUser);
  const colaDisponible = !vistaLimitada;
  const modoCompletar = colaDisponible && modoLista === 'completar';
  const modoFinalizados = modoLista === 'finalizados';

  const [estadoFiltro, setEstadoFiltro] = useState<string>(() =>
    isLimsOperativaLimitada(currentUser) ? 'FINALIZADO' : ''
  );

  const estadosFiltroOpciones = modoFinalizados
    ? ESTADOS_BANDEJA_LIMITADA
    : modoCompletar
      ? ESTADOS_A_COMPLETAR
      : vistaLimitada
        ? ESTADOS_BANDEJA_LIMITADA
        : ESTADOS_BANDEJA;

  const fechaApi = formatFechaLocal(diaSeleccionado);
  const interpNumero = useMemo(
    () => interpretarNumeroOrden(filtroNumeroDebounced),
    [filtroNumeroDebounced]
  );
  const qPaciente = filtroPacienteDebounced.trim();
  const busquedaPorProtocolo = interpNumero.tipo === 'exacto';
  const busquedaPorPaciente = !busquedaPorProtocolo && qPaciente.length > 0;
  /** Búsqueda global (nº o paciente): no acota al día / cola. */
  const busquedaGlobal = busquedaPorProtocolo || busquedaPorPaciente;

  const diasTabs = useMemo(() => buildDiasLaboratorio(diasPestanas), [diasPestanas]);
  const tabValue = modoCompletar
    ? COLA_TAB
    : modoFinalizados
      ? FINALIZADOS_TAB
      : fechaApi;

  useEffect(() => {
    const t = window.setTimeout(() => setFiltroNumeroDebounced(filtroNumero), 300);
    return () => window.clearTimeout(t);
  }, [filtroNumero]);

  useEffect(() => {
    const t = window.setTimeout(() => setFiltroPacienteDebounced(filtroPaciente), 350);
    return () => window.clearTimeout(t);
  }, [filtroPaciente]);

  const load = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    try {
      let labs: Awaited<ReturnType<typeof listSolicitudesExamen>>;
      let micros: Awaited<ReturnType<typeof listEstudiosMicrobiologia>> = [];

      // 1) Número de protocolo exacto (130 → LAB-año-00130, o 2025-00130).
      if (interpNumero.tipo === 'exacto') {
        const [labsRes, microsRes] = await Promise.all([
          listSolicitudesExamen({ numero: interpNumero.numero }),
          listEstudiosMicrobiologia({ numero: interpNumero.numero }).catch(() => []),
        ]);
        labs = labsRes;
        micros = microsRes;
        setRows(
          await attachIqcStatusToRows(
            sortPedidosPorNumero([
              ...labs.map(mapLabToPendiente),
              ...micros.map(mapMicroToPendiente),
            ])
          )
        );
        return;
      }

      // 2) Paciente (nombre / DNI) — búsqueda API, sin acotar al día.
      if (qPaciente) {
        const labParams: Parameters<typeof listSolicitudesExamen>[0] = { search: qPaciente };
        const microParams: Parameters<typeof listEstudiosMicrobiologia>[0] = {
          search: qPaciente,
        };
        if (estadoFiltro) {
          labParams.estado = estadoFiltro;
        }
        const [labsRes, microsRes] = await Promise.all([
          listSolicitudesExamen(labParams),
          cargarMicrosConEstados(
            microParams,
            estadoFiltro ? estadosMicroDesdeFiltroLab(estadoFiltro) : null
          ).catch(() => []),
        ]);
        labs = labsRes;
        micros = microsRes;
        let microRows = micros.map(mapMicroToPendiente);
        if (estadoFiltro) {
          const allowedMicro = estadosMicroDesdeFiltroLab(estadoFiltro);
          if (allowedMicro) {
            microRows = microRows.filter((r) => allowedMicro.includes(r.estado));
          }
        }
        setRows(
          await attachIqcStatusToRows(
            sortPedidosPorNumero([...labs.map(mapLabToPendiente), ...microRows])
          )
        );
        return;
      }

      // 3) A completar: abiertas (nunca FINALIZADO).
      if (modoCompletar) {
        const labParams: Parameters<typeof listSolicitudesExamen>[0] = {};
        const microParams: Parameters<typeof listEstudiosMicrobiologia>[0] = {};
        let microEstadosFiltro: string[] | null = null;

        // No permitir FINALIZADO/CANCELADO en esta solapa aunque el filtro diga otra cosa.
        const estadoAbierto =
          estadoFiltro && ESTADOS_A_COMPLETAR.includes(estadoFiltro as (typeof ESTADOS_A_COMPLETAR)[number])
            ? estadoFiltro
            : '';

        if (estadoAbierto) {
          labParams.estado = estadoAbierto;
          microEstadosFiltro = estadosMicroDesdeFiltroLab(estadoAbierto);
        } else {
          labParams.cola = 'trabajo';
          microParams.cola = 'trabajo';
        }

        const [labsRes, microsRes] = await Promise.all([
          listSolicitudesExamen(labParams),
          cargarMicrosConEstados(microParams, microEstadosFiltro).catch(() => []),
        ]);
        labs = labsRes;
        micros = microsRes;

        let microRows = micros.map(mapMicroToPendiente);
        if (microEstadosFiltro) {
          microRows = microRows.filter((r) => microEstadosFiltro!.includes(r.estado));
        } else {
          microRows = microRows.filter((r) => MICRO_COLA.has(r.estado));
        }
        // Defensa: nunca mostrar cierre micro en A completar.
        microRows = microRows.filter((r) => !MICRO_FINALIZADOS.includes(r.estado as (typeof MICRO_FINALIZADOS)[number]));

        setRows(
          await attachIqcStatusToRows(
            sortPedidosPorNumero([
              ...labs.filter((l) => l.estado !== 'FINALIZADO' && l.estado !== 'CANCELADO').map(mapLabToPendiente),
              ...microRows,
            ])
          )
        );
        return;
      }

      // 4) Finalizados: solo cierre clínico / micro informado-validado (últimos 15 días).
      // La búsqueda por número (arriba) no aplica este tope: encuentra cualquier año.
      if (modoFinalizados) {
        const hoy = startOfLocalDay();
        const fechaHasta = formatFechaLocal(hoy);
        const fechaDesde = formatFechaLocal(addLocalDays(hoy, -(FINALIZADOS_DIAS - 1)));
        const [labsRes, microsRes] = await Promise.all([
          listSolicitudesExamen({
            estado: 'FINALIZADO',
            fecha_desde: fechaDesde,
            fecha_hasta: fechaHasta,
          }),
          cargarMicrosConEstados(
            { fecha_desde: fechaDesde, fecha_hasta: fechaHasta },
            [...MICRO_FINALIZADOS]
          ).catch(() => []),
        ]);
        labs = labsRes;
        micros = microsRes;
        const microRows = micros
          .map(mapMicroToPendiente)
          .filter((r) => MICRO_FINALIZADOS.includes(r.estado as (typeof MICRO_FINALIZADOS)[number]));

        setRows(
          await attachIqcStatusToRows(
            sortPedidosPorNumero([...labs.map(mapLabToPendiente), ...microRows])
          )
        );
        return;
      }

      // 5) Vista por día (lab por fecha_muestra; micro por fecha en API).
      const [labsRes, microsRes] = await Promise.all([
        listSolicitudesExamen({
          estado: estadoFiltro || undefined,
          fecha_muestra: fechaApi,
        }),
        listEstudiosMicrobiologia({ fecha: fechaApi }).catch(() => []),
      ]);
      labs = labsRes;
      micros = microsRes;
      let microRows = micros
        .filter((e) => MICRO_EN_BANDEJA.has(e.estado))
        .map(mapMicroToPendiente);
      if (vistaLimitada) {
        microRows = microRows.filter((r) =>
          MICRO_FINALIZADOS.includes(r.estado as (typeof MICRO_FINALIZADOS)[number])
        );
      } else if (estadoFiltro) {
        if (estadoFiltro === 'FINALIZADO') {
          microRows = microRows.filter((r) =>
            MICRO_FINALIZADOS.includes(r.estado as (typeof MICRO_FINALIZADOS)[number])
          );
        } else {
          const allowedMicro = estadosMicroDesdeFiltroLab(estadoFiltro);
          microRows = allowedMicro
            ? microRows.filter((r) => allowedMicro.includes(r.estado))
            : [];
        }
      }
      setRows(
        await attachIqcStatusToRows(
          sortPedidosPorNumero([...labs.map(mapLabToPendiente), ...microRows])
        )
      );
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarOrdenes));
    } finally {
      setLoading(false);
    }
  }, [
    allowed,
    estadoFiltro,
    fechaApi,
    interpNumero,
    modoCompletar,
    modoFinalizados,
    qPaciente,
    vistaLimitada,
  ]);

  useEffect(() => {
    load();
  }, [load]);

  const filtradas = rows;

  const etiquetaVista = modoCompletar
    ? 'A completar'
    : modoFinalizados
      ? 'Finalizados'
      : labelDiaOrden(diaSeleccionado);

  const imprimirListado = async () => {
    if (!filtradas.length) return;
    setImprimiendoListado(true);
    try {
      const blob = await getListadoOrdenesDiaPdfBlob(
        filtradas.map((r) => ({ tipo: r.tipo, id: r.id })),
        modoCompletar || modoFinalizados ? formatFechaLocal(startOfLocalDay()) : fechaApi
      );
      await printPdfBlob(blob);
    } catch (e) {
      toast.error(formatLimsPdfDownloadError(e));
    } finally {
      setImprimiendoListado(false);
    }
  };

  const handleTabChange = (_: React.SyntheticEvent, v: string) => {
    if (v === COLA_TAB) {
      setModoLista('completar');
      setEstadoFiltro((prev) =>
        prev && ESTADOS_A_COMPLETAR.includes(prev as (typeof ESTADOS_A_COMPLETAR)[number])
          ? prev
          : ''
      );
      return;
    }
    if (v === FINALIZADOS_TAB) {
      setModoLista('finalizados');
      setEstadoFiltro('FINALIZADO');
      return;
    }
    setModoLista('dia');
    setEstadoFiltro(vistaLimitada ? 'FINALIZADO' : '');
    setDiaSeleccionado(parseFechaLocal(v));
  };

  const handleFechaManual = (iso: string) => {
    if (!iso) return;
    const d = parseFechaLocal(iso);
    setModoLista('dia');
    setEstadoFiltro(vistaLimitada ? 'FINALIZADO' : '');
    setDiaSeleccionado(d);
    setDiasPestanas((n) => diasVisiblesParaIncluir(d, n));
  };

  const onVer = (row: PendientePedidoRow) => {
    if (row.tipo === 'MICROBIOLOGIA') {
      navigate(
        `/laboratorio/microbiologia/estudios/${row.id}`,
        withNavBack('/laboratorio/ordenes', '← Volver al listado')
      );
      return;
    }
    navigate(
      `/laboratorio/ordenes/${row.id}`,
      withNavBack('/laboratorio/ordenes', '← Volver al listado')
    );
  };

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>No tiene permisos para acceder al módulo de órdenes LIMS.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }} data-demo="page-lims-ordenes">
      <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h5" gutterBottom>
            Órdenes LIMS
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {busquedaPorProtocolo && interpNumero.tipo === 'exacto'
              ? `Protocolo exacto ${interpNumero.numero}.`
              : busquedaPorPaciente
                ? `Búsqueda por paciente «${qPaciente}».`
                : modoCompletar
                  ? 'A completar: pedidos no finalizados (todos los días). Extracción y etiquetas en '
                  : modoFinalizados
                    ? `Finalizados: liberadas de los últimos ${FINALIZADOS_DIAS} días. Buscá por número (solo dígitos = año actual; anteponé el año para otros). Extracción y etiquetas en `
                    : vistaLimitada
                      ? `Pedidos finalizados / informados con actividad el ${labelDiaOrden(diaSeleccionado)}. Las pendientes de recepción están en `
                      : `Lab clínico (muestra tomada) y microbiología (recibidos) el ${labelDiaOrden(diaSeleccionado)}. Pendientes de recepción en `}
            {!busquedaGlobal && (
              <Button
                size="small"
                sx={{ p: 0, minWidth: 0, verticalAlign: 'baseline' }}
                onClick={() => navigate('/laboratorio/pendientes')}
              >
                Pendientes
              </Button>
            )}
            {!busquedaGlobal && '.'}
          </Typography>
        </Box>
      </Stack>

      <Paper sx={{ mb: 2 }}>
        <Box
          sx={{
            px: 2,
            pt: 1.5,
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 1,
          }}
        >
          <Typography variant="subtitle2">
            {modoCompletar
              ? 'A completar'
              : modoFinalizados
                ? 'Finalizados'
                : 'Día de toma / recepción'}
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
            <TextField
              type="date"
              size="small"
              label="Ir a fecha"
              value={fechaApi}
              onChange={(e) => handleFechaManual(e.target.value)}
              InputLabelProps={{ shrink: true }}
            />
            <Button size="small" variant="outlined" onClick={() => setDiasPestanas((n) => n + 7)}>
              Ver más días
            </Button>
          </Box>
        </Box>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          sx={{ px: 1 }}
        >
          {colaDisponible && (
            <Tab value={COLA_TAB} label="A COMPLETAR" sx={{ fontWeight: 700 }} />
          )}
          <Tab value={FINALIZADOS_TAB} label="FINALIZADOS" sx={{ fontWeight: 700 }} />
          {diasTabs.map((d) => {
            const key = formatFechaLocal(d);
            return <Tab key={key} value={key} label={labelDiaOrden(d)} />;
          })}
        </Tabs>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Box
          sx={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 2,
            alignItems: 'center',
            // Reserva espacio para helperText absoluto (evita desalineado Número vs Paciente).
            pb: 2.5,
            '& .MuiTextField-root': {
              position: 'relative',
              '& .MuiFormHelperText-root': {
                position: 'absolute',
                left: 0,
                top: '100%',
                m: 0,
                mt: 0.25,
                lineHeight: 1.25,
                whiteSpace: 'nowrap',
              },
            },
          }}
        >
          <TextField
            size="small"
            label="Número"
            value={filtroNumero}
            onChange={(e) => setFiltroNumero(e.target.value)}
            sx={{ width: 180 }}
            placeholder="130"
            helperText="130 = año actual · 2025-00130"
            inputProps={{ inputMode: 'numeric', 'aria-label': 'Número de protocolo' }}
          />
          <TextField
            size="small"
            label="Paciente"
            value={filtroPaciente}
            onChange={(e) => setFiltroPaciente(e.target.value)}
            sx={{ minWidth: 220, flex: '1 1 200px' }}
            placeholder="Apellido o DNI"
            helperText="Nombre o DNI"
            disabled={busquedaPorProtocolo}
            inputProps={{ 'aria-label': 'Buscar paciente' }}
          />
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Estado</InputLabel>
            <Select
              label="Estado"
              value={modoFinalizados ? 'FINALIZADO' : estadoFiltro}
              onChange={(e) => setEstadoFiltro(e.target.value as string)}
              disabled={vistaLimitada || modoFinalizados}
            >
              {!vistaLimitada && !modoFinalizados && (
                <MenuItem value="">
                  {modoCompletar ? 'No finalizadas' : 'Todos (con muestra)'}
                </MenuItem>
              )}
              {estadosFiltroOpciones.map((s) => (
                <MenuItem key={s} value={s}>
                  {s}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button size="small" variant="outlined" onClick={load} disabled={loading}>
            Actualizar
          </Button>
          <Chip size="small" label={`${filtradas.length} pedido(s)`} variant="outlined" />
          {puedeObraSocial && (
            <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', ml: { sm: 'auto' } }}>
              <Button
                size="small"
                variant="outlined"
                onClick={imprimirListado}
                disabled={loading || imprimiendoListado || filtradas.length === 0}
                startIcon={imprimiendoListado ? <CircularProgress size={16} /> : undefined}
              >
                Imprimir listado
              </Button>
              <Button
                size="small"
                variant="contained"
                onClick={() => setDialogPedidosOpen(true)}
                disabled={loading || filtradas.length === 0}
              >
                Imprimir pedidos
              </Button>
            </Box>
          )}
        </Box>
      </Paper>

      <ImprimirPedidosDialog
        open={dialogPedidosOpen}
        onClose={() => setDialogPedidosOpen(false)}
        rows={filtradas}
        diaLabel={etiquetaVista}
      />

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <Paper>
          <OrdenesLimsTabla
            rows={filtradas}
            emptyMessage={
              busquedaPorProtocolo
                ? 'Sin pedidos con ese número.'
                : busquedaPorPaciente
                  ? 'Sin pedidos para ese paciente.'
                  : modoCompletar
                    ? 'Sin pedidos por completar.'
                    : modoFinalizados
                      ? `Sin finalizados en los últimos ${FINALIZADOS_DIAS} días. Buscá por número para órdenes más antiguas.`
                      : `Sin pedidos el ${labelDiaOrden(diaSeleccionado).toLowerCase()}.`
            }
            mostrarIndiceDia={modoLista === 'dia'}
            onVer={onVer}
            puedeObraSocial={puedeObraSocial}
            onObraSocialSaved={load}
          />
        </Paper>
      )}
    </Box>
  );
};

export default OrdenesLims;
