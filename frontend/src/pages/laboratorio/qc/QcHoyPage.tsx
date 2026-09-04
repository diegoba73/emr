import React, { useCallback, useEffect, useState } from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import toast from 'react-hot-toast';
import {
  createCalibracionQc,
  createCorridaQc,
  getTableroIqcHoy,
  type IqcEnsayoHoy,
  type IqcEquipoHoy,
  type IqcNivelHoy,
  type IqcTableroHoy,
} from '../../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeApiErrorMessage, getSafeClinicalActionMessage } from '../../../utils/apiError';

type Semaforo = 'liberado' | 'falta' | 'no_ok' | 'sin_trabajo';

const COLOR: Record<Semaforo, string> = {
  liberado: '#2e7d32',
  falta: '#ed6c02',
  no_ok: '#c62828',
  sin_trabajo: '#616161',
};

const LABEL: Record<Semaforo, string> = {
  liberado: 'Liberado',
  falta: 'Falta control',
  no_ok: 'No OK — calibrar',
  sin_trabajo: 'Sin trabajo',
};

function todayISO(): string {
  const d = new Date();
  const z = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}

function plusDaysISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  const z = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
}

function nowISO(): string {
  return new Date().toISOString();
}

function NivelChip({ nivel, pack }: { nivel: string; pack: IqcNivelHoy | null | undefined }) {
  const est = pack?.estado || 'falta';
  const color =
    est === 'aceptada' ? 'success' : est === 'rechazada' ? 'error' : est === 'pendiente' ? 'warning' : 'default';
  const txt = est === 'aceptada' ? 'OK' : est === 'rechazada' ? 'No OK' : 'Falta';
  return <Chip size="small" color={color} variant={est === 'falta' ? 'outlined' : 'filled'} label={`${nivel} ${txt}`} />;
}

