import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Divider,
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
  ToggleButton,
  ToggleButtonGroup,
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
  createLoteProductoQc,
  createMaterialQc,
  createProductoQc,
  getLeveyJenningsExamen,
  listCalibracionesQc,
  listCorridasQc,
  listEquiposQc,
  listLotesControl,
  listLotesProductoQc,
  listMaterialesQc,
  listProductosQc,
  listTiposExamenLims,
  putTargetsLoteProducto,
  type Calibracion,
  type CorridaQC,
  type EquipoAnalizador,
  type LeveyJenningsSeries,
  type LoteControl,
  type LoteProductoControl,
  type MaterialControl,
  type ProductoControl,
  type PuntoCurvaCalibracion,
  type TargetLoteControl,
} from '../../../services/limsApi';
import type { LimsTipoExamen } from '../../../types/lims';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../../utils/apiError';

const EQUIPOS_POR_ENSAYO = new Set(['VIDAS_KUBE', 'FINECARE']);

const NIVEL_LABEL: Record<string, string> = {
  N1: 'S1 (normal)',
  N2: 'S2 (patológico)',
  N3: 'Nivel 3',
};

function labelLoteQc(l: LoteControl, mat?: MaterialControl): string {
  const exam = mat
    ? `${mat.tipo_examen_codigo} ${NIVEL_LABEL[mat.nivel] || mat.nivel}`
    : `mat #${l.material}`;
  const eq = mat?.equipo_codigo ? ` · ${mat.equipo_codigo}` : '';
  return `${exam}${eq} — lote ${l.codigo_lote}`;
}

function labelLoteProducto(l: LoteProductoControl): string {
  return `${l.producto_nombre} · ${l.equipo_codigo} — lote ${l.codigo_lote}`;
}

type QcMargenes = {
  media: number;
  de: number;
  warnLow: number;
  warnHigh: number;
  outLow: number;
  outHigh: number;
};

function parseQcNum(v: string | number | null | undefined): number | null {
  if (v === null || v === undefined || v === '') return null;
  const n = typeof v === 'number' ? v : Number(String(v).replace(',', '.'));
  return Number.isFinite(n) ? n : null;
}

