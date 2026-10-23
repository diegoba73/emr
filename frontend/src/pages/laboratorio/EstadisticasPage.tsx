import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  MenuItem,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Typography,
} from '@mui/material';
import {
  downloadEstadisticasCsv,
  getEstadisticasPorEstado,
  getEstadisticasPorExamen,
  getEstadisticasPorObraSocial,
  getEstadisticasPorOrigen,
  getEstadisticasResumen,
  getEstadisticasSeries,
  type EstadisticasFiltros,
  type EstadisticasGranularidad,
  type EstadisticasResumen,
  type EstadisticasSeries,
} from '../../services/limsApi';
import { useData } from '../../contexts/DataContext';
import { canAccessEstadisticasLims } from '../../utils/permissions';

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoISO(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function yearStartISO() {
  return `${new Date().getFullYear()}-01-01`;
}

type TabKey = 'examen' | 'obra_social' | 'origen' | 'estado';

const ESTADOS = [
  '',
  'PENDIENTE',
  'EN_PROCESO',
  'INFORMADO_PARCIAL',
  'LISTO_PARA_VALIDAR',
  'FINALIZADO',
  'CANCELADO',
];

const ORIGENES = [
  '',
  'GUARDIA',
  'AMBULATORIO_CEHTA',
  'AMBULATORIO_ICPL',
  'INTERNACION_UCO',
  'INTERNACION_UCE',
  'EXTERNO_CEHTA',
  'EXTERNO_ICPL',
];

const EstadisticasPage: React.FC = () => {
  const { currentUser } = useData();
  const allowed = canAccessEstadisticasLims(currentUser);

  const [desde, setDesde] = useState(daysAgoISO(30));
  const [hasta, setHasta] = useState(todayISO());
  const [granularidad, setGranularidad] = useState<EstadisticasGranularidad>('dia');
  const [estado, setEstado] = useState('');
  const [origen, setOrigen] = useState('');
  const [obraSocial, setObraSocial] = useState('');
  const [codigo, setCodigo] = useState('');
  const [tab, setTab] = useState<TabKey>('examen');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resumen, setResumen] = useState<EstadisticasResumen | null>(null);
  const [serie, setSerie] = useState<EstadisticasSeries | null>(null);
  const [tabla, setTabla] = useState<
    { key: string; label: string; cantidad: number; porcentaje: number }[]
  >([]);

  const filtros: EstadisticasFiltros = useMemo(
    () => ({
      desde,
      hasta,
      granularidad,
      estado: estado || undefined,
      origen: origen || undefined,
      obra_social: obraSocial || undefined,
      codigo: codigo || undefined,
    }),
    [codigo, desde, estado, granularidad, hasta, obraSocial, origen]
  );

  const cargar = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [r, s] = await Promise.all([
        getEstadisticasResumen(filtros),
        getEstadisticasSeries(filtros),
      ]);
      setResumen(r);
      setSerie(s);

      if (tab === 'examen') {
        const t = await getEstadisticasPorExamen(filtros);
        setTabla(
          t.items.map((i) => ({
            key: i.codigo || '',
            label: `${i.codigo} — ${i.nombre}`,
            cantidad: i.cantidad,
            porcentaje: i.porcentaje,
          }))
        );
      } else if (tab === 'obra_social') {
        const t = await getEstadisticasPorObraSocial(filtros);
        setTabla(
          t.items.map((i) => ({
            key: i.obra_social,
            label: i.obra_social,
            cantidad: i.cantidad,
            porcentaje: i.porcentaje,
          }))
        );
      } else if (tab === 'origen') {
        const t = await getEstadisticasPorOrigen(filtros);
        setTabla(
          t.items.map((i) => ({
            key: i.origen,
            label: i.label,
            cantidad: i.cantidad,
            porcentaje: i.porcentaje,
          }))
        );
      } else {
        const t = await getEstadisticasPorEstado(filtros);
        setTabla(
          t.items.map((i) => ({
            key: i.estado,
            label: i.estado,
            cantidad: i.cantidad,
            porcentaje: i.porcentaje,
          }))
        );
      }
    } catch {
      setError('No se pudieron cargar las estadísticas.');
      setResumen(null);
      setSerie(null);
      setTabla([]);
    } finally {
      setLoading(false);
    }
  }, [filtros, tab]);

  useEffect(() => {
    if (!allowed) return;
    void cargar();
  }, [allowed, cargar]);

  const maxSerie = useMemo(() => {
    if (!serie?.puntos.length) return 1;
    return Math.max(1, ...serie.puntos.map((p) => Math.max(p.ordenes, p.examenes)));
  }, [serie]);

  const maxTabla = useMemo(() => {
    if (!tabla.length) return 1;
    return Math.max(1, ...tabla.map((r) => r.cantidad));
  }, [tabla]);

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">
          Solo secretaría de laboratorio, bioquímico o administrador.
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Estadísticas
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Volúmenes LIMS (órdenes y exámenes) por período, sin datos de pacientes.
      </Typography>

      <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" flexWrap="wrap" gap={1} sx={{ mb: 2 }}>
          <Chip
            label="Hoy"
            size="small"
            onClick={() => {
              setDesde(todayISO());
              setHasta(todayISO());
              setGranularidad('dia');
            }}
          />
          <Chip
            label="7 días"
            size="small"
            onClick={() => {
              setDesde(daysAgoISO(7));
              setHasta(todayISO());
              setGranularidad('dia');
            }}
          />
          <Chip
            label="30 días"
            size="small"
            onClick={() => {
              setDesde(daysAgoISO(30));
              setHasta(todayISO());
              setGranularidad('dia');
            }}
          />
          <Chip
            label="Año"
            size="small"
            onClick={() => {
              setDesde(yearStartISO());
              setHasta(todayISO());
              setGranularidad('mes');
            }}
          />
        </Stack>

        <Stack direction="row" flexWrap="wrap" gap={2} alignItems="center">
          <TextField
            size="small"
            label="Desde"
            type="date"
            InputLabelProps={{ shrink: true }}
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
          />
          <TextField
            size="small"
            label="Hasta"
            type="date"
            InputLabelProps={{ shrink: true }}
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
          />
          <TextField
            select
            size="small"
            label="Granularidad"
            value={granularidad}
            onChange={(e) => setGranularidad(e.target.value as EstadisticasGranularidad)}
            sx={{ minWidth: 120 }}
          >
            <MenuItem value="dia">Día</MenuItem>
            <MenuItem value="mes">Mes</MenuItem>
            <MenuItem value="anio">Año</MenuItem>
          </TextField>
          <TextField
            select
            size="small"
            label="Estado"
            value={estado}
            onChange={(e) => setEstado(e.target.value)}
            sx={{ minWidth: 160 }}
          >
            {ESTADOS.map((e) => (
              <MenuItem key={e || 'all'} value={e}>
                {e || 'Todos'}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            select
            size="small"
            label="Origen"
            value={origen}
            onChange={(e) => setOrigen(e.target.value)}
            sx={{ minWidth: 180 }}
          >
            {ORIGENES.map((o) => (
              <MenuItem key={o || 'all'} value={o}>
                {o || 'Todos'}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            size="small"
            label="Obra social"
            value={obraSocial}
            onChange={(e) => setObraSocial(e.target.value)}
          />
          <TextField
            size="small"
            label="Código examen"
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
          />
          <Button variant="contained" onClick={() => void cargar()} disabled={loading}>
            Consultar
          </Button>
          <Button
            variant="outlined"
            disabled={loading}
            onClick={() =>
              void downloadEstadisticasCsv({ ...filtros, dimension: tab === 'examen' ? 'examen' : tab })
            }
          >
            Exportar CSV
          </Button>
        </Stack>
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      )}

      {!loading && resumen && (
        <>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ mb: 2 }}>
            <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
              <Typography variant="overline" color="text.secondary">
                Órdenes
              </Typography>
              <Typography variant="h4">{resumen.total_ordenes}</Typography>
            </Paper>
            <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
              <Typography variant="overline" color="text.secondary">
                Exámenes
              </Typography>
              <Typography variant="h4">{resumen.total_examenes}</Typography>
            </Paper>
            <Paper variant="outlined" sx={{ p: 2, flex: 1 }}>
              <Typography variant="overline" color="text.secondary">
                Período
              </Typography>
              <Typography variant="h6">
                {resumen.desde} → {resumen.hasta}
              </Typography>
            </Paper>
          </Stack>

          <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Serie temporal
            </Typography>
            {!serie?.puntos.length ? (
              <Typography variant="body2" color="text.secondary">
                Sin datos en el rango.
              </Typography>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {serie.puntos.map((p) => (
                  <Box key={p.periodo}>
                    <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.25 }}>
                      <Typography variant="caption">{p.periodo}</Typography>
                      <Typography variant="caption">
                        {p.ordenes} ord. · {p.examenes} ex.
                      </Typography>
                    </Stack>
                    <Box
                      sx={{
                        height: 8,
                        bgcolor: 'action.hover',
                        borderRadius: 1,
                        overflow: 'hidden',
                        display: 'flex',
                      }}
                    >
                      <Box
                        sx={{
                          width: `${(p.ordenes / maxSerie) * 100}%`,
                          bgcolor: 'primary.main',
                          height: '100%',
                        }}
                      />
                      <Box
                        sx={{
                          width: `${(p.examenes / maxSerie) * 100}%`,
                          bgcolor: 'secondary.main',
                          height: '100%',
                          opacity: 0.7,
                        }}
                      />
                    </Box>
                  </Box>
                ))}
              </Box>
            )}
          </Paper>

          <Paper variant="outlined" sx={{ mb: 2 }}>
            <Tabs
              value={tab}
              onChange={(_, v: TabKey) => setTab(v)}
              variant="scrollable"
              scrollButtons="auto"
            >
              <Tab value="examen" label="Por examen" />
              <Tab value="obra_social" label="Obra social" />
              <Tab value="origen" label="Origen" />
              <Tab value="estado" label="Estado" />
            </Tabs>
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Concepto</TableCell>
                    <TableCell align="right">Cantidad</TableCell>
                    <TableCell align="right">%</TableCell>
                    <TableCell sx={{ minWidth: 120 }}>Distribución</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {tabla.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={4}>
                        <Typography variant="body2" color="text.secondary">
                          Sin datos.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    tabla.map((row) => (
                      <TableRow key={row.key || row.label}>
                        <TableCell>{row.label}</TableCell>
                        <TableCell align="right">{row.cantidad}</TableCell>
                        <TableCell align="right">{row.porcentaje}</TableCell>
                        <TableCell>
                          <Box
                            sx={{
                              height: 6,
                              bgcolor: 'action.hover',
                              borderRadius: 1,
                              overflow: 'hidden',
                            }}
                          >
                            <Box
                              sx={{
                                width: `${(row.cantidad / maxTabla) * 100}%`,
                                bgcolor: 'primary.main',
                                height: '100%',
                              }}
                            />
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
          </Paper>
        </>
      )}
    </Box>
  );
};

export default EstadisticasPage;