const QcHoyPage: React.FC = () => {
  const [board, setBoard] = useState<IqcTableroHoy | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notaCal, setNotaCal] = useState<Record<number, string>>({});
  const [valorEnsayo, setValorEnsayo] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setBoard(await getTableroIqcHoy());
    } catch (e) {
      toast.error(
        getSafeApiErrorMessage(
          e,
          'No se pudo cargar el tablero de hoy. Si acabás de actualizar, reiniciá el backend.'
        )
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const registrarNivel = async (opts: {
    lote_producto?: number | null;
    lote_control?: number | null;
    nivel: 'N1' | 'N2';
    equipo: number;
    ok: boolean;
    valor?: string;
  }) => {
    if (opts.lote_producto && opts.lote_control) return;
    if (!opts.lote_producto && !opts.lote_control) {
      toast.error('Falta lote de control. Cargalo en Catálogo / lotes.');
      return;
    }
    setSaving(true);
    try {
      const modo = opts.ok
        ? opts.valor?.trim()
          ? 'VALORES'
          : 'ACEPTAR_NIVEL'
        : 'RECHAZAR_NIVEL';
      await createCorridaQc({
        lote_producto: opts.lote_producto || null,
        lote_control: opts.lote_control || null,
        nivel: opts.nivel,
        equipo: opts.equipo,
        fecha: nowISO(),
        modo,
        valor: opts.valor?.trim() ? Number(opts.valor.replace(',', '.')) : undefined,
        observaciones: opts.ok ? 'control OK' : 'control no OK',
      });
      toast.success(opts.ok ? `Control ${opts.nivel === 'N1' ? 'S1' : 'S2'} OK` : 'Control no OK registrado');
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsRegistrarCorridaQc));
    } finally {
      setSaving(false);
    }
  };

  const calibrar = async (eq: IqcEquipoHoy, tipoExamen?: number) => {
    setSaving(true);
    try {
      await createCalibracionQc({
        equipo: eq.id,
        fecha: todayISO(),
        vigente_hasta: plusDaysISO(1),
        calibrador_nombre: 'Recalibración',
        tipo: 'PUNTO_UNICO',
        tipo_examen: tipoExamen ?? null,
        observaciones: (notaCal[eq.id] || '').trim() || 'recalibración por control fuera',
      });
      toast.success('Calibración registrada. Repetí el control.');
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsQcCatalogo));
    } finally {
      setSaving(false);
    }
  };

  const siguienteNivel = (s1?: IqcNivelHoy | null, s2?: IqcNivelHoy | null): 'N1' | 'N2' =>
    s1?.estado === 'aceptada' ? 'N2' : 'N1';

  const accionesMultiparam = (eq: IqcEquipoHoy) => {
    const nivel = siguienteNivel(eq.s1, eq.s2);
    const pack = nivel === 'N1' ? eq.s1 : eq.s2;
    const loteId = eq.lote_producto_id || pack?.lote_producto_id;
    const tag = nivel === 'N1' ? 'S1' : 'S2';
    return (
      <Stack spacing={1.5}>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <NivelChip nivel="S1" pack={eq.s1} />
          <NivelChip nivel="S2" pack={eq.s2} />
          {eq.lote_codigo && (
            <Chip size="small" variant="outlined" label={`Lote ${eq.lote_codigo}`} />
          )}
        </Stack>
        {eq.estado !== 'liberado' && loteId && (
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <Button
              size="large"
              variant="contained"
              color="success"
              disabled={saving}
              onClick={() =>
                void registrarNivel({
                  lote_producto: loteId,
                  nivel,
                  equipo: eq.id,
                  ok: true,
                })
              }
              sx={{ flex: 1, py: 1.5, fontSize: '1.05rem', fontWeight: 700 }}
            >
              Control {tag} OK
            </Button>
            <Button
              size="large"
              variant="contained"
              color="error"
              disabled={saving}
              onClick={() =>
                void registrarNivel({
                  lote_producto: loteId,
                  nivel,
                  equipo: eq.id,
                  ok: false,
                })
              }
              sx={{ flex: 1, py: 1.5, fontSize: '1.05rem', fontWeight: 700 }}
            >
              Control {tag} no OK
            </Button>
          </Stack>
        )}
        {eq.estado === 'no_ok' && (
          <CalibrarBloque
            eq={eq}
            nota={notaCal[eq.id] || ''}
            onNota={(v) => setNotaCal((p) => ({ ...p, [eq.id]: v }))}
            onCalibrar={() => void calibrar(eq)}
            saving={saving}
          />
        )}
      </Stack>
    );
  };

  const filaEnsayo = (eq: IqcEquipoHoy, fila: IqcEnsayoHoy) => {
    const nivel = siguienteNivel(fila.s1, fila.s2);
    const pack = nivel === 'N1' ? fila.s1 : fila.s2;
    const loteId = pack?.lote_control_id;
    const tag = nivel === 'N1' ? 'S1' : 'S2';
    const vKey = `${eq.id}-${fila.tipo_examen}-${nivel}`;
    return (
      <Box
        key={fila.tipo_examen}
        sx={{
          border: '1px solid',
          borderColor: 'divider',
          borderLeft: `6px solid ${COLOR[fila.estado]}`,
          borderRadius: 1,
          p: 1.5,
          bgcolor: fila.pedido_hoy ? 'action.hover' : 'transparent',
        }}
      >
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} alignItems={{ md: 'center' }}>
          <Box sx={{ minWidth: 160, flex: 1 }}>
            <Typography fontWeight={700}>
              {fila.codigo}
              {fila.pedido_hoy ? ' · pedido hoy' : ''}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {fila.nombre} — {fila.resumen}
            </Typography>
          </Box>
          <Stack direction="row" spacing={0.5}>
            <NivelChip nivel="S1" pack={fila.s1} />
            <NivelChip nivel="S2" pack={fila.s2} />
          </Stack>
          {fila.estado !== 'liberado' && loteId && (
            <Stack direction="row" spacing={1}>
              <Button
                variant="contained"
                color="success"
                disabled={saving}
                onClick={() =>
                  void registrarNivel({
                    lote_control: loteId,
                    nivel,
                    equipo: eq.id,
                    ok: true,
                    valor: valorEnsayo[vKey],
                  })
                }
              >
                {tag} OK
              </Button>
              <Button
                variant="contained"
                color="error"
                disabled={saving}
                onClick={() =>
                  void registrarNivel({
                    lote_control: loteId,
                    nivel,
                    equipo: eq.id,
                    ok: false,
                  })
                }
              >
                {tag} no OK
              </Button>
            </Stack>
          )}
        </Stack>
        {fila.estado === 'no_ok' && (
          <CalibrarBloque
            eq={eq}
            nota={notaCal[eq.id] || ''}
            onNota={(v) => setNotaCal((p) => ({ ...p, [eq.id]: v }))}
            onCalibrar={() => void calibrar(eq, fila.tipo_examen)}
            saving={saving}
          />
        )}
        {fila.estado !== 'liberado' && loteId && (
          <Accordion disableGutters elevation={0} sx={{ bgcolor: 'transparent', mt: 0.5 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 0, minHeight: 36 }}>
              <Typography variant="body2">Cargar valor del aparato (opcional)</Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ px: 0 }}>
              <TextField
                size="small"
                label={`Valor ${tag}`}
                type="number"
                value={valorEnsayo[vKey] || ''}
                onChange={(e) => setValorEnsayo((p) => ({ ...p, [vKey]: e.target.value }))}
                sx={{ width: 160 }}
              />
            </AccordionDetails>
          </Accordion>
        )}
      </Box>
    );
  };

  if (loading && !board) {
    return <CircularProgress size={28} />;
  }

  const equipos = (board?.equipos || []).filter((e) => e.codigo !== 'ANALIZADOR-DEMO');

  return (
    <Box>
      <Typography variant="h5" fontWeight={800} gutterBottom>
        Hoy — controles de la mañana
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 2, maxWidth: 720 }}>
        Largá los controles <strong>antes</strong> de ensayar. Verde = liberado. Ámbar = falta S1 o S2. Rojo =
        no OK: calibrá y repetí el control.
      </Typography>
      {board && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
          {board.fecha}
        </Typography>
      )}
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
          gap: 2,
        }}
      >
        {equipos.map((eq) => (
          <Box
            key={eq.id}
            sx={{
              borderRadius: 2,
              overflow: 'hidden',
              border: '1px solid',
              borderColor: 'divider',
              bgcolor: 'background.paper',
            }}
          >
            <Box sx={{ bgcolor: COLOR[eq.estado], color: '#fff', px: 2, py: 1.5 }}>
              <Typography variant="h6" fontWeight={800} sx={{ lineHeight: 1.2 }}>
                {eq.codigo} — {LABEL[eq.estado]}
              </Typography>
              <Typography variant="body2" sx={{ opacity: 0.95 }}>
                {eq.nombre} · {eq.resumen}
              </Typography>
            </Box>
            <Box sx={{ p: 2 }}>
              {eq.modo === 'MULTIPARAM' ? (
                <>
                  {accionesMultiparam(eq)}
                  {eq.ensayos_hoy.length > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="subtitle2" gutterBottom>
                        Ensayos de hoy
                      </Typography>
                      <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
                        {eq.ensayos_hoy.map((ex) => (
                          <Chip
                            key={ex.id}
                            label={ex.codigo}
                            size="small"
                            color={ex.liberado ? 'success' : 'default'}
                            variant={ex.liberado ? 'filled' : 'outlined'}
                            title={ex.liberado ? 'Liberado' : ex.razon || 'No liberado'}
                          />
                        ))}
                      </Stack>
                      {!eq.ensayos_hoy[0]?.liberado && eq.estado !== 'liberado' && (
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                          {eq.resumen}. Cuando S1 y S2 estén OK, todos estos ensayos se liberan juntos.
                        </Typography>
                      )}
                    </Box>
                  )}
                  {eq.ensayos_hoy.length === 0 && eq.tiene_trabajo && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                      Sin órdenes en curso. Igual podés liberar el equipo para el día.
                    </Typography>
                  )}
                  <Accordion disableGutters elevation={0} sx={{ bgcolor: 'transparent', mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 0, minHeight: 36 }}>
                      <Typography variant="body2">Cargar valores del aparato (opcional)</Typography>
                    </AccordionSummary>
                    <AccordionDetails sx={{ px: 0 }}>
                      <Typography variant="body2" color="text.secondary">
                        El día a día es Control OK / no OK. Si querés Westgard con números por ensayo, usá
                        Catálogo / lotes → Corridas.
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                </>
              ) : (
                <Stack spacing={1.25}>
                  {eq.ensayos.length === 0 && (
                    <Alert severity="info">No hay materiales de ensayo. Cargalos en Catálogo / lotes.</Alert>
                  )}
                  {eq.ensayos.map((fila) => filaEnsayo(eq, fila))}
                </Stack>
              )}
              {eq.calibracion_hoy && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
                  Calibración hoy: {eq.calibracion_hoy.observaciones || eq.calibracion_hoy.fecha}
                </Typography>
              )}
              {!eq.tiene_trabajo && eq.modo === 'MULTIPARAM' && (
                <Alert severity="warning" sx={{ mt: 1 }}>
                  Falta producto o lote de control. Configuralo en Catálogo / lotes.
                </Alert>
              )}
            </Box>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

function CalibrarBloque({
  eq,
  nota,
  onNota,
  onCalibrar,
  saving,
}: {
  eq: IqcEquipoHoy;
  nota: string;
  onNota: (v: string) => void;
  onCalibrar: () => void;
  saving: boolean;
}) {
  return (
    <Alert severity="error" sx={{ mt: 1 }}>
      <Typography fontWeight={700} gutterBottom>
        Calibrá {eq.codigo} y repetí el control
      </Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems="center">
        <TextField
          size="small"
          label="Nota (opcional)"
          value={nota}
          onChange={(e) => onNota(e.target.value)}
          sx={{ flex: 1, minWidth: 200 }}
        />
        <Button variant="outlined" color="inherit" disabled={saving} onClick={onCalibrar}>
          Calibré
        </Button>
      </Stack>
    </Alert>
  );
}

export default QcHoyPage;
