import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  FormControl,
  FormControlLabel,
  FormGroup,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import {
  accionLlegada,
  checkinTurnoRecepcion,
  getCoberturaHoy,
  getTableroRecepcion,
  listPuestosRecepcion,
  moverPuestoLlegada,
  putCoberturaHoy,
} from '../services/recepcionApi';
import type {
  CoberturaHoyPayload,
  LlegadaRecepcion,
  PuestoRecepcion,
  TableroRecepcion,
  TurnoPendienteCheckin,
} from '../types/recepcion';
import { getSafeClinicalActionMessage } from '../utils/apiError';
import { useData } from '../contexts/DataContext';
import { normalizeRol } from '../utils/permissions';
import { apiService } from '../services/api';
import AtencionDetailDrawer from '../modules/atenciones/components/AtencionDetailDrawer';

const ESTADO_COLOR: Record<string, 'default' | 'info' | 'warning' | 'success' | 'error' | 'primary'> =
  {
    EN_ESPERA_RECEPCION: 'warning',
    EN_ESPERA: 'info',
    LLAMADO: 'primary',
    EN_ATENCION: 'success',
    ATENDIDO: 'default',
    NO_ASISTIO: 'error',
    PROGRAMADO: 'default',
  };

const TIPO_LABEL: Record<string, string> = {
  CONSULTA: 'Consulta',
  ESTUDIO: 'Estudio',
  PROCEDIMIENTO: 'Procedimiento',
  CIRUGIA: 'Cirugía',
  EXTRACCION: 'Extracción',
  SIN_TURNO: 'Sin turno',
};

const PRIORIDAD_CHIP: Record<
  string,
  {
    color: 'success' | 'info' | 'warning' | 'default';
    label: (p: NonNullable<LlegadaRecepcion['prioridad']>) => string;
  }
> = {
  EN_HORARIO: {
    color: 'success',
    label: (p) => `★ Prioridad ${p.hora_turno || ''}`.trim(),
  },
  ANTICIPADO: {
    color: 'info',
    label: (p) => `Turno ${p.hora_turno || ''}`.trim(),
  },
  TARDE: {
    color: 'warning',
    label: (p) => `Tarde ${p.hora_turno || ''}`.trim(),
  },
  SIN_TURNO: {
    color: 'default',
    label: () => 'Sin turno',
  },
};