function fmtQc(n: number, digits = 2): string {
  return n.toLocaleString('es-AR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

function rangoTxt(low: number, high: number): string {
  return `${fmtQc(low)} – ${fmtQc(high)}`;
}

function margenesDeMaterial(
  m: Pick<MaterialControl, 'media_target' | 'de_target'>
): QcMargenes | null {
  const media = parseQcNum(m.media_target);
  const de = parseQcNum(m.de_target);
  if (media == null || de == null || de <= 0) return null;
  return {
    media,
    de,
    warnLow: media - 2 * de,
    warnHigh: media + 2 * de,
    outLow: media - 3 * de,
    outHigh: media + 3 * de,
  };
}

function clasificarValorQc(valor: number, m: QcMargenes): 'ok' | 'warning' | 'fuera' {
  if (valor < m.outLow || valor > m.outHigh) return 'fuera';
  if (valor < m.warnLow || valor > m.warnHigh) return 'warning';
  return 'ok';
}

function QcMargenesResumen({
  material,
  valorMedido,
}: {
  material: MaterialControl;
  valorMedido?: string;
}) {
  const m = margenesDeMaterial(material);
  if (!m) {
    return (
      <Alert severity="warning" sx={{ mb: 2 }}>
        Este material no tiene DE válida: no se pueden calcular márgenes de aceptación.
      </Alert>
    );
  }
  const v = parseQcNum(valorMedido);
  const clase = v == null ? null : clasificarValorQc(v, m);
  const severity = clase === 'fuera' ? 'error' : clase === 'warning' ? 'warning' : 'info';
  return (
    <Alert severity={severity} sx={{ mb: 2, py: 0.5 }}>
      <Typography variant="body2" fontWeight={600}>
        {material.tipo_examen_codigo} {NIVEL_LABEL[material.nivel] || material.nivel}
        {' · '}Media {fmtQc(m.media)} · DE {fmtQc(m.de)}
      </Typography>
      <Typography variant="body2">
        Aceptación (±2s): {rangoTxt(m.warnLow, m.warnHigh)}
        {' · '}
        Fuera de control (±3s): {rangoTxt(m.outLow, m.outHigh)}
      </Typography>
      {clase === 'ok' && (
        <Typography variant="body2">El valor {fmtQc(v!)} está dentro de ±2s.</Typography>
      )}
      {clase === 'warning' && (
        <Typography variant="body2">
          El valor {fmtQc(v!)} está entre 2s y 3s (alerta Westgard 1-2s).
        </Typography>
      )}
      {clase === 'fuera' && (
        <Typography variant="body2">
          El valor {fmtQc(v!)} está fuera de ±3s (rechazo 1-3s).
        </Typography>
      )}
    </Alert>
  );
}

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function plusDaysISO(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

function LjChart({ series }: { series: LeveyJenningsSeries }) {
  const w = 680;
  const h = 240;
  const padL = 64;
  const padR = 16;
  const padY = 24;
  const pts = series.puntos;
  const mean = series.media_target;
  const sd = series.de_target || 1;
  const margenes: QcMargenes = {
    media: mean,
    de: sd,
    warnLow: mean - 2 * sd,
    warnHigh: mean + 2 * sd,
    outLow: mean - 3 * sd,
    outHigh: mean + 3 * sd,
  };
  const caption = (
    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
      Media {fmtQc(mean)} · DE {fmtQc(sd)} · ±2s {rangoTxt(margenes.warnLow, margenes.warnHigh)} · ±3s{' '}
      {rangoTxt(margenes.outLow, margenes.outHigh)}
    </Typography>
  );
  if (!pts.length) {
    return (
      <Box>
        {caption}
        <Typography color="text.secondary">Sin puntos QC.</Typography>
      </Box>
    );
  }
  const ys = pts.map((p) => p.valor);
  const yMin = Math.min(mean - 3 * sd, ...ys) - sd;
  const yMax = Math.max(mean + 3 * sd, ...ys) + sd;
  const xScale = (i: number) => padL + (i * (w - padL - padR)) / Math.max(pts.length - 1, 1);
  const yScale = (v: number) => h - padY - ((v - yMin) / (yMax - yMin || 1)) * (h - 2 * padY);
  const axisLine = (mul: number, color: string, label: string) => {
    const y = yScale(mean + mul * sd);
    return (
      <g key={label}>
        <line
          x1={padL}
          x2={w - padR}
          y1={y}
          y2={y}
          stroke={color}
          strokeDasharray={mul === 0 ? undefined : '4 4'}
        />
        <text x={4} y={y + 3} fontSize={10} fill={color}>
          {label} {fmtQc(mean + mul * sd)}
        </text>
      </g>
    );
  };
  const path = pts
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p.valor)}`)
    .join(' ');

  return (
    <Box>
      {caption}
      <svg width="100%" viewBox={`0 0 ${w} ${h}`} role="img" aria-label="Levey-Jennings">
        <rect x={0} y={0} width={w} height={h} fill="transparent" />
        {axisLine(0, '#1976d2', 'Media')}
        {axisLine(2, '#ed6c02', '+2s')}
        {axisLine(-2, '#ed6c02', '-2s')}
        {axisLine(3, '#d32f2f', '+3s')}
        {axisLine(-3, '#d32f2f', '-3s')}
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
    </Box>
  );
}

const QcHubPage: React.FC = () => {
  const [tab, setTab] = useState(0);
  const [equipos, setEquipos] = useState<EquipoAnalizador[]>([]);
  const [materiales, setMateriales] = useState<MaterialControl[]>([]);
  const [lotes, setLotes] = useState<LoteControl[]>([]);
  const [productos, setProductos] = useState<ProductoControl[]>([]);
  const [lotesProducto, setLotesProducto] = useState<LoteProductoControl[]>([]);
  const [corridas, setCorridas] = useState<CorridaQC[]>([]);
  const [cals, setCals] = useState<Calibracion[]>([]);
  const [examenes, setExamenes] = useState<LimsTipoExamen[]>([]);
  const [lj, setLj] = useState<LeveyJenningsSeries | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [formCorrida, setFormCorrida] = useState({
    tipo: 'PRODUCTO' as 'PRODUCTO' | 'ENSAYO',
    lote_producto: '',
    lote_control: '',
    nivel: 'N1' as 'N1' | 'N2' | 'N3',
    modo: 'ACEPTAR_NIVEL' as 'ACEPTAR_NIVEL' | 'VALORES',
    valor: '',
    valores: {} as Record<number, string>,
    equipo: '',
  });
  const [formMaterial, setFormMaterial] = useState({
    tipo_examen: '',
    nombre: 'Control VIDAS',
    marca: '',
    producto: 'Control VIDAS',
    nivel: 'N1' as 'N1' | 'N2' | 'N3',
    media_target: '100',
    de_target: '5',
  });
  const [formLote, setFormLote] = useState({
    material: '',
    codigo_lote: '',
    vencimiento: plusDaysISO(365),
  });
  const [formProducto, setFormProducto] = useState({
    codigo: '',
    nombre: '',
    marca: '',
    equipo: '',
  });
  const [formLoteProd, setFormLoteProd] = useState({
    producto: '',
    codigo_lote: '',
    vencimiento: plusDaysISO(365),
  });
  const [loteTargetsEdit, setLoteTargetsEdit] = useState('');
  const [targetDraft, setTargetDraft] = useState<
    Record<string, { media: string; de: string }>
  >({});
  const [formEquipo, setFormEquipo] = useState({
    codigo: '',
    nombre: '',
    marca_modelo: '',
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
  const lotesProductoActivos = useMemo(
    () => lotesProducto.filter((l) => l.activo),
    [lotesProducto]
  );
  const materialesPorEnsayo = useMemo(
    () =>
      materiales.filter(
        (m) => m.activo && m.equipo_codigo && EQUIPOS_POR_ENSAYO.has(m.equipo_codigo)
      ),
    [materiales]
  );
  const lotesPorEnsayo = useMemo(
    () =>
      lotesActivos.filter((l) => {
        const mat = materialById.get(l.material);
        return mat?.equipo_codigo && EQUIPOS_POR_ENSAYO.has(mat.equipo_codigo);
      }),
    [lotesActivos, materialById]
  );

  const materialCorridaSeleccionada = useMemo(() => {
    const lote = lotesPorEnsayo.find((l) => String(l.id) === formCorrida.lote_control);
    if (!lote) return undefined;
    return materialById.get(lote.material);
  }, [formCorrida.lote_control, lotesPorEnsayo, materialById]);

  const loteProductoSeleccionado = useMemo(
    () => lotesProductoActivos.find((l) => String(l.id) === formCorrida.lote_producto),
    [formCorrida.lote_producto, lotesProductoActivos]
  );

  const targetsNivel = useMemo(() => {
    if (!loteProductoSeleccionado) return [] as TargetLoteControl[];
    return loteProductoSeleccionado.targets.filter((t) => t.nivel === formCorrida.nivel);
  }, [loteProductoSeleccionado, formCorrida.nivel]);

  const productosPorEquipo = useMemo((): Array<[string, ProductoControl[]]> => {
    const groups = new Map<string, ProductoControl[]>();
    for (const p of productos.filter((x) => x.activo)) {
      const key = p.equipo_codigo || '—';
      const arr = groups.get(key) || [];
      arr.push(p);
      groups.set(key, arr);
    }
    return Array.from(groups.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [productos]);

  const loteTargetsSeleccionado = useMemo(
    () => lotesProducto.find((l) => String(l.id) === loteTargetsEdit),
    [lotesProducto, loteTargetsEdit]
  );

  const examenesDeLoteTargets = useMemo(() => {
    if (!loteTargetsSeleccionado) return [] as LimsTipoExamen[];
    const ids = new Set(loteTargetsSeleccionado.targets.map((t) => t.tipo_examen));
    const delEquipo = examenes.filter((ex) => {
      if (ids.has(ex.id)) return true;
      const prod = productos.find((p) => p.id === loteTargetsSeleccionado.producto);
      return prod != null && ex.equipo_analizador === prod.equipo;
    });
    const seen = new Set<number>();
    const out: LimsTipoExamen[] = [];
    for (const ex of delEquipo.sort((a, b) => a.codigo.localeCompare(b.codigo))) {
      if (seen.has(ex.id)) continue;
      seen.add(ex.id);
      out.push(ex);
    }
    return out;
  }, [loteTargetsSeleccionado, examenes, productos]);

  const margenesFormMaterial = useMemo(
    () => margenesDeMaterial(formMaterial),
    [formMaterial]
  );

  const helperValorCorrida = useMemo(() => {
    if (!materialCorridaSeleccionada) return ' ';
    const mg = margenesDeMaterial(materialCorridaSeleccionada);
    return mg ? `Aceptable ±2s: ${rangoTxt(mg.warnLow, mg.warnHigh)}` : ' ';
  }, [materialCorridaSeleccionada]);

  const examenesOrdenados = useMemo(
    () => [...examenes].sort((a, b) => a.codigo.localeCompare(b.codigo)),
    [examenes]
  );
  const examenesPorEnsayo = useMemo(
    () =>
      examenesOrdenados.filter(
        (ex) =>
          ex.equipo_analizador_codigo && EQUIPOS_POR_ENSAYO.has(ex.equipo_analizador_codigo)
      ),
    [examenesOrdenados]
  );

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const settled = await Promise.allSettled([
        listEquiposQc(),
        listMaterialesQc(),
        listLotesControl(),
        listLotesProductoQc(),
        listProductosQc(),
        listCorridasQc(),
        listCalibracionesQc(),
        listTiposExamenLims({ activo: true }),
      ]);
      const pick = <T,>(i: number, fallback: T): T =>
        settled[i].status === 'fulfilled' ? (settled[i] as PromiseFulfilledResult<T>).value : fallback;
      const e = pick(0, [] as EquipoAnalizador[]);
      const m = pick(1, [] as MaterialControl[]);
      const l = pick(2, [] as LoteControl[]);
      const lp = pick(3, [] as LoteProductoControl[]);
      const prod = pick(4, [] as ProductoControl[]);
      const c = pick(5, [] as CorridaQC[]);
      const cal = pick(6, [] as Calibracion[]);
      const ex = pick(7, [] as LimsTipoExamen[]);
      const failed = settled
        .map((s, i) => (s.status === 'rejected' ? i : -1))
        .filter((i) => i >= 0);
      if (failed.includes(0)) {
        toast.error(
          getSafeClinicalActionMessage(
            (settled[0] as PromiseRejectedResult).reason,
            CLINICAL_ACTION_ERRORS.genericClinicalAction
          )
        );
      } else if (failed.length) {
        toast.error(
          'Parte del catálogo QC no cargó (productos/lotes o cartas). Los equipos sí se pueden usar si aparecen abajo.'
        );
      }
      setEquipos(e);
      setMateriales(m);
      setLotes(l);
      setLotesProducto(lp);
      setProductos(prod);
      setCorridas(c);
      setCals(cal);
      setExamenes(ex);
      const lpActivos = lp.filter((x) => x.activo);
      const matsEnsayo = m.filter(
        (x) => x.activo && x.equipo_codigo && EQUIPOS_POR_ENSAYO.has(x.equipo_codigo)
      );
      const lotesEnsayo = l.filter((x) => {
        const mat = matsEnsayo.find((mm) => mm.id === x.material);
        return x.activo && mat;
      });
      const equipoDefault =
        e.find((eq) => eq.activo && eq.codigo === 'CM260') || e.find((eq) => eq.activo) || e[0];
      setFormCorrida((prev) => ({
        ...prev,
        lote_producto: prev.lote_producto || (lpActivos[0] ? String(lpActivos[0].id) : ''),
        lote_control: prev.lote_control || (lotesEnsayo[0] ? String(lotesEnsayo[0].id) : ''),
        equipo: prev.equipo || (equipoDefault ? String(equipoDefault.id) : ''),
      }));
      setFormLote((prev) => ({
        ...prev,
        material: prev.material || (matsEnsayo[0] ? String(matsEnsayo[0].id) : ''),
      }));
      setFormLoteProd((prev) => ({
        ...prev,
        producto: prev.producto || (prod[0] ? String(prod[0].id) : ''),
      }));
      setFormProducto((prev) => ({
        ...prev,
        equipo: prev.equipo || (equipoDefault ? String(equipoDefault.id) : ''),
      }));
      setLoteTargetsEdit((prev) => prev || (lpActivos[0] ? String(lpActivos[0].id) : ''));
      setFormCal((prev) => ({
        ...prev,
        equipo: prev.equipo || (e[0] ? String(e[0].id) : ''),
      }));
      setFormMaterial((prev) => ({
        ...prev,
        tipo_examen: prev.tipo_examen || (ex[0] ? String(ex[0].id) : ''),
      }));
      const glu = ex.find((x) => x.codigo === 'GLU') || ex[0];
      if (glu) {
        try {
          setLj(await getLeveyJenningsExamen(glu.id));
        } catch {
          setLj(null);
        }
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

  useEffect(() => {
    const lote = lotesProducto.find((l) => String(l.id) === loteTargetsEdit);
    if (!lote) {
      setTargetDraft({});
      return;
    }
    const next: Record<string, { media: string; de: string }> = {};
    for (const t of lote.targets) {
      next[`${t.tipo_examen}-${t.nivel}`] = {
        media: String(t.media_target),
        de: String(t.de_target),
      };
    }
    setTargetDraft(next);
  }, [loteTargetsEdit, lotesProducto]);

  const submitCorrida = async () => {
    setSaving(true);
    try {
      if (formCorrida.tipo === 'PRODUCTO') {
        const loteId = Number(formCorrida.lote_producto);
        if (!loteId || Number.isNaN(loteId)) {
          toast.error('Seleccioná un lote de producto.');
          setSaving(false);
          return;
        }
        const nivelReg = formCorrida.nivel;
        const nivelLabel = NIVEL_LABEL[nivelReg] || nivelReg;
        if (formCorrida.modo === 'ACEPTAR_NIVEL') {
          await createCorridaQc({
            lote_producto: loteId,
            nivel: nivelReg,
            equipo: formCorrida.equipo ? Number(formCorrida.equipo) : null,
            fecha: new Date().toISOString(),
            modo: 'ACEPTAR_NIVEL',
          });
          toast.success(`${nivelLabel} aceptado`);
        } else {
          const valores = targetsNivel
            .map((t) => ({
              tipo_examen: t.tipo_examen,
              valor: formCorrida.valores[t.tipo_examen],
            }))
            .filter((v) => v.valor != null && String(v.valor).trim() !== '');
          if (!valores.length) {
            toast.error('Cargá al menos un valor por ensayo.');
            setSaving(false);
            return;
          }
          await createCorridaQc({
            lote_producto: loteId,
            nivel: nivelReg,
            equipo: formCorrida.equipo ? Number(formCorrida.equipo) : null,
            fecha: new Date().toISOString(),
            modo: 'VALORES',
            valores,
          });
          toast.success(`Corrida ${nivelLabel} con valores registrada`);
          setFormCorrida((p) => ({ ...p, valores: {} }));
        }
        // Tras S1, pasar a S2 para no registrar dos veces el mismo nivel por error.
        if (nivelReg === 'N1') {
          setFormCorrida((p) => ({ ...p, nivel: 'N2', valores: {} }));
          toast('Elegí Registrar aceptación (o Con valores) para S2.', { icon: '👉' });
        }
      } else {
        const loteId = Number(formCorrida.lote_control);
        if (!loteId || Number.isNaN(loteId)) {
          toast.error('Seleccioná un lote de control.');
          setSaving(false);
          return;
        }
        if (!formCorrida.valor.trim() || Number.isNaN(Number(formCorrida.valor))) {
          toast.error('Ingresá el valor medido del control.');
          setSaving(false);
          return;
        }
        await createCorridaQc({
          lote_control: loteId,
          equipo: formCorrida.equipo ? Number(formCorrida.equipo) : null,
          fecha: new Date().toISOString(),
          valor: Number(formCorrida.valor),
        });
        toast.success('Corrida registrada');
        setFormCorrida((p) => ({ ...p, valor: '' }));
      }
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
        equipo: exam?.equipo_analizador ?? null,
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

  const submitProducto = async () => {
    if (!formProducto.codigo.trim() || !formProducto.nombre.trim() || !formProducto.equipo) {
      toast.error('Completá código, nombre y equipo del producto.');
      return;
    }
    setSaving(true);
    try {
      await createProductoQc({
        codigo: formProducto.codigo.trim().toUpperCase(),
        nombre: formProducto.nombre.trim(),
        marca: formProducto.marca.trim(),
        equipo: Number(formProducto.equipo),
        modo: 'MULTIPARAM',
        activo: true,
      });
      toast.success('Producto creado');
      setFormProducto((p) => ({ ...p, codigo: '', nombre: '' }));
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsQcCatalogo));
    } finally {
      setSaving(false);
    }
  };

  const submitLoteProd = async () => {
    if (!formLoteProd.producto || !formLoteProd.codigo_lote.trim() || !formLoteProd.vencimiento) {
      toast.error('Completá producto, código de lote y vencimiento.');
      return;
    }
    setSaving(true);
    try {
      await createLoteProductoQc({
        producto: Number(formLoteProd.producto),
        codigo_lote: formLoteProd.codigo_lote.trim(),
        vencimiento: formLoteProd.vencimiento,
        activo: true,
      });
      toast.success('Lote de producto creado');
      setFormLoteProd((p) => ({ ...p, codigo_lote: '' }));
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsQcCatalogo));
    } finally {
      setSaving(false);
    }
  };

  const submitTargets = async () => {
    const loteId = Number(loteTargetsEdit);
    if (!loteId || !examenesDeLoteTargets.length) {
      toast.error('Seleccioná un lote con ensayos.');
      return;
    }
    const rows: Array<{
      tipo_examen: number;
      nivel: 'N1' | 'N2' | 'N3';
      media_target: string;
      de_target: string;
    }> = [];
    for (const ex of examenesDeLoteTargets) {
      for (const nivel of ['N1', 'N2'] as const) {
        const d = targetDraft[`${ex.id}-${nivel}`];
        if (!d || !d.media.trim() || !d.de.trim()) continue;
        rows.push({
          tipo_examen: ex.id,
          nivel,
          media_target: d.media,
          de_target: d.de,
        });
      }
    }
    if (!rows.length) {
      toast.error('Completá al menos un target (media y DE).');
      return;
    }
    setSaving(true);
    try {
      await putTargetsLoteProducto(loteId, rows);
      toast.success('Targets guardados');
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
      setFormEquipo({ codigo: '', nombre: '', marca_modelo: '', activo: true });
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
        IQC híbrido: productos multiparámetro (Standatrol, Sysmex, Coatron, Diestro, EDAN) habilitan
        el equipo con S1+S2. VIDAS y Finecare siguen con control por ensayo.
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
          <Autocomplete
            size="small"
            sx={{ mb: 2, maxWidth: 520 }}
            options={examenesOrdenados}
            value={examenes.find((x) => x.id === lj?.tipo_examen_id) || null}
            onChange={async (_e, ex) => {
              if (ex) setLj(await getLeveyJenningsExamen(ex.id));
              else setLj(null);
            }}
            getOptionLabel={(ex) => `${ex.codigo} — ${ex.nombre}`}
            isOptionEqualToValue={(a, b) => a.id === b.id}
            filterOptions={(opts, state) => {
              const q = state.inputValue.trim().toLowerCase();
              if (!q) return opts;
              return opts.filter((ex) =>
                `${ex.codigo} ${ex.nombre} ${ex.equipo_analizador_codigo || ''}`.toLowerCase().includes(q)
              );
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Ensayo (Levey-Jennings)"
                placeholder="Buscar por código o equipo…"
              />
            )}
          />
          {lj && <LjChart series={lj} />}
          {!lj && !loading && (
            <Typography color="text.secondary">Seleccioná un ensayo para ver la carta.</Typography>
          )}
        </Box>
      )}

      {tab === 1 && (
        <Box>
          <ToggleButtonGroup
            exclusive
            size="small"
            value={formCorrida.tipo}
            onChange={(_e, v) => {
              if (v) setFormCorrida((p) => ({ ...p, tipo: v }));
            }}
            sx={{ mb: 2 }}
          >
            <ToggleButton value="PRODUCTO">Producto (multiparámetro)</ToggleButton>
            <ToggleButton value="ENSAYO">Ensayo (VIDAS / Finecare)</ToggleButton>
          </ToggleButtonGroup>

          {formCorrida.tipo === 'PRODUCTO' && (
            <Box>
              {!lotesProductoActivos.length && !loading && (
                <Typography color="warning.main" sx={{ mb: 2 }}>
                  No hay lotes de producto. Creá producto y lote en Materiales / Lotes, o ejecutá{' '}
                  <code>seed_qc_demo</code>.
                </Typography>
              )}
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }} flexWrap="wrap">
                <Autocomplete
                  size="small"
                  sx={{ minWidth: 320, flex: 1, maxWidth: 520 }}
                  options={[...lotesProductoActivos].sort((a, b) =>
                    labelLoteProducto(a).localeCompare(labelLoteProducto(b), 'es')
                  )}
                  value={loteProductoSeleccionado || null}
                  onChange={(_e, lote) => {
                    setFormCorrida((p) => ({
                      ...p,
                      lote_producto: lote ? String(lote.id) : '',
                      equipo: lote?.equipo != null ? String(lote.equipo) : p.equipo,
                      valores: {},
                    }));
                  }}
                  getOptionLabel={(l) => labelLoteProducto(l)}
                  isOptionEqualToValue={(a, b) => a.id === b.id}
                  renderInput={(params) => (
                    <TextField {...params} label="Producto / lote" placeholder="Standatrol, Sysmex…" />
                  )}
                />
                <FormControl size="small" sx={{ minWidth: 140 }}>
                  <InputLabel id="qc-nivel">Nivel</InputLabel>
                  <Select
                    labelId="qc-nivel"
                    label="Nivel"
                    value={formCorrida.nivel}
                    onChange={(e) =>
                      setFormCorrida((p) => ({
                        ...p,
                        nivel: e.target.value as 'N1' | 'N2' | 'N3',
                        valores: {},
                      }))
                    }
                  >
                    <MenuItem value="N1">{NIVEL_LABEL.N1}</MenuItem>
                    <MenuItem value="N2">{NIVEL_LABEL.N2}</MenuItem>
                  </Select>
                </FormControl>
                <FormControl size="small" sx={{ minWidth: 160 }}>
                  <InputLabel id="qc-equipo-prod">Equipo</InputLabel>
                  <Select
                    labelId="qc-equipo-prod"
                    label="Equipo"
                    value={formCorrida.equipo}
                    onChange={(e) => setFormCorrida((p) => ({ ...p, equipo: String(e.target.value) }))}
                  >
                    {equipos.filter((eq) => eq.activo).map((eq) => (
                      <MenuItem key={eq.id} value={String(eq.id)}>{eq.codigo}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <ToggleButtonGroup
                  exclusive
                  size="small"
                  value={formCorrida.modo}
                  onChange={(_e, v) => {
                    if (v) setFormCorrida((p) => ({ ...p, modo: v }));
                  }}
                >
                  <ToggleButton value="ACEPTAR_NIVEL">Modo rápido</ToggleButton>
                  <ToggleButton value="VALORES">Con valores</ToggleButton>
                </ToggleButtonGroup>
                {formCorrida.modo === 'ACEPTAR_NIVEL' && (
                  <Button variant="contained" onClick={submitCorrida} disabled={saving || !lotesProductoActivos.length}>
                    {saving ? 'Guardando…' : 'Registrar aceptación'}
                  </Button>
                )}
              </Stack>
              {formCorrida.modo === 'ACEPTAR_NIVEL' && (
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  Modo rápido solo elige cómo registrar: no guarda nada al hacer clic ahí. Elegí el{' '}
                  <strong>Nivel</strong> (S1 o S2) y después pulsá <strong>Registrar aceptación</strong>.
                </Typography>
              )}
              {formCorrida.modo === 'VALORES' && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    Valores por ensayo ({NIVEL_LABEL[formCorrida.nivel]}). Target ±2s / ±3s.
                  </Typography>
                  <Table size="small" sx={{ mb: 1 }}>
                    <TableHead>
                      <TableRow>
                        <TableCell>Ensayo</TableCell>
                        <TableCell>Media</TableCell>
                        <TableCell>±2s</TableCell>
                        <TableCell>±3s</TableCell>
                        <TableCell>Valor</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {targetsNivel.map((t) => {
                        const mg = margenesDeMaterial(t);
                        const v = formCorrida.valores[t.tipo_examen] || '';
                        return (
                          <TableRow key={t.id}>
                            <TableCell>{t.tipo_examen_codigo}</TableCell>
                            <TableCell>{mg ? fmtQc(mg.media) : t.media_target}</TableCell>
                            <TableCell>{mg ? rangoTxt(mg.warnLow, mg.warnHigh) : '—'}</TableCell>
                            <TableCell>{mg ? rangoTxt(mg.outLow, mg.outHigh) : '—'}</TableCell>
                            <TableCell>
                              <TextField
                                size="small"
                                type="number"
                                value={v}
                                onChange={(e) =>
                                  setFormCorrida((p) => ({
                                    ...p,
                                    valores: { ...p.valores, [t.tipo_examen]: e.target.value },
                                  }))
                                }
                                sx={{ width: 110 }}
                              />
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                  <Button variant="contained" onClick={submitCorrida} disabled={saving || !targetsNivel.length}>
                    {saving ? 'Guardando…' : 'Registrar valores'}
                  </Button>
                </Box>
              )}
            </Box>
          )}

          {formCorrida.tipo === 'ENSAYO' && (
        <Box>
          {!lotesPorEnsayo.length && !loading && (
            <Typography color="warning.main" sx={{ mb: 2 }}>
              No hay lotes activos. Creá material y lote en la pestaña Materiales / Lotes, o ejecutá{' '}
              <code>seed_qc_demo</code>.
            </Typography>
          )}
          {materialCorridaSeleccionada && (
            <QcMargenesResumen
              material={materialCorridaSeleccionada}
              valorMedido={formCorrida.valor}
            />
          )}
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }} alignItems="flex-start">
            <Autocomplete
              size="small"
              sx={{ minWidth: 360, flex: 1, maxWidth: 560 }}
              options={[...lotesPorEnsayo].sort((a, b) =>
                labelLoteQc(a, materialById.get(a.material)).localeCompare(
                  labelLoteQc(b, materialById.get(b.material)),
                  'es'
                )
              )}
              value={lotesPorEnsayo.find((l) => String(l.id) === formCorrida.lote_control) || null}
              onChange={(_e, lote) => {
                if (!lote) {
                  setFormCorrida((p) => ({ ...p, lote_control: '' }));
                  return;
                }
                const mat = materialById.get(lote.material);
                setFormCorrida((p) => ({
                  ...p,
                  lote_control: String(lote.id),
                  equipo: mat?.equipo != null ? String(mat.equipo) : p.equipo,
                }));
              }}
              getOptionLabel={(l) => labelLoteQc(l, materialById.get(l.material))}
              isOptionEqualToValue={(a, b) => a.id === b.id}
              filterOptions={(opts, state) => {
                const q = state.inputValue.trim().toLowerCase();
                if (!q) return opts;
                return opts.filter((l) => {
                  const mat = materialById.get(l.material);
                  const hay = [
                    l.codigo_lote,
                    mat?.tipo_examen_codigo || '',
                    mat?.tipo_examen_nombre || '',
                    mat?.nombre || '',
                    mat?.equipo_codigo || '',
                    mat ? NIVEL_LABEL[mat.nivel] || mat.nivel : '',
                  ]
                    .join(' ')
                    .toLowerCase();
                  return hay.includes(q);
                });
              }}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Lote de control"
                  placeholder="Buscar examen, equipo o lote…"
                />
              )}
              disabled={!lotesPorEnsayo.length}
            />
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
              helperText={helperValorCorrida}
            />
            <Button variant="contained" onClick={submitCorrida} disabled={saving || !lotesPorEnsayo.length}>
              {saving ? 'Guardando…' : 'Registrar corrida'}
            </Button>
          </Stack>
            </Box>
          )}
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Fecha</TableCell>
                <TableCell>Tipo</TableCell>
                <TableCell>Producto / material</TableCell>
                <TableCell>Lote</TableCell>
                <TableCell>Nivel</TableCell>
                <TableCell>Puntos</TableCell>
                <TableCell>Estado</TableCell>
                <TableCell>Reglas</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {corridas.map((c) => {
                const ultimo = c.puntos?.length ? c.puntos[c.puntos.length - 1] : undefined;
                const reglas = (c.puntos || []).flatMap((p) => p.reglas_disparadas || []);
                const esProd = Boolean(c.lote_producto);
                return (
                  <TableRow key={c.id}>
                    <TableCell>{new Date(c.fecha).toLocaleString('es-AR')}</TableCell>
                    <TableCell>{esProd ? 'Producto' : 'Ensayo'}</TableCell>
                    <TableCell>{c.producto_nombre || c.material_nombre || '—'}</TableCell>
                    <TableCell>{c.lote_codigo}</TableCell>
                    <TableCell>{c.nivel ? NIVEL_LABEL[c.nivel] || c.nivel : '—'}</TableCell>
                    <TableCell>
                      {c.puntos?.length
                        ? `${c.puntos.length}${ultimo ? ` · último ${fmtQc(parseQcNum(ultimo.valor) ?? 0)}` : ''}`
                        : '—'}
                    </TableCell>
                    <TableCell>{c.estado}</TableCell>
                    <TableCell>
                      {reglas.length ? (
                        <Typography variant="caption" color="text.secondary">
                          {Array.from(new Set(reglas)).join(', ')}
                        </Typography>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Box>
      )}

      {tab === 2 && (
        <Box>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Productos multiparámetro
          </Typography>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={1} sx={{ mb: 2 }} flexWrap="wrap">
            <TextField
              size="small"
              label="Código"
              value={formProducto.codigo}
              onChange={(e) => setFormProducto((p) => ({ ...p, codigo: e.target.value }))}
              sx={{ width: 160 }}
            />
            <TextField
              size="small"
              label="Nombre"
              value={formProducto.nombre}
              onChange={(e) => setFormProducto((p) => ({ ...p, nombre: e.target.value }))}
              sx={{ minWidth: 220 }}
            />
            <TextField
              size="small"
              label="Marca"
              value={formProducto.marca}
              onChange={(e) => setFormProducto((p) => ({ ...p, marca: e.target.value }))}
              sx={{ width: 140 }}
            />
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="prod-eq">Equipo</InputLabel>
              <Select
                labelId="prod-eq"
                label="Equipo"
                value={formProducto.equipo}
                onChange={(e) => setFormProducto((p) => ({ ...p, equipo: String(e.target.value) }))}
              >
                {equipos
                  .filter((eq) => eq.activo && !EQUIPOS_POR_ENSAYO.has(eq.codigo))
                  .map((eq) => (
                    <MenuItem key={eq.id} value={String(eq.id)}>
                      {eq.codigo}
                    </MenuItem>
                  ))}
              </Select>
            </FormControl>
            <Button variant="contained" onClick={submitProducto} disabled={saving}>
              Alta producto
            </Button>
          </Stack>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mb: 2 }} flexWrap="wrap">
            <FormControl size="small" sx={{ minWidth: 260 }}>
              <InputLabel id="lote-prod">Producto</InputLabel>
              <Select
                labelId="lote-prod"
                label="Producto"
                value={formLoteProd.producto}
                onChange={(e) => setFormLoteProd((p) => ({ ...p, producto: String(e.target.value) }))}
              >
                {productos.filter((p) => p.activo).map((p) => (
                  <MenuItem key={p.id} value={String(p.id)}>
                    {p.equipo_codigo} — {p.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="Código lote"
              value={formLoteProd.codigo_lote}
              onChange={(e) => setFormLoteProd((p) => ({ ...p, codigo_lote: e.target.value }))}
            />
            <TextField
              size="small"
              label="Vencimiento"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={formLoteProd.vencimiento}
              onChange={(e) => setFormLoteProd((p) => ({ ...p, vencimiento: e.target.value }))}
            />
            <Button variant="contained" onClick={submitLoteProd} disabled={saving || !productos.length}>
              Alta lote
            </Button>
          </Stack>
          {productosPorEquipo.map(([eqCodigo, prods]) => (
            <Box key={eqCodigo} sx={{ mb: 2 }}>
              <Typography variant="subtitle2" fontWeight={600}>{eqCodigo}</Typography>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Producto</TableCell>
                    <TableCell>Marca</TableCell>
                    <TableCell>Lotes</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {prods.map((p: ProductoControl) => (
                    <TableRow key={p.id}>
                      <TableCell>{p.codigo} — {p.nombre}</TableCell>
                      <TableCell>{p.marca || '—'}</TableCell>
                      <TableCell>
                        {lotesProducto.filter((l) => l.producto === p.id).map((l) => l.codigo_lote).join(', ') || '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          ))}
          <Typography variant="subtitle1" fontWeight={600} gutterBottom sx={{ mt: 2 }}>
            Targets del inserto (ensayo × S1/S2)
          </Typography>
          <FormControl size="small" sx={{ minWidth: 360, mb: 1 }}>
            <InputLabel id="lote-tgt">Lote</InputLabel>
            <Select
              labelId="lote-tgt"
              label="Lote"
              value={loteTargetsEdit}
              onChange={(e) => setLoteTargetsEdit(String(e.target.value))}
            >
              {lotesProductoActivos.map((l) => (
                <MenuItem key={l.id} value={String(l.id)}>{labelLoteProducto(l)}</MenuItem>
              ))}
            </Select>
          </FormControl>
          {loteTargetsSeleccionado && (
            <Box sx={{ mb: 3, overflowX: 'auto' }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Ensayo</TableCell>
                    <TableCell>S1 media</TableCell>
                    <TableCell>S1 DE</TableCell>
                    <TableCell>S2 media</TableCell>
                    <TableCell>S2 DE</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {examenesDeLoteTargets.map((ex) => {
                    const s1 = targetDraft[`${ex.id}-N1`] || { media: '', de: '' };
                    const s2 = targetDraft[`${ex.id}-N2`] || { media: '', de: '' };
                    return (
                      <TableRow key={ex.id}>
                        <TableCell>{ex.codigo}</TableCell>
                        {(['N1', 'N2'] as const).map((nivel) => {
                          const d = nivel === 'N1' ? s1 : s2;
                          return (
                            <React.Fragment key={nivel}>
                              <TableCell>
                                <TextField
                                  size="small"
                                  type="number"
                                  value={d.media}
                                  onChange={(e) =>
                                    setTargetDraft((prev) => ({
                                      ...prev,
                                      [`${ex.id}-${nivel}`]: { ...d, media: e.target.value },
                                    }))
                                  }
                                  sx={{ width: 90 }}
                                />
                              </TableCell>
                              <TableCell>
                                <TextField
                                  size="small"
                                  type="number"
                                  value={d.de}
                                  onChange={(e) =>
                                    setTargetDraft((prev) => ({
                                      ...prev,
                                      [`${ex.id}-${nivel}`]: { ...d, de: e.target.value },
                                    }))
                                  }
                                  sx={{ width: 80 }}
                                />
                              </TableCell>
                            </React.Fragment>
                          );
                        })}
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
              <Button variant="contained" onClick={submitTargets} disabled={saving} sx={{ mt: 1 }}>
                Guardar targets
              </Button>
            </Box>
          )}
          <Divider sx={{ my: 3 }} />
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Controles por ensayo (VIDAS / Finecare)
          </Typography>
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
                {(examenesPorEnsayo.length ? examenesPorEnsayo : examenesOrdenados).map((ex) => (
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
          {margenesFormMaterial && (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Márgenes calculados: aceptación ±2s {rangoTxt(margenesFormMaterial.warnLow, margenesFormMaterial.warnHigh)}
              {' · '}fuera de control ±3s {rangoTxt(margenesFormMaterial.outLow, margenesFormMaterial.outHigh)}
            </Typography>
          )}

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
                {materialesPorEnsayo.map((m) => (
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
            <Button variant="contained" onClick={submitLote} disabled={saving || !materialesPorEnsayo.length}>
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
                <TableCell>Equipo</TableCell>
                <TableCell>Media</TableCell>
                <TableCell>DE</TableCell>
                <TableCell>Aceptación ±2s</TableCell>
                <TableCell>Fuera ±3s</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {materialesPorEnsayo.map((m) => {
                const mg = margenesDeMaterial(m);
                return (
                  <TableRow key={m.id}>
                    <TableCell>{m.nombre}</TableCell>
                    <TableCell>
                      {[m.marca, m.producto].filter(Boolean).join(' · ') || '—'}
                    </TableCell>
                    <TableCell>
                      {m.tipo_examen_codigo} — {m.tipo_examen_nombre}
                    </TableCell>
                  <TableCell>{NIVEL_LABEL[m.nivel] || m.nivel}</TableCell>
                  <TableCell>{m.equipo_codigo || '—'}</TableCell>
                  <TableCell>{mg ? fmtQc(mg.media) : m.media_target}</TableCell>
                  <TableCell>{mg ? fmtQc(mg.de) : m.de_target}</TableCell>
                  <TableCell>{mg ? rangoTxt(mg.warnLow, mg.warnHigh) : '—'}</TableCell>
                  <TableCell>{mg ? rangoTxt(mg.outLow, mg.outHigh) : '—'}</TableCell>
                  </TableRow>
                );
              })}
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
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Los equipos del lab (CM260, Sysmex, Coatron, Diestro, VIDAS, EDAN, Finecare) se crean con{' '}
            <code>seed_qc_demo</code>. Acá solo hace falta un código que todavía no exista.
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
