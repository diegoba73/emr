import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  CircularProgress,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import toast from 'react-hot-toast';
import {
  createCalibracionQc,
  createCorridaQc,
  createEquipoQc,
  createLoteControl,
  createMaterialQc,
  getLeveyJenningsMaterial,
  listCalibracionesQc,
  listCorridasQc,
  listEquiposQc,
  listLotesControl,
  listMaterialesQc,
  listTiposExamenLims,
  type Calibracion,
  type CorridaQC,
  type EquipoAnalizador,
  type LeveyJenningsSeries,
  type LoteControl,
  type MaterialControl,
  type PuntoCurvaCalibracion,
} from '../../../services/limsApi';
import type { LimsTipoExamen } from '../../../types/lims';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../../utils/apiError';

const NIVEL_LABEL: Record<string, string> = {
  N1: 'S1 (normal)',
  N2: 'S2 (patológico)',
  N3: 'Nivel 3',
};

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function plusDaysISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function LjChart({ series }: { series: LeveyJenningsSeries }) {
  const w = 640;
  const h = 220;
  const pad = 30;
  const pts = series.puntos;
  if (!pts.length) {
    return <Typography color="text.secondary">Sin puntos QC.</Typography>;
  }
  const mean = series.media_target;
  const sd = series.de_target || 1;
  const ys = pts.map((p) => p.valor);
  const yMin = Math.min(mean - 3 * sd, ...ys) - sd;
  const yMax = Math.max(mean + 3 * sd, ...ys) + sd;
  const xScale = (i: number) => pad + (i * (w - 2 * pad)) / Math.max(pts.length - 1, 1);
  const yScale = (v: number) => h - pad - ((v - yMin) / (yMax - yMin || 1)) * (h - 2 * pad);
  const line = (mul: number, color: string) => {
    const y = yScale(mean + mul * sd);
    return <line key={mul} x1={pad} x2={w - pad} y1={y} y2={y} stroke={color} strokeDasharray="4 4" />;
  };
  const path = pts
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p.valor)}`)
    .join(' ');

  return (
    <svg width="100%" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Levey-Jennings">
      <rect x={0} y={0} width={w} height={h} fill="transparent" />
      {line(0, '#1976d2')}
      {line(2, '#ed6c02')}
      {line(-2, '#ed6c02')}
      {line(3, '#d32f2f')}
      {line(-3, '#d32f2f')}
      <path d={path} fill="none" stroke="#333" strokeWidth={1.5} />
      {pts.map((p, i) => (
        <circle
          key={p.id}
          cx={xScale(i)}
          cy={yScale(p.valor)}
          r={3.5}
          fill={p.fuera_control ? '#d32f2f' : p.warning ? '#ed6c02' : '#2e7d32'}
        />
      ))}
    </svg>
  );
}

const QcHubPage: React.FC = () => {
  const [tab, setTab] = useState(0);
  const [equipos, setEquipos] = useState<EquipoAnalizador[]>([]);
  const [materiales, setMateriales] = useState<MaterialControl[]>([]);
  const [lotes, setLotes] = useState<LoteControl[]>([]);
  const [corridas, setCorridas] = useState<CorridaQC[]>([]);
  const [cals, setCals] = useState<Calibracion[]>([]);
  const [examenes, setExamenes] = useState<LimsTipoExamen[]>([]);
  const [lj, setLj] = useState<LeveyJenningsSeries | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [formCorrida, setFormCorrida] = useState({ lote_control: '', valor: '', equipo: '' });
  const [formMaterial, setFormMaterial] = useState({
    tipo_examen: '',
    nombre: 'Standatrol S-E',
    marca: 'Wiener',
    producto: 'Standatrol S-E 2 Niveles',
    nivel: 'N1' as 'N1' | 'N2' | 'N3',
    media_target: '100',
    de_target: '5',
  });
  const [formLote, setFormLote] = useState({
    material: '',
    codigo_lote: '',
    vencimiento: plusDaysISO(365),
  });
  const [formEquipo, setFormEquipo] = useState({
    codigo: 'CM260',
    nombre: 'Autoanalizador CM260',
    marca_modelo: 'CM260',
    activo: true,
  });
  const [formCal, setFormCal] = useState({
    equipo: '',
    tipo_examen: '',
    fecha: todayISO(),
    vigente_hasta: plusDaysISO(30),
    calibrador_nombre: 'Calibrador A Plus',
    marca: 'Wiener',
    codigo_lote: '',
    tipo: 'PUNTO_UNICO' as 'PUNTO_UNICO' | 'CURVA_MULTIPUNTO',
    observaciones: '',
  });
  const [puntosCurva, setPuntosCurva] = useState<PuntoCurvaCalibracion[]>([
    { orden: 1, concentracion: '', senal: '', unidad: 'mg/L' },
    { orden: 2, concentracion: '', senal: '', unidad: 'mg/L' },
  ]);

  const materialById = useMemo(() => {
    const map = new Map<number, MaterialControl>();
    for (const m of materiales) map.set(m.id, m);
    return map;
  }, [materiales]);

  const lotesActivos = useMemo(() => lotes.filter((l) => l.activo), [lotes]);

  const examenesOrdenados = useMemo(
    () => [...examenes].sort((a, b) => a.codigo.localeCompare(b.codigo)),
    [examenes]
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [e, m, l, c, cal, ex] = await Promise.all([
        listEquiposQc(),
        listMaterialesQc(),
        listLotesControl(),
        listCorridasQc(),
        listCalibracionesQc(),
        listTiposExamenLims({ activo: true }),
      ]);
      setEquipos(e);
      setMateriales(m);
      setLotes(l);
      setCorridas(c);
      setCals(cal);
      setExamenes(ex);
      const activos = l.filter((x) => x.activo);
      setFormCorrida((prev) => ({
        ...prev,
        lote_control: prev.lote_control || (activos[0] ? String(activos[0].id) : ''),
        equipo: prev.equipo || (e[0] ? String(e[0].id) : ''),
      }));
      setFormLote((prev) => ({
        ...prev,
        material: prev.material || (m[0] ? String(m[0].id) : ''),
      }));
      setFormCal((prev) => ({
        ...prev,
        equipo: prev.equipo || (e[0] ? String(e[0].id) : ''),
      }));
      setFormMaterial((prev) => ({
        ...prev,
        tipo_examen: prev.tipo_examen || (ex[0] ? String(ex[0].id) : ''),
      }));
      if (m[0]) {
        setLj(await getLeveyJenningsMaterial(m[0].id));
      }
    } catch (err) {
      toast.error(getSafeClinicalActionMessage(err, CLINICAL_ACTION_ERRORS.genericClinicalAction));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const submitCorrida = async () => {
    const loteId = Number(formCorrida.lote_control);
    if (!loteId || Number.isNaN(loteId)) {
      toast.error('Seleccioná un lote de control.');
      return;
    }
    if (!formCorrida.valor.trim() || Number.isNaN(Number(formCorrida.valor))) {
      toast.error('Ingresá el valor medido del control.');
      return;
    }
    setSaving(true);
    try {
      await createCorridaQc({
        lote_control: loteId,
        equipo: formCorrida.equipo ? Number(formCorrida.equipo) : null,
        fecha: new Date().toISOString(),
        valor: Number(formCorrida.valor),
      });
      toast.success('Corrida registrada');
      setFormCorrida((p) => ({ ...p, valor: '' }));
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsRegistrarCorridaQc));
    } finally {
      setSaving(false);
    }
  };

  const submitMaterial = async () => {
    if (!formMaterial.tipo_examen) {
      toast.error('Seleccioná el examen.');
      return;
    }
    setSaving(true);
    try {
      const exam = examenes.find((x) => x.id === Number(formMaterial.tipo_examen));
      const nombre =
        formMaterial.nombre.trim() ||
        `${formMaterial.producto || 'Control'} ${exam?.codigo || ''} ${NIVEL_LABEL[formMaterial.nivel]}`;
      await createMaterialQc({
        nombre,
        tipo_examen: Number(formMaterial.tipo_examen),
        nivel: formMaterial.nivel,
        media_target: formMaterial.media_target,
        de_target: formMaterial.de_target,
        marca: formMaterial.marca,
        producto: formMaterial.producto,
        activo: true,
      });
      toast.success('Material creado');
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsQcCatalogo));
    } finally {
      setSaving(false);
    }
  };

  const submitLote = async () => {
    if (!formLote.material || !formLote.codigo_lote.trim() || !formLote.vencimiento) {
      toast.error('Completá material, código de lote y vencimiento.');
      return;
    }
    setSaving(true);
    try {
      await createLoteControl({
        material: Number(formLote.material),
        codigo_lote: formLote.codigo_lote.trim(),
        vencimiento: formLote.vencimiento,
        activo: true,
      });
      toast.success('Lote creado');
      setFormLote((p) => ({ ...p, codigo_lote: '' }));
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsQcCatalogo));
    } finally {
      setSaving(false);
    }
  };

  const submitEquipo = async () => {
    if (!formEquipo.codigo.trim() || !formEquipo.nombre.trim()) {
      toast.error('Código y nombre del equipo son obligatorios.');
      return;
    }
    setSaving(true);
    try {
      await createEquipoQc({
        codigo: formEquipo.codigo.trim(),
        nombre: formEquipo.nombre.trim(),
        marca_modelo: formEquipo.marca_modelo.trim(),
        activo: formEquipo.activo,
      });
      toast.success('Equipo creado');
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsQcCatalogo));
    } finally {
      setSaving(false);
    }
  };

  const submitCalibracion = async () => {
    if (!formCal.equipo) {
      toast.error('Seleccioná el equipo.');
      return;
    }
    if (formCal.tipo === 'CURVA_MULTIPUNTO' && !formCal.tipo_examen) {
      toast.error('La curva multipunto requiere técnica (PCR / PCR-us).');
      return;
    }
    const puntos =
      formCal.tipo === 'CURVA_MULTIPUNTO'
        ? puntosCurva
            .map((p, i) => ({
              orden: i + 1,
              concentracion: String(p.concentracion).trim(),
              senal: String(p.senal ?? '').trim(),
              unidad: p.unidad || 'mg/L',
            }))
            .filter((p) => p.concentracion)
        : [];
    if (formCal.tipo === 'CURVA_MULTIPUNTO' && puntos.length < 2) {
      toast.error('Ingresá al menos 2 puntos de la curva.');
      return;
    }
    setSaving(true);
    try {
      await createCalibracionQc({
        equipo: Number(formCal.equipo),
        fecha: formCal.fecha,
        vigente_hasta: formCal.vigente_hasta,
        calibrador_nombre: formCal.calibrador_nombre,
        marca: formCal.marca,
        codigo_lote: formCal.codigo_lote,
        tipo: formCal.tipo,
        tipo_examen: formCal.tipo_examen ? Number(formCal.tipo_examen) : null,
        puntos_curva: puntos,
        observaciones: formCal.observaciones,
      });
      toast.success('Calibración registrada');
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsQcCatalogo));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" fontWeight={700} gutterBottom>
        Control de calidad (Westgard)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Química CM260: Standatrol S-E (S1/S2) + Calibrador A Plus. PCR / PCR-us: curva de aglutinación
        multipunto.
      </Typography>
      <Tabs value={tab} onChange={(_e, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Levey-Jennings" />
        <Tab label="Corridas" />
        <Tab label="Materiales / Lotes" />
        <Tab label="Equipos / Calibraciones" />
      </Tabs>
      {loading && <CircularProgress size={24} />}

      {tab === 0 && (
        <Box>
          <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap">
            {materiales.map((m) => (
              <Button
                key={m.id}
                size="small"
                variant={lj?.material_id === m.id ? 'contained' : 'outlined'}
                onClick={async () => setLj(await getLeveyJenningsMaterial(m.id))}
              >
                {m.tipo_examen_codigo} {NIVEL_LABEL[m.nivel] || m.nivel}
              </Button>
            ))}
          </Stack>
          {lj && <LjChart series={lj} />}
        </Box>
      )}

      {tab === 1 && (
        <Box>
          {!lotesActivos.length && !loading && (
            <Typography color="warning.main" sx={{ mb: 2 }}>
              No hay lotes activos. Creá material y lote en la pestaña Materiales / Lotes, o ejecutá{' '}
              <code>seed_qc_demo</code>.
            </Typography>
          )}
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }} alignItems="flex-start">
            <FormControl size="small" sx={{ minWidth: 280 }}>
              <InputLabel id="qc-lote-label">Lote de control</InputLabel>
              <Select
                labelId="qc-lote-label"
                label="Lote de control"
                value={formCorrida.lote_control}
                onChange={(e) => setFormCorrida((p) => ({ ...p, lote_control: String(e.target.value) }))}
              >
                {lotesActivos.map((l) => {
                  const mat = materialById.get(l.material);
                  const exam = mat
                    ? `${mat.tipo_examen_codigo} ${NIVEL_LABEL[mat.nivel] || mat.nivel}`
                    : `mat #${l.material}`;
                  return (
                    <MenuItem key={l.id} value={String(l.id)}>
                      {exam} — {l.codigo_lote}
                    </MenuItem>
                  );
                })}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel id="qc-equipo-corrida">Equipo</InputLabel>
              <Select
                labelId="qc-equipo-corrida"
                label="Equipo"
                value={formCorrida.equipo}
                onChange={(e) => setFormCorrida((p) => ({ ...p, equipo: String(e.target.value) }))}
              >
                <MenuItem value="">(sin equipo)</MenuItem>
                {equipos
                  .filter((eq) => eq.activo)
                  .map((eq) => (
                    <MenuItem key={eq.id} value={String(eq.id)}>
                      {eq.codigo}
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Valor medido"
              type="number"
              value={formCorrida.valor}
              onChange={(e) => setFormCorrida((p) => ({ ...p, valor: e.target.value }))}
              sx={{ width: 140 }}
            />
            <Button variant="contained" onClick={submitCorrida} disabled={saving || !lotesActivos.length}>
              {saving ? 'Guardando…' : 'Registrar corrida'}
            </Button>
          </Stack>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Fecha</TableCell>
                <TableCell>Material</TableCell>
                <TableCell>Lote</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell>Puntos</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {corridas.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>{new Date(c.fecha).toLocaleString('es-AR')}</TableCell>
                  <TableCell>{c.material_nombre}</TableCell>
                  <TableCell>{c.lote_codigo}</TableCell>
                  <TableCell>{c.estado}</TableCell>
                  <TableCell>{c.puntos?.length || 0}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}

      {tab === 2 && (
        <Box>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Nuevo material de control
          </Typography>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ mb: 2 }} flexWrap="wrap">
            <FormControl size="small" sx={{ minWidth: 220 }}>
              <InputLabel id="mat-exam">Examen</InputLabel>
              <Select
                labelId="mat-exam"
                label="Examen"
                value={formMaterial.tipo_examen}
                onChange={(e) => setFormMaterial((p) => ({ ...p, tipo_examen: String(e.target.value) }))}
              >
                {examenesOrdenados.map((ex) => (
                  <MenuItem key={ex.id} value={String(ex.id)}>
                    {ex.codigo} — {ex.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel id="mat-nivel">Nivel</InputLabel>
              <Select
                labelId="mat-nivel"
                label="Nivel"
                value={formMaterial.nivel}
                onChange={(e) =>
                  setFormMaterial((p) => ({ ...p, nivel: e.target.value as 'N1' | 'N2' | 'N3' }))
                }
              >
                <MenuItem value="N1">{NIVEL_LABEL.N1}</MenuItem>
                <MenuItem value="N2">{NIVEL_LABEL.N2}</MenuItem>
                <MenuItem value="N3">{NIVEL_LABEL.N3}</MenuItem>
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Marca"
              value={formMaterial.marca}
              onChange={(e) => setFormMaterial((p) => ({ ...p, marca: e.target.value }))}
              sx={{ width: 120 }}
            />
            <TextField
              size="small"
              label="Producto"
              value={formMaterial.producto}
              onChange={(e) => setFormMaterial((p) => ({ ...p, producto: e.target.value }))}
              sx={{ minWidth: 200 }}
            />
            <TextField
              size="small"
              label="Media target"
              type="number"
              value={formMaterial.media_target}
              onChange={(e) => setFormMaterial((p) => ({ ...p, media_target: e.target.value }))}
              sx={{ width: 120 }}
            />
            <TextField
              size="small"
              label="DE target"
              type="number"
              value={formMaterial.de_target}
              onChange={(e) => setFormMaterial((p) => ({ ...p, de_target: e.target.value }))}
              sx={{ width: 110 }}
            />
            <Button variant="contained" onClick={submitMaterial} disabled={saving}>
              Agregar material
            </Button>
          </Stack>

          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Nuevo lote
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 3 }} flexWrap="wrap">
            <FormControl size="small" sx={{ minWidth: 260 }}>
              <InputLabel id="lote-mat">Material</InputLabel>
              <Select
                labelId="lote-mat"
                label="Material"
                value={formLote.material}
                onChange={(e) => setFormLote((p) => ({ ...p, material: String(e.target.value) }))}
              >
                {materiales.map((m) => (
                  <MenuItem key={m.id} value={String(m.id)}>
                    {m.tipo_examen_codigo} {NIVEL_LABEL[m.nivel] || m.nivel} — {m.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Código lote"
              value={formLote.codigo_lote}
              onChange={(e) => setFormLote((p) => ({ ...p, codigo_lote: e.target.value }))}
            />
            <TextField
              size="small"
              label="Vencimiento"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={formLote.vencimiento}
              onChange={(e) => setFormLote((p) => ({ ...p, vencimiento: e.target.value }))}
            />
            <Button variant="contained" onClick={submitLote} disabled={saving || !materiales.length}>
              Agregar lote
            </Button>
          </Stack>

          <Typography variant="subtitle1" gutterBottom>
            Materiales
          </Typography>
          <Table size="small" sx={{ mb: 3 }}>
            <TableHead>
              <TableRow>
                <TableCell>Nombre</TableCell>
                <TableCell>Marca / Producto</TableCell>
                <TableCell>Examen</TableCell>
                <TableCell>Nivel</TableCell>
                <TableCell>Media</TableCell>
                <TableCell>DE</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {materiales.map((m) => (
                <TableRow key={m.id}>
                  <TableCell>{m.nombre}</TableCell>
                  <TableCell>
                    {[m.marca, m.producto].filter(Boolean).join(' · ') || '—'}
                  </TableCell>
                  <TableCell>
                    {m.tipo_examen_codigo} — {m.tipo_examen_nombre}
                  </TableCell>
                  <TableCell>{NIVEL_LABEL[m.nivel] || m.nivel}</TableCell>
                  <TableCell>{m.media_target}</TableCell>
                  <TableCell>{m.de_target}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <Typography variant="subtitle1" gutterBottom>
            Lotes
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Código lote</TableCell>
                <TableCell>Material</TableCell>
                <TableCell>Examen</TableCell>
                <TableCell>Vencimiento</TableCell>
                <TableCell>Activo</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {lotes.map((l) => {
                const mat = materialById.get(l.material);
                return (
                  <TableRow key={l.id}>
                    <TableCell>{l.codigo_lote}</TableCell>
                    <TableCell>{l.material_nombre || mat?.nombre || l.material}</TableCell>
                    <TableCell>
                      {mat ? `${mat.tipo_examen_codigo} ${NIVEL_LABEL[mat.nivel] || mat.nivel}` : '—'}
                    </TableCell>
                    <TableCell>{l.vencimiento}</TableCell>
                    <TableCell>{l.activo ? 'Sí' : 'No'}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Box>
      )}

      {tab === 3 && (
        <Box>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Nuevo equipo
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 3 }} flexWrap="wrap">
            <TextField
              size="small"
              label="Código"
              value={formEquipo.codigo}
              onChange={(e) => setFormEquipo((p) => ({ ...p, codigo: e.target.value }))}
            />
            <TextField
              size="small"
              label="Nombre"
              value={formEquipo.nombre}
              onChange={(e) => setFormEquipo((p) => ({ ...p, nombre: e.target.value }))}
              sx={{ minWidth: 220 }}
            />
            <TextField
              size="small"
              label="Marca / modelo"
              value={formEquipo.marca_modelo}
              onChange={(e) => setFormEquipo((p) => ({ ...p, marca_modelo: e.target.value }))}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={formEquipo.activo}
                  onChange={(e) => setFormEquipo((p) => ({ ...p, activo: e.target.checked }))}
                />
              }
              label="Activo"
            />
            <Button variant="contained" onClick={submitEquipo} disabled={saving}>
              Agregar equipo
            </Button>
          </Stack>

          <Typography variant="subtitle1" gutterBottom>
            Equipos
          </Typography>
          <Table size="small" sx={{ mb: 3 }}>
            <TableHead>
              <TableRow>
                <TableCell>Código</TableCell>
                <TableCell>Nombre</TableCell>
                <TableCell>Marca / modelo</TableCell>
                <TableCell>Activo</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {equipos.map((e) => (
                <TableRow key={e.id}>
                  <TableCell>{e.codigo}</TableCell>
                  <TableCell>{e.nombre}</TableCell>
                  <TableCell>{e.marca_modelo || '—'}</TableCell>
                  <TableCell>{e.activo ? 'Sí' : 'No'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Nueva calibración
          </Typography>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ mb: 1 }} flexWrap="wrap">
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="cal-equipo">Equipo</InputLabel>
              <Select
                labelId="cal-equipo"
                label="Equipo"
                value={formCal.equipo}
                onChange={(e) => setFormCal((p) => ({ ...p, equipo: String(e.target.value) }))}
              >
                {equipos.map((eq) => (
                  <MenuItem key={eq.id} value={String(eq.id)}>
                    {eq.codigo}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 180 }}>
              <InputLabel id="cal-tipo">Tipo</InputLabel>
              <Select
                labelId="cal-tipo"
                label="Tipo"
                value={formCal.tipo}
                onChange={(e) =>
                  setFormCal((p) => ({
                    ...p,
                    tipo: e.target.value as 'PUNTO_UNICO' | 'CURVA_MULTIPUNTO',
                    calibrador_nombre:
                      e.target.value === 'PUNTO_UNICO' ? p.calibrador_nombre || 'Calibrador A Plus' : p.calibrador_nombre,
                  }))
                }
              >
                <MenuItem value="PUNTO_UNICO">Punto único (A Plus)</MenuItem>
                <MenuItem value="CURVA_MULTIPUNTO">Curva multipunto (PCR)</MenuItem>
              </Select>
            </FormControl>
            {formCal.tipo === 'CURVA_MULTIPUNTO' && (
              <FormControl size="small" sx={{ minWidth: 220 }}>
                <InputLabel id="cal-exam">Técnica</InputLabel>
                <Select
                  labelId="cal-exam"
                  label="Técnica"
                  value={formCal.tipo_examen}
                  onChange={(e) => setFormCal((p) => ({ ...p, tipo_examen: String(e.target.value) }))}
                >
                  {examenesOrdenados
                    .filter((ex) => /PCR/i.test(ex.codigo) || /PCR|proteína c reactiva/i.test(ex.nombre))
                    .concat(
                      examenesOrdenados.filter(
                        (ex) => !(/PCR/i.test(ex.codigo) || /PCR|proteína c reactiva/i.test(ex.nombre))
                      )
                    )
                    .map((ex) => (
                      <MenuItem key={ex.id} value={String(ex.id)}>
                        {ex.codigo} — {ex.nombre}
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>
            )}
            <TextField
              size="small"
              label="Calibrador"
              value={formCal.calibrador_nombre}
              onChange={(e) => setFormCal((p) => ({ ...p, calibrador_nombre: e.target.value }))}
              sx={{ minWidth: 180 }}
            />
            <TextField
              size="small"
              label="Marca"
              value={formCal.marca}
              onChange={(e) => setFormCal((p) => ({ ...p, marca: e.target.value }))}
              sx={{ width: 120 }}
            />
            <TextField
              size="small"
              label="Lote calibrador"
              value={formCal.codigo_lote}
              onChange={(e) => setFormCal((p) => ({ ...p, codigo_lote: e.target.value }))}
            />
            <TextField
              size="small"
              label="Fecha"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={formCal.fecha}
              onChange={(e) => setFormCal((p) => ({ ...p, fecha: e.target.value }))}
            />
            <TextField
              size="small"
              label="Vigente hasta"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={formCal.vigente_hasta}
              onChange={(e) => setFormCal((p) => ({ ...p, vigente_hasta: e.target.value }))}
            />
          </Stack>

          {formCal.tipo === 'CURVA_MULTIPUNTO' && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                Puntos de la curva de aglutinación (concentración / señal)
              </Typography>
              {puntosCurva.map((p, idx) => (
                <Stack key={idx} direction="row" spacing={1} sx={{ mb: 1 }} alignItems="center">
                  <Typography variant="caption" sx={{ width: 24 }}>
                    {idx + 1}
                  </Typography>
                  <TextField
                    size="small"
                    label="Concentración"
                    value={p.concentracion}
                    onChange={(e) =>
                      setPuntosCurva((rows) =>
                        rows.map((r, i) => (i === idx ? { ...r, concentracion: e.target.value } : r))
                      )
                    }
                    sx={{ width: 140 }}
                  />
                  <TextField
                    size="small"
                    label="Señal"
                    value={p.senal ?? ''}
                    onChange={(e) =>
                      setPuntosCurva((rows) =>
                        rows.map((r, i) => (i === idx ? { ...r, senal: e.target.value } : r))
                      )
                    }
                    sx={{ width: 120 }}
                  />
                  <TextField
                    size="small"
                    label="Unidad"
                    value={p.unidad ?? ''}
                    onChange={(e) =>
                      setPuntosCurva((rows) =>
                        rows.map((r, i) => (i === idx ? { ...r, unidad: e.target.value } : r))
                      )
                    }
                    sx={{ width: 100 }}
                  />
                  <IconButton
                    size="small"
                    aria-label="Quitar punto"
                    disabled={puntosCurva.length <= 2}
                    onClick={() => setPuntosCurva((rows) => rows.filter((_, i) => i !== idx))}
                  >
                    <DeleteOutlineIcon fontSize="small" />
                  </IconButton>
                </Stack>
              ))}
              <Button
                size="small"
                startIcon={<AddIcon />}
                onClick={() =>
                  setPuntosCurva((rows) => [
                    ...rows,
                    { orden: rows.length + 1, concentracion: '', senal: '', unidad: 'mg/L' },
                  ])
                }
              >
                Agregar punto
              </Button>
            </Box>
          )}

          <Button variant="contained" onClick={submitCalibracion} disabled={saving || !equipos.length} sx={{ mb: 3 }}>
            Registrar calibración
          </Button>

          <Typography variant="subtitle1" gutterBottom>
            Calibraciones
          </Typography>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Equipo</TableCell>
                <TableCell>Tipo</TableCell>
                <TableCell>Calibrador</TableCell>
                <TableCell>Técnica</TableCell>
                <TableCell>Fecha</TableCell>
                <TableCell>Vigente hasta</TableCell>
                <TableCell>Puntos</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {cals.map((c) => (
                <TableRow key={c.id}>
                  <TableCell>{c.equipo_codigo || c.equipo_nombre}</TableCell>
                  <TableCell>{c.tipo === 'CURVA_MULTIPUNTO' ? 'Curva' : '1 punto'}</TableCell>
                  <TableCell>
                    {[c.marca, c.calibrador_nombre, c.codigo_lote].filter(Boolean).join(' · ') || '—'}
                  </TableCell>
                  <TableCell>{c.tipo_examen_codigo || '—'}</TableCell>
                  <TableCell>{c.fecha}</TableCell>
                  <TableCell>{c.vigente_hasta}</TableCell>
                  <TableCell>{c.puntos_curva?.length || 0}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>
      )}
    </Box>
  );
};

export default QcHubPage;