function fechaHoyLocal(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

const TIPO_CHIP_COBERTURA: { value: string; label: string }[] = [
  { value: 'CONSULTA', label: 'T' },
  { value: 'SIN_TURNO', label: 'S' },
  { value: 'ESTUDIO', label: 'E' },
  { value: 'PROCEDIMIENTO', label: 'P' },
  { value: 'CIRUGIA', label: 'Cirugía' },
];

/** Registro en recepción hecho + turno con médico → el llamado es del médico, no de secretaría. */
function esColaDelMedico(l: LlegadaRecepcion): boolean {
  if (!l.turno || !l.medico_nombre) return false;
  if (['EN_ESPERA', 'EN_ATENCION'].includes(l.estado_flujo)) return true;
  return l.estado_flujo === 'LLAMADO' && (l.zona_llamado || '') === 'MEDICO';
}

function sortLlegadas(rows: LlegadaRecepcion[]): LlegadaRecepcion[] {
  const prioridadOrden: Record<string, number> = {
    EN_HORARIO: 0,
    TARDE: 1,
    ANTICIPADO: 2,
    SIN_TURNO: 3,
  };
  return [...rows].sort((a, b) => {
    const pa = prioridadOrden[a.prioridad?.codigo || 'SIN_TURNO'] ?? 9;
    const pb = prioridadOrden[b.prioridad?.codigo || 'SIN_TURNO'] ?? 9;
    if (pa !== pb) return pa - pb;
    const ta = a.turno_inicio ? new Date(a.turno_inicio).getTime() : Number.MAX_SAFE_INTEGER;
    const tb = b.turno_inicio ? new Date(b.turno_inicio).getTime() : Number.MAX_SAFE_INTEGER;
    return ta - tb;
  });
}

const RecepcionTablero: React.FC = () => {
  const { currentUser } = useData();
  const rol = normalizeRol(currentUser);
  const soyMedico = rol === 'medico';
  const soyLab = rol === 'laboratorio' || rol === 'secretaria_lab' || rol === 'bioquimico';
  const soySecretaria = !soyMedico && !soyLab;
  const [puestos, setPuestos] = useState<PuestoRecepcion[]>([]);
  const [puestoId, setPuestoId] = useState<number | ''>('');
  const [tablero, setTablero] = useState<TableroRecepcion | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | string | null>(null);
  const [atencionId, setAtencionId] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [filtroTipo, setFiltroTipo] = useState<string>('TODOS');
  const [coberturaPayload, setCoberturaPayload] = useState<CoberturaHoyPayload | null>(null);
  const [covPuestoId, setCovPuestoId] = useState<number | ''>('');
  const [covTipos, setCovTipos] = useState<string[]>([]);
  const [savingCobertura, setSavingCobertura] = useState(false);
  const fecha = fechaHoyLocal();

  const loadCobertura = useCallback(async () => {
    if (!soySecretaria) return;
    try {
      const data = await getCoberturaHoy();
      setCoberturaPayload(data);
      setPuestos(data.puestos_disponibles || []);
      if (data.cobertura) {
        setCovPuestoId(data.cobertura.puesto);
        setCovTipos(data.cobertura.tipos || []);
        setPuestoId(data.cobertura.puesto);
      } else {
        setCovPuestoId('');
        setCovTipos([]);
      }
    } catch {
      setCoberturaPayload(null);
    }
  }, [soySecretaria]);

  const load = useCallback(async () => {
    setError(null);
    try {
      const data = await getTableroRecepcion(fecha, soySecretaria ? null : puestoId || null);
      setTablero(data);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo cargar el tablero.'));
    } finally {
      setLoading(false);
    }
  }, [fecha, puestoId, soySecretaria]);

  useEffect(() => {
    if (soySecretaria) {
      void loadCobertura();
      return;
    }
    listPuestosRecepcion()
      .then((rows) => {
        const activos = rows.filter((p) => p.activo);
        if (soyLab) {
          const sala = activos.filter(
            (p) =>
              p.codigo === 'sala-extraccion' ||
              (p.label_publico || p.nombre || '').toLowerCase().includes('extracci')
          );
          setPuestos(sala.length ? sala : activos);
          if (sala[0]) setPuestoId(sala[0].id);
        } else {
          setPuestos(activos);
        }
      })
      .catch(() => setPuestos([]));
  }, [soyLab, soySecretaria, loadCobertura]);

  useEffect(() => {
    setLoading(true);
    void load();
    const id = window.setInterval(() => void load(), 15000);
    return () => window.clearInterval(id);
  }, [load]);

  const puestoActual = useMemo(
    () => puestos.find((p) => p.id === (covPuestoId || puestoId)) || null,
    [puestos, puestoId, covPuestoId]
  );

  const tieneCobertura = Boolean(coberturaPayload?.cobertura);
  const tiposCoberturaLabel = (coberturaPayload?.cobertura?.tipos || [])
    .map((t) => TIPO_CHIP_COBERTURA.find((x) => x.value === t)?.label || t)
    .join(' ');

  const guardarCobertura = async () => {
    if (!covPuestoId || covTipos.length === 0) {
      setError('Elegí puesto y al menos un tipo (T/S/E/P) para tu cobertura de hoy.');
      return;
    }
    setSavingCobertura(true);
    setError(null);
    try {
      await putCoberturaHoy({ puesto: Number(covPuestoId), tipos: covTipos });
      await loadCobertura();
      await load();
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo guardar la cobertura.'));
    } finally {
      setSavingCobertura(false);
    }
  };

  const toggleTipoCobertura = (tipo: string) => {
    setCovTipos((prev) =>
      prev.includes(tipo) ? prev.filter((t) => t !== tipo) : [...prev, tipo]
    );
  };

  const onCheckin = async (t: TurnoPendienteCheckin) => {
    setBusyId(`t-${t.turno_id}`);
    try {
      await checkinTurnoRecepcion(t.turno_id, puestoId || t.puesto_sugerido_id);
      await load();
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo registrar la llegada.'));
    } finally {
      setBusyId(null);
    }
  };

  const abrirConsulta = async (l: LlegadaRecepcion) => {
    if (!l.turno) {
      throw new Error('Esta llegada no tiene turno; no se puede abrir la consulta.');
    }
    const result = await apiService.iniciarAtencionTurno(l.turno);
    const id = result.atencion?.id;
    if (!id) throw new Error('No se obtuvo la atención clínica del turno.');
    setAtencionId(id);
    setDrawerOpen(true);
  };

  const onAccion = async (
    l: LlegadaRecepcion,
    accion: 'llamar' | 'derivar-espera' | 'en-atencion' | 'atendido' | 'no-asistio'
  ) => {
    setBusyId(l.id);
    try {
      if (accion === 'en-atencion' && soyMedico) {
        if (l.estado_flujo !== 'EN_ATENCION') {
          await accionLlegada(l.id, 'en-atencion');
        }
        await abrirConsulta(l);
        await load();
        return;
      }
      await accionLlegada(l.id, accion);
      await load();
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo completar la acción.'));
    } finally {
      setBusyId(null);
    }
  };

  const onMover = async (l: LlegadaRecepcion, nuevoPuesto: number) => {
    setBusyId(l.id);
    try {
      await moverPuestoLlegada(l.id, nuevoPuesto);
      await load();
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo mover de puesto.'));
    } finally {
      setBusyId(null);
    }
  };

  const llegadas = sortLlegadas(tablero?.llegadas || []);
  const pendientes = tablero?.turnos_pendientes_checkin || [];
  const enCursoAll = llegadas.filter((l) => {
    if (soyMedico) {
      // Solo tras registro de secretaría (cola clínica / llamado a consultorio).
      if (['EN_ESPERA', 'EN_ATENCION'].includes(l.estado_flujo)) return true;
      return l.estado_flujo === 'LLAMADO' && (l.zona_llamado || '') === 'MEDICO';
    }
    return ['EN_ESPERA_RECEPCION', 'EN_ESPERA', 'LLAMADO', 'EN_ATENCION'].includes(
      l.estado_flujo
    );
  });
  const enCurso =
    filtroTipo === 'TODOS'
      ? enCursoAll
      : filtroTipo === 'PROCEDIMIENTO'
        ? enCursoAll.filter((l) =>
            l.tipo_actividad === 'PROCEDIMIENTO' || l.tipo_actividad === 'CIRUGIA'
          )
        : enCursoAll.filter((l) => l.tipo_actividad === filtroTipo);
  const atendidos = llegadas.filter((l) => l.estado_flujo === 'ATENDIDO');

  const contadoresTipo = useMemo(() => {
    const keys = ['CONSULTA', 'SIN_TURNO', 'ESTUDIO', 'PROCEDIMIENTO', 'CIRUGIA', 'EXTRACCION'] as const;
    const map: Record<string, number> = {};
    for (const k of keys) map[k] = 0;
    for (const l of enCursoAll) {
      if (l.tipo_actividad && map[l.tipo_actividad] != null) map[l.tipo_actividad] += 1;
    }
    // Prefijos turnero: T≈CONSULTA con turno, S=SIN_TURNO, E, P=PROC+CIR, L
    return {
      T: map.CONSULTA || 0,
      S: map.SIN_TURNO || 0,
      E: map.ESTUDIO || 0,
      P: (map.PROCEDIMIENTO || 0) + (map.CIRUGIA || 0),
      L: map.EXTRACCION || 0,
      total: enCursoAll.length,
    };
  }, [enCursoAll]);

  const renderAccionesLlegada = (l: LlegadaRecepcion) => {
    const busy = busyId === l.id;
    if (l.estado_flujo === 'ATENDIDO') {
      return soyMedico && l.turno ? (
        <Button
          size="small"
          disabled={busy}
          onClick={() => {
            setBusyId(l.id);
            void abrirConsulta(l)
              .then(() => load())
              .catch((e) =>
                setError(getSafeClinicalActionMessage(e, 'No se pudo abrir la consulta.'))
              )
              .finally(() => setBusyId(null));
          }}
        >
          Ver consulta
        </Button>
      ) : (
        <Typography variant="caption" color="text.secondary">
          Consulta guardada
        </Typography>
      );
    }

    if (esColaDelMedico(l) && !soyMedico) {
      return (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, justifyContent: 'flex-end' }}>
          <Typography variant="caption" color="text.secondary" sx={{ maxWidth: 160 }}>
            En cola del médico
          </Typography>
          <Button
            size="small"
            color="error"
            disabled={busy}
            onClick={() => void onAccion(l, 'no-asistio')}
          >
            No asistió
          </Button>
        </Box>
      );
    }

    return (
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, justifyContent: 'flex-end' }}>
        {l.estado_flujo === 'EN_ESPERA_RECEPCION' && soySecretaria && l.turno && (
          <Button
            size="small"
            variant="outlined"
            disabled={busy}
            onClick={() => void onAccion(l, 'derivar-espera')}
          >
            Pasar a médico
          </Button>
        )}
        {((soyMedico &&
          (l.estado_flujo === 'EN_ESPERA' ||
            (l.estado_flujo === 'LLAMADO' && (l.zona_llamado || '') === 'MEDICO'))) ||
          (soyLab &&
            ['EN_ESPERA_RECEPCION', 'EN_ESPERA', 'LLAMADO'].includes(l.estado_flujo)) ||
          (soySecretaria &&
            l.tipo_actividad !== 'EXTRACCION' &&
            ['EN_ESPERA_RECEPCION', 'LLAMADO'].includes(l.estado_flujo) &&
            !esColaDelMedico(l))) && (
          <Button
            size="small"
            variant="contained"
            color="primary"
            disabled={busy || (soySecretaria && !tieneCobertura)}
            onClick={() => void onAccion(l, 'llamar')}
          >
            {l.estado_flujo === 'LLAMADO' ? 'Rellamar' : 'Llamar'}
          </Button>
        )}
        {(l.estado_flujo === 'LLAMADO' || l.estado_flujo === 'EN_ATENCION') && (
          <Button
            size="small"
            variant={soyMedico ? 'contained' : 'outlined'}
            disabled={busy}
            onClick={() => void onAccion(l, 'en-atencion')}
          >
            {soyMedico
              ? l.estado_flujo === 'EN_ATENCION'
                ? 'Abrir consulta'
                : 'En atención'
              : 'En atención'}
          </Button>
        )}
        {(soyLab || soySecretaria) && ['LLAMADO', 'EN_ATENCION'].includes(l.estado_flujo) && (
          <Button
            size="small"
            color="success"
            disabled={busy}
            onClick={() => void onAccion(l, 'atendido')}
          >
            Atendido
          </Button>
        )}
        <Button
          size="small"
          color="error"
          disabled={busy}
          onClick={() => void onAccion(l, 'no-asistio')}
        >
          No asistió
        </Button>
      </Box>
    );
  };

  const renderTablaEnCurso = (rows: LlegadaRecepcion[]) => (
    <TableContainer component={Paper} sx={{ mb: 3 }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>#</TableCell>
            <TableCell>Paciente</TableCell>
            <TableCell>Tipo</TableCell>
            <TableCell>Horario</TableCell>
            <TableCell>Médico / destino</TableCell>
            <TableCell>Estado</TableCell>
            {!soyMedico && <TableCell>Puesto</TableCell>}
            <TableCell align="right">Acciones</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={soyMedico ? 7 : 8}>
                <Typography color="text.secondary">Nadie en esta sección todavía.</Typography>
              </TableCell>
            </TableRow>
          ) : (
            rows.map((l) => {
              const pr = l.prioridad;
              const chipCfg = PRIORIDAD_CHIP[pr?.codigo || 'SIN_TURNO'] || PRIORIDAD_CHIP.SIN_TURNO;
              return (
                <TableRow
                  key={l.id}
                  hover
                  selected={l.estado_flujo === 'LLAMADO' || pr?.es_prioridad === true}
                >
                  <TableCell>
                    <Typography fontWeight={800} letterSpacing={0.5}>
                      {l.codigo_llamado || (l.numero_orden_dia != null ? `#${l.numero_orden_dia}` : '—')}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography fontWeight={600}>{l.paciente_nombre}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      DNI {l.paciente_dni || '—'}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip size="small" label={TIPO_LABEL[l.tipo_actividad] || l.tipo_actividad} />
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      color={chipCfg.color}
                      label={pr ? chipCfg.label(pr) : 'Sin turno'}
                      sx={pr?.es_prioridad ? { fontWeight: 700 } : undefined}
                    />
                  </TableCell>
                  <TableCell>
                    {l.medico_nombre || '—'}
                    {(l.destino || l.destino_label) && (
                      <Typography variant="caption" display="block" color="text.secondary">
                        → {l.destino || l.destino_label}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      color={ESTADO_COLOR[l.estado_flujo] || 'default'}
                      label={l.estado_flujo.replace(/_/g, ' ')}
                    />
                  </TableCell>
                  {!soyMedico && (
                    <TableCell>
                      <Select
                        size="small"
                        value={String(l.puesto)}
                        disabled={busyId === l.id || l.estado_flujo === 'ATENDIDO'}
                        onChange={(e) => void onMover(l, Number(e.target.value))}
                        sx={{ minWidth: 140 }}
                      >
                        {puestos.map((p) => (
                          <MenuItem key={p.id} value={String(p.id)}>
                            {p.nombre}
                          </MenuItem>
                        ))}
                      </Select>
                    </TableCell>
                  )}
                  <TableCell align="right">{renderAccionesLlegada(l)}</TableCell>
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <Box sx={{ p: 2 }} data-demo="page-recepcion-tablero">
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" sx={{ fontWeight: 700, flex: 1 }}>
          {soyMedico
            ? 'Recepción — mis pacientes de hoy'
            : soyLab
              ? 'Laboratorio — cola de extracciones (L)'
              : 'Recepción — tablero del día'}
        </Typography>
        {soyLab && (
          <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 600 }}>
            Puesto: Sala de extracción
          </Typography>
        )}
        <Button variant="outlined" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
      </Box>

      {soySecretaria && (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 700 }}>
            Hoy estoy en
            {tieneCobertura && puestoActual
              ? `: ${puestoActual.label_publico || puestoActual.nombre} · Atiendo: ${tiposCoberturaLabel || '—'}`
              : '…'}
          </Typography>
          {!tieneCobertura && (
            <Alert severity="warning" sx={{ mb: 1.5 }}>
              Configurá tu cobertura (puesto + tipos) antes de llamar pacientes.
            </Alert>
          )}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'center' }}>
            <FormControl size="small" sx={{ minWidth: 200 }}>
              <InputLabel>Puesto</InputLabel>
              <Select
                label="Puesto"
                value={covPuestoId === '' ? '' : String(covPuestoId)}
                onChange={(e) =>
                  setCovPuestoId(e.target.value === '' ? '' : Number(e.target.value))
                }
              >
                {(coberturaPayload?.puestos_disponibles || puestos).map((p) => (
                  <MenuItem key={p.id} value={String(p.id)}>
                    {p.label_publico || p.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormGroup row>
              {TIPO_CHIP_COBERTURA.map((t) => (
                <FormControlLabel
                  key={t.value}
                  control={
                    <Checkbox
                      size="small"
                      checked={covTipos.includes(t.value)}
                      onChange={() => toggleTipoCobertura(t.value)}
                    />
                  }
                  label={t.label}
                />
              ))}
            </FormGroup>
            <Button
              variant="contained"
              size="small"
              disabled={savingCobertura}
              onClick={() => void guardarCobertura()}
            >
              Guardar cobertura
            </Button>
          </Box>
        </Paper>
      )}

      <Alert severity="info" sx={{ mb: 2 }}>
        {soyMedico ? (
          <>
            Pacientes ya registrados en recepción (cola médica). <strong>Llamar</strong> avisa en la
            app y en la TV; <strong>En atención</strong> inicia la consulta (o el paciente toca «Ya
            voy»).
          </>
        ) : soyLab ? (
          <>
            Cola <strong>L</strong> → destino fijo <strong>Sala de extracción</strong>.{' '}
            <strong>Llamar</strong> avisa al paciente en la TV; no pasa por secretaría ni por el
            médico.
          </>
        ) : (
          <>
            El paciente se anuncia por QR o app. La cola se filtra por los tipos de tu cobertura.
            Cuando esté OK administrativamente, usá <strong>Pasar a médico</strong> para enviarlo a
            la cola del médico.
          </>
        )}
      </Alert>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {!soyMedico && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2, alignItems: 'center' }}>
          <Typography variant="body2" color="text.secondary" sx={{ mr: 0.5 }}>
            En espera:
          </Typography>
          {(
            [
              { key: 'TODOS', label: `Todos (${contadoresTipo.total})` },
              { key: 'CONSULTA', label: `T ${contadoresTipo.T}` },
              { key: 'SIN_TURNO', label: `S ${contadoresTipo.S}` },
              { key: 'ESTUDIO', label: `E ${contadoresTipo.E}` },
              { key: 'PROCEDIMIENTO', label: `P ${contadoresTipo.P}` },
              { key: 'EXTRACCION', label: `L ${contadoresTipo.L}` },
            ] as const
          )
            .filter((c) => {
              if (soyLab) return c.key === 'TODOS' || c.key === 'EXTRACCION';
              if (soySecretaria) {
                if (c.key === 'EXTRACCION') return false;
                if (c.key === 'TODOS') return true;
                const tipos = coberturaPayload?.cobertura?.tipos || [];
                if (!tipos.length) return true;
                if (c.key === 'PROCEDIMIENTO') {
                  return tipos.includes('PROCEDIMIENTO') || tipos.includes('CIRUGIA');
                }
                return tipos.includes(c.key);
              }
              return true;
            })
            .map((c) => (
              <Chip
                key={c.key}
                size="small"
                label={c.label}
                color={filtroTipo === c.key ? 'primary' : 'default'}
                variant={filtroTipo === c.key ? 'filled' : 'outlined'}
                onClick={() => setFiltroTipo(c.key)}
                sx={{ fontWeight: 700 }}
              />
            ))}
        </Box>
      )}

      {loading && !tablero ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          {/* Extracciones (L): walk-in / orden de llegada — sin turnos de agenda. */}
          {!soyLab && (
            <>
              <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600 }}>
                1. Turnos de hoy sin registro en recepción ({pendientes.length})
              </Typography>
              <TableContainer component={Paper} sx={{ mb: 3 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Hora</TableCell>
                      <TableCell>Paciente</TableCell>
                      <TableCell>Tipo</TableCell>
                      <TableCell>Médico / recurso</TableCell>
                      <TableCell>Puesto sugerido</TableCell>
                      <TableCell align="right">Acción</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {pendientes.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={6}>
                          <Typography color="text.secondary">
                            No hay turnos pendientes de registro.
                          </Typography>
                        </TableCell>
                      </TableRow>
                    ) : (
                      pendientes.map((t) => (
                        <TableRow key={t.turno_id} hover>
                          <TableCell>
                            {new Date(t.inicio).toLocaleTimeString('es-AR', {
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </TableCell>
                          <TableCell>
                            <Typography fontWeight={600}>{t.paciente_nombre}</Typography>
                            <Typography variant="caption">DNI {t.paciente_dni || '—'}</Typography>
                          </TableCell>
                          <TableCell>
                            <Chip
                              size="small"
                              label={TIPO_LABEL[t.tipo_actividad] || t.tipo_actividad}
                            />
                          </TableCell>
                          <TableCell>
                            {t.medico_nombre || '—'}
                            {t.recurso_nombre && (
                              <Typography variant="caption" display="block">
                                {t.recurso_nombre}
                              </Typography>
                            )}
                          </TableCell>
                          <TableCell>{t.puesto_sugerido_label}</TableCell>
                          <TableCell align="right">
                            {soyMedico ? (
                              <Typography variant="caption" color="text.secondary">
                                Esperando registro de recepción
                              </Typography>
                            ) : (
                              <Button
                                size="small"
                                variant="contained"
                                disabled={busyId === `t-${t.turno_id}`}
                                onClick={() => void onCheckin(t)}
                              >
                                Registrar llegada
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          )}

          <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600 }}>
            {soyLab ? '1' : '2'}. En recepción / en curso ({enCurso.length})
          </Typography>
          {renderTablaEnCurso(enCurso)}

          <Typography variant="subtitle1" sx={{ mb: 1, fontWeight: 600 }}>
            {soyLab ? '2' : '3'}. Atendidos — consulta guardada ({atendidos.length})
          </Typography>
          {renderTablaEnCurso(atendidos)}
        </>
      )}

      <AtencionDetailDrawer
        atencionId={atencionId}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setAtencionId(null);
          void load();
        }}
        currentUser={currentUser}
        forceEdit
        initialTab="detalle"
        onIntervencionSaved={async () => {
          await load();
        }}
      />
    </Box>
  );
};

export default RecepcionTablero;
