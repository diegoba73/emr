import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  IconButton,
  InputAdornment,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import toast from 'react-hot-toast';
import type {
  LimsTipoExamen,
  MuestraTransaccional,
  SolicitudExamenLims,
} from '../../types/lims';
import {
  getIqcPrecheck,
  getTiposExamenMap,
  patchOrdenInformeOrden,
  postCargarResultados,
  postSugerirConclusionHemograma,
  type IqcPrecheckResult,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { groupResultadosPorPanel } from '../../utils/limsResultadosPanel';
import {
  applyOrdenGrupos,
  PANEL_HEMOGRAMA,
  reorderOrdenGrupos,
  resolveOrdenGrupos,
} from '../../utils/limsOrdenInforme';
import ResultadoRangoInfo from './ResultadoRangoInfo';
import ResultadosOrdenLista from './ResultadosOrdenLista';
import AnalisisLongitudinalPanel from './AnalisisLongitudinalPanel';
import { useHistorialAnalitos } from './useHistorialAnalitos';
import {
  applyAutofillVcmChcm,
  buildCargarResultadoPayload,
  buildValoresBorradorConclusion,
  draftCreatinuriaDesdeResultado,
  draftRowClearsServerValue,
  draftRowHasValue,
  draftSysmexTicketFromResultado,
  draftValorClinicoNumerico,
  filterMuestrasProcesables,
  getTipoExamenCatalog,
  normalizeDraftRow,
  suggestMuestraIdForResultado,
  validateCargaResultadosMuestra,
  validateCargaResultadosValores,
  resultadoDebeGuardarse,
  resultadoPuedeOmitirseSinMuestra,
  resultadoTieneValorGuardado,
  type DraftCargaRow,
} from '../../utils/limsCargaMuestra';
import {
  clinicoDesdeEquipoCreatinuria,
  esCreatininuria,
  formatCreatinuriaNumero,
  parseNumeroCarga,
} from '../../utils/creatinuriaDilucion';
import { countResultadosConValor, valorTextoDesdeResultado } from '../../utils/limsOrdenResultados';
import { ordenPuedeCargarResultados } from '../../utils/limsEstadosOrden';
import {
  computeFormulaProgress,
  formatFormulaProgressLabel,
  isCalculadoEntrada,
  isFormulaPercent,
  previewTicketInforme,
  usesTicketEntry,
} from '../../utils/entradaResultados';
import {
  calcAbsolutoFormula,
  calcCaIonZeislerMmolL,
  formatAbsolutoMm3,
  FORMULA_LEUCO_CODIGOS,
  esResultadoNoCalculable,
} from '../../utils/calculosDerivados';
import { getSysmexUnidad } from '../../utils/sysmexHemograma';
import {
  CODIGO_PROT_T,
  esCodigoElpFraccion,
  formatPctElp,
  porcentajeFraccionElp,
} from '../../utils/proteinograma';

export interface CargaResultadosLimsProps {
  orden: SolicitudExamenLims;
  muestras: MuestraTransaccional[];
  canOperate: boolean;
  /** Si false, oculta el formulario de carga/edición (solo lectura). */
  permitirEdicion?: boolean;
  onGuardado: (o: SolicitudExamenLims) => void;
  /** Mostrar «Validar y liberar» junto a Guardar (bioquímico/admin, lista para validar). */
  mostrarValidar?: boolean;
  onValidar?: () => void;
  validando?: boolean;
  /** p.ej. obra social no autorizada en ambulatorio. */
  validarDeshabilitado?: boolean;
  validarDeshabilitadoMotivo?: string;
}

/** Anchos fijos para que Valor/Unidad/Referencia alineen entre paneles. */
const CARGA_COL_WIDTHS_STD = ['34%', '28%', '12%', '20%', '52px'] as const;
const CARGA_COL_WIDTHS_TICKET = ['28%', '18%', '14%', '12%', '20%', '52px'] as const;

function CargaColGroup({ ticket }: { ticket: boolean }) {
  const widths = ticket ? CARGA_COL_WIDTHS_TICKET : CARGA_COL_WIDTHS_STD;
  return (
    <colgroup>
      {widths.map((w, i) => (
        <col key={i} style={{ width: w }} />
      ))}
    </colgroup>
  );
}

/** Claves de foco para navegación con Enter en la grilla de carga. */
function buildCargaFocusOrder(
  grupos: ReturnType<typeof groupResultadosPorPanel>,
  tiposExamenMap: Map<number, LimsTipoExamen>
): string[] {
  const keys: string[] = [];
  let observacionesInsertada = false;
  for (const grupo of grupos) {
    for (const r of grupo.resultados) {
      const te = tiposExamenMap.get(r.tipo_examen);
      if (isCalculadoEntrada(te, r.tipo_examen_codigo)) {
        continue;
      }
      if (usesTicketEntry(te, r.tipo_examen_codigo)) {
        keys.push(`sysmex-${r.id}`);
      } else {
        keys.push(`valor-${r.id}`);
      }
    }
    // Conclusión del hemograma: foco justo debajo del panel.
    if (grupo.codigo === PANEL_HEMOGRAMA) {
      keys.push('observaciones');
      observacionesInsertada = true;
    }
  }
  if (!observacionesInsertada) {
    keys.push('observaciones');
  }
  return keys;
}

function focusCargaField(key: string): boolean {
  const input = document.querySelector<HTMLInputElement | HTMLTextAreaElement>(
    `[data-carga-focus="${key}"]`
  );
  if (!input) return false;
  input.focus();
  if (input instanceof HTMLInputElement && input.type !== 'hidden') {
    input.select();
  } else if (input instanceof HTMLTextAreaElement) {
    input.select();
  }
  return true;
}

function formatFechaHistorialCorta(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit' });
}

const CargaResultadosLims: React.FC<CargaResultadosLimsProps> = ({
  orden,
  muestras,
  canOperate,
  permitirEdicion = true,
  onGuardado,
  mostrarValidar = false,
  onValidar,
  validando = false,
  validarDeshabilitado = false,
  validarDeshabilitadoMotivo,
}) => {
  const resultados = orden.resultados || [];
  const dilucionCreatinuria = Boolean(orden.crea_u_dilucion_activa);
  const dilucionOpts = useMemo(
    () => ({
      dilucionCreatinuria,
      edadAnos: orden.paciente_edad ?? null,
      sexo: orden.paciente_sexo ?? null,
    }),
    [dilucionCreatinuria, orden.paciente_edad, orden.paciente_sexo]
  );
  const [draft, setDraft] = useState<Record<number, DraftCargaRow>>({});
  const [observacionesOrden, setObservacionesOrden] = useState('');
  const [saving, setSaving] = useState(false);
  const [iqcPrecheck, setIqcPrecheck] = useState<IqcPrecheckResult | null>(null);
  const [sugeriendo, setSugeriendo] = useState(false);
  const [sugerenciaMeta, setSugerenciaMeta] = useState<{
    fuente: string;
    marcado: boolean;
  } | null>(null);
  const [tiposExamenMap, setTiposExamenMap] = useState<Map<number, LimsTipoExamen>>(new Map());
  const tiposHistorialKey = Array.from(new Set(resultados.map((r) => r.tipo_examen))).sort((a, b) => a - b).join(',');
  const { previosPorTipo, loading: loadingHistorial, error: errorHistorial, actualizar: actualizarHistorial } =
    useHistorialAnalitos(orden.id, tiposHistorialKey);

  const esHemograma = useMemo(
    () =>
      (orden.paneles_resumen ?? []).some((p) => p.codigo === PANEL_HEMOGRAMA) ||
      (orden.resultados ?? []).some((r) =>
        ['HGB', 'HEMATIES', 'HTO', 'PLAQ', 'RDW'].includes(
          (r.tipo_examen_codigo || '').toUpperCase()
        )
      ),
    [orden.paneles_resumen, orden.resultados]
  );

  const muestrasProcesables = useMemo(() => filterMuestrasProcesables(muestras), [muestras]);
  const gruposBase = useMemo(
    () => groupResultadosPorPanel({ ...orden, orden_grupos_informe: undefined }, resultados),
    [orden, resultados]
  );
  const [ordenGrupos, setOrdenGrupos] = useState<string[]>([]);
  const [savingOrden, setSavingOrden] = useState(false);

  useEffect(() => {
    setOrdenGrupos(resolveOrdenGrupos(gruposBase, orden.orden_grupos_informe));
  }, [orden.orden_grupos_informe, gruposBase]);

  const grupos = useMemo(
    () => applyOrdenGrupos(gruposBase, ordenGrupos),
    [gruposBase, ordenGrupos]
  );
  const analisisFingerprint = useMemo(
    () =>
      resultados
        .map((r) => `${r.id}:${r.valor_obtenido ?? ''}:${r.valor_numerico ?? ''}:${r.es_patologico}:${r.es_critico}`)
        .join('|'),
    [resultados]
  );
  const focusOrder = useMemo(() => buildCargaFocusOrder(grupos, tiposExamenMap), [grupos, tiposExamenMap]);
  const guardarBtnRef = useRef<HTMLButtonElement>(null);
  const [focusedSysmexKey, setFocusedSysmexKey] = useState<string | null>(null);
  const indicesManualRef = useRef<Set<number>>(new Set());
  /** Filas que el operador vació a propósito (no rellenar con Zeisler/autofill). */
  const clearedIdsRef = useRef<Set<number>>(new Set());

  const formulaProgress = useMemo(
    () =>
      computeFormulaProgress(
        resultados.map((r) => ({
          te: tiposExamenMap.get(r.tipo_examen),
          codigo: r.tipo_examen_codigo,
          valor_sysmex: draft[r.id]?.valor_sysmex,
        }))
      ),
    [resultados, draft, tiposExamenMap]
  );

  const focusNextField = useCallback(
    (currentKey: string) => {
      const idx = focusOrder.indexOf(currentKey);
      if (idx === -1) return;
      for (let i = idx + 1; i < focusOrder.length; i += 1) {
        if (focusCargaField(focusOrder[i])) return;
      }
      guardarBtnRef.current?.focus();
    },
    [focusOrder]
  );

  const handleEnterNext = useCallback(
    (currentKey: string) => (ev: React.KeyboardEvent) => {
      if (ev.key !== 'Enter' || ev.shiftKey || ev.nativeEvent.isComposing) return;
      ev.preventDefault();
      focusNextField(currentKey);
    },
    [focusNextField]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const te = await getTiposExamenMap();
        if (cancelled) return;
        setTiposExamenMap(te);
      } catch {
        if (!cancelled) {
          toast.error('No se pudo cargar el catálogo de exámenes.');
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const liveIds = new Set(resultados.map((r) => r.id));
    Array.from(clearedIdsRef.current).forEach((id) => {
      if (!liveIds.has(id)) clearedIdsRef.current.delete(id);
    });
    Array.from(indicesManualRef.current).forEach((id) => {
      if (!liveIds.has(id)) indicesManualRef.current.delete(id);
    });

    setDraft((prev) => {
      const next: Record<number, DraftCargaRow> = {};
      for (const r of resultados) {
        const te = tiposExamenMap.get(r.tipo_examen);
        const codigo = r.tipo_examen_codigo ?? te?.codigo;
        const muestraId = suggestMuestraIdForResultado(
          r,
          muestrasProcesables,
          tiposExamenMap,
          r.muestra_id ?? null
        );
        const unidadCatalogo =
          r.unidad?.trim() ||
          te?.unidad_default?.trim() ||
          getSysmexUnidad(codigo) ||
          '';
        const creaUDraft = draftCreatinuriaDesdeResultado(r, dilucionCreatinuria);
        const usaDraftCreaU =
          dilucionCreatinuria && esCreatininuria(codigo) && Boolean(creaUDraft.valor);
        const valorNumericoStr = usaDraftCreaU
          ? creaUDraft.valor_numerico
          : r.valor_numerico !== null && r.valor_numerico !== undefined
            ? String(r.valor_numerico)
            : '';
        const built: DraftCargaRow = {
          // Texto/símbolos (valor_obtenido) mandan; numérico solo si no hay texto.
          // CREA_U con dilución: pantalla = CM260 (clínico ÷ 20).
          valor: usaDraftCreaU ? creaUDraft.valor : valorTextoDesdeResultado(r),
          valor_sysmex: draftSysmexTicketFromResultado(r, te, codigo),
          valor_numerico: valorNumericoStr,
          unidad: unidadCatalogo,
          muestra_id: muestraId,
        };
        const prevRow = prev[r.id];
        if (prevRow) {
          // Conservar el borrador en memoria aunque esté vacío: si el operador
          // borró un valor ya informado, no restaurarlo desde el servidor al
          // refrescar catálogo/muestras (si no, "limpiar + guardar" no funciona).
          built.valor_sysmex = prevRow.valor_sysmex;
          built.valor = prevRow.valor;
          built.valor_numerico = prevRow.valor_numerico;
          if (prevRow.unidad.trim()) built.unidad = prevRow.unidad;
          if (prevRow.muestra_id != null) {
            // Re-sugerir: puede upgradear heparina legacy → SUERO canónico.
            const resolved = suggestMuestraIdForResultado(
              r,
              muestrasProcesables,
              tiposExamenMap,
              prevRow.muestra_id
            );
            if (resolved != null) built.muestra_id = resolved;
          }
          if (
            draftRowClearsServerValue(r, built, te, codigo) ||
            clearedIdsRef.current.has(r.id)
          ) {
            clearedIdsRef.current.add(r.id);
            indicesManualRef.current.add(r.id);
          }
        }
        next[r.id] = built;
        const c = (codigo || '').toUpperCase();
        if (
          (c === 'VCM' || c === 'HCM' || c === 'CHCM') &&
          draftRowHasValue(built, te, codigo) &&
          (r.valor_obtenido || r.valor_numerico != null) &&
          !clearedIdsRef.current.has(r.id)
        ) {
          // Valor ya persistido: tratar como fijado hasta que el operador edite bases.
          indicesManualRef.current.add(r.id);
        }
      }
      // CA_ION persistido: solo fijar manual si no coincide con Zeisler actual.
      for (const r of resultados) {
        const te = tiposExamenMap.get(r.tipo_examen);
        const c = (r.tipo_examen_codigo || te?.codigo || '').toUpperCase();
        if (c !== 'CA_ION') continue;
        if (clearedIdsRef.current.has(r.id)) {
          indicesManualRef.current.add(r.id);
          continue;
        }
        const built = next[r.id];
        if (!built || !draftRowHasValue(built, te, r.tipo_examen_codigo)) continue;
        const byCodigo = new Map<string, (typeof resultados)[number]>();
        for (const x of resultados) {
          const cx = (
            x.tipo_examen_codigo ||
            tiposExamenMap.get(x.tipo_examen)?.codigo ||
            ''
          ).toUpperCase();
          if (cx) byCodigo.set(cx, x);
        }
        const rCa = byCodigo.get('CA');
        const rProt = byCodigo.get('PROT_T');
        const caN = rCa
          ? Number(next[rCa.id]?.valor_numerico || next[rCa.id]?.valor || '')
          : NaN;
        const protN = rProt
          ? Number(next[rProt.id]?.valor_numerico || next[rProt.id]?.valor || '')
          : NaN;
        const estimado =
          Number.isFinite(caN) && Number.isFinite(protN)
            ? calcCaIonZeislerMmolL(caN, protN)
            : null;
        const actual = Number(built.valor_numerico || built.valor || '');
        if (
          estimado == null ||
          !Number.isFinite(actual) ||
          Math.round(actual * 100) !== Math.round(estimado * 100)
        ) {
          indicesManualRef.current.add(r.id);
        } else {
          indicesManualRef.current.delete(r.id);
        }
      }
      return applyAutofillVcmChcm(
        resultados,
        next,
        tiposExamenMap,
        indicesManualRef.current,
        clearedIdsRef.current,
        dilucionOpts
      );
    });
    setObservacionesOrden(orden.observaciones ?? '');
    setSugerenciaMeta(null);
  }, [
    analisisFingerprint,
    muestrasProcesables,
    tiposExamenMap,
    orden.observaciones,
    resultados,
    dilucionCreatinuria,
    dilucionOpts,
  ]);

  const progreso = useMemo(() => countResultadosConValor(orden), [orden]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const p = await getIqcPrecheck(orden.id);
        if (!cancelled) setIqcPrecheck(p);
      } catch {
        if (!cancelled) setIqcPrecheck(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [orden.id, orden.estado]);

  const iqcBloqueaCarga = Boolean(iqcPrecheck?.aplicable && !iqcPrecheck.ok);
  const iqcSinConfiguracion = Boolean(iqcPrecheck?.sin_configuracion);

  const editable =
    permitirEdicion &&
    canOperate &&
    ordenPuedeCargarResultados(orden.estado) &&
    resultados.length > 0;

  const tiposExamenMapRef = useRef(tiposExamenMap);
  tiposExamenMapRef.current = tiposExamenMap;
  const resultadosRef = useRef(resultados);
  resultadosRef.current = resultados;
  const dilucionOptsRef = useRef(dilucionOpts);
  dilucionOptsRef.current = dilucionOpts;

  const setRow = (id: number, patch: Partial<DraftCargaRow>) => {
    const r = resultadosRef.current.find((x) => x.id === id);
    const te = r ? tiposExamenMapRef.current.get(r.tipo_examen) : undefined;
    const codigo = (r?.tipo_examen_codigo || te?.codigo || '').toUpperCase();
    if (codigo === 'VCM' || codigo === 'HCM' || codigo === 'CHCM' || codigo === 'CA_ION') {
      if (patch.valor_sysmex !== undefined || patch.valor !== undefined || patch.valor_numerico !== undefined) {
        indicesManualRef.current.add(id);
      }
    }
    setDraft((d) => {
      const merged: DraftCargaRow = {
        ...(d[id] || emptyDraft()),
        ...patch,
      };
      // Ticket vacío: limpiar también valor/numérico para no dejar basura stale.
      if (patch.valor_sysmex !== undefined && !String(patch.valor_sysmex).trim()) {
        merged.valor = '';
        merged.valor_numerico = '';
      }
      if (r && draftRowClearsServerValue(r, merged, te, codigo)) {
        clearedIdsRef.current.add(id);
        indicesManualRef.current.add(id);
      } else if (draftRowHasValue(merged, te, codigo)) {
        clearedIdsRef.current.delete(id);
      } else if (r && !resultadoTieneValorGuardado(r)) {
        clearedIdsRef.current.delete(id);
      }
      const next = { ...d, [id]: merged };
      return applyAutofillVcmChcm(
        resultadosRef.current,
        next,
        tiposExamenMapRef.current,
        indicesManualRef.current,
        clearedIdsRef.current,
        dilucionOptsRef.current
      );
    });
  };

  const moveGrupoInforme = useCallback(
    async (grupoKey: string, direction: 'up' | 'down') => {
      const next = reorderOrdenGrupos(ordenGrupos, grupoKey, direction);
      if (next === ordenGrupos) {
        return;
      }
      const prev = ordenGrupos;
      setOrdenGrupos(next);
      setSavingOrden(true);
      try {
        const updated = await patchOrdenInformeOrden(orden.id, next);
        onGuardado(updated);
      } catch {
        setOrdenGrupos(prev);
        toast.error('No se pudo guardar el orden del informe.');
      } finally {
        setSavingOrden(false);
      }
    },
    [orden.id, ordenGrupos, onGuardado]
  );

  const handleSugerirConclusion = async () => {
    setSugeriendo(true);
    try {
      const valores_borrador = buildValoresBorradorConclusion(
        resultados,
        draft,
        tiposExamenMap,
        dilucionOpts
      );
      if (Object.keys(valores_borrador).length === 0) {
        toast.error('Ingresá al menos un valor del hemograma para sugerir la conclusión.');
        return;
      }
      const data = await postSugerirConclusionHemograma(orden.id, { valores_borrador });
      if (!data.texto?.trim()) {
        toast.error('No se pudo generar una conclusión con los valores actuales.');
        return;
      }
      setObservacionesOrden(data.texto.trim());
      setSugerenciaMeta({
        fuente: data.fuente || 'reglas',
        marcado: Boolean(data.marcado_sugerencia),
      });
      toast.success(
        data.fuente === 'medgemma'
          ? 'Sugerencia MedGemma lista — revisá y guardá.'
          : 'Sugerencia por reglas lista — revisá y guardá.'
      );
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, 'No se pudo sugerir la conclusión.'));
    } finally {
      setSugeriendo(false);
    }
  };

  const resultadosYaCompletos =
    orden.estado === 'LISTO_PARA_VALIDAR' ||
    (progreso.total > 0 && progreso.conValor >= progreso.total);

  const filaTieneValorEnPantalla = useCallback(
    (r: (typeof resultados)[number]) => {
      const te = getTipoExamenCatalog(r.tipo_examen, tiposExamenMap);
      const row = draft[r.id] || emptyDraft();
      if (clearedIdsRef.current.has(r.id) && !draftRowHasValue(row, te, r.tipo_examen_codigo)) {
        return false;
      }
      return (
        draftRowHasValue(row, te, r.tipo_examen_codigo) || resultadoTieneValorGuardado(r)
      );
    },
    [draft, tiposExamenMap, resultados]
  );

  /** Progreso en pantalla (draft + guardado): habilita informar parcial sin exigir otro click. */
  const progresoPantalla = useMemo(() => {
    const total = resultados.length;
    const conValor = resultados.filter(filaTieneValorEnPantalla).length;
    return { conValor, total };
  }, [resultados, filaTieneValorEnPantalla]);

  const puedeInformarParcial =
    progresoPantalla.conValor > 0 &&
    progresoPantalla.conValor < progresoPantalla.total &&
    orden.estado !== 'LISTO_PARA_VALIDAR' &&
    orden.estado !== 'FINALIZADO';

  const toastSinFilasAGuardar = () => {
    const completosEnPantalla =
      resultadosYaCompletos ||
      (resultados.length > 0 && resultados.every(filaTieneValorEnPantalla));
    if (completosEnPantalla) {
      toast.success(
        'Los resultados de la orden ya están completos, ya se pueden validar.'
      );
      return;
    }
    // Ya hay valores pero nada dirty: no mostrar error engañoso de “ingresá un valor”.
    if (resultados.some(filaTieneValorEnPantalla)) {
      toast.success(
        'No hay cambios nuevos para guardar. Completá el resto de ensayos o informá parcialmente.'
      );
      return;
    }
    toast.error(
      'Ingresá al menos un valor para guardar, o borrá un valor ya cargado para marcarlo como no informado.'
    );
  };

  const handleGuardar = async (informarParcial = false) => {
    const filasAGuardar = resultados.filter((r) => {
      const te = getTipoExamenCatalog(r.tipo_examen, tiposExamenMap);
      const row = draft[r.id] || emptyDraft();
      if (clearedIdsRef.current.has(r.id) && resultadoTieneValorGuardado(r)) {
        return true;
      }
      return resultadoDebeGuardarse(r, row, te, dilucionOpts);
    });

    // Valores ya guardados, nada dirty: marcar INFORMADO_PARCIAL sin reenviar filas.
    // No exige IQC (no muta resultados; mismo criterio que móvil / BE).
    if (!filasAGuardar.length && informarParcial) {
      if (orden.estado === 'INFORMADO_PARCIAL') {
        toast.success('La orden ya está en Informe parcial.');
        return;
      }
      if (progreso.conValor === 0) {
        toast.error('Guardá al menos un valor antes de informar parcialmente.');
        return;
      }
      if (progreso.conValor >= progreso.total || resultadosYaCompletos) {
        toast.success(
          'Los resultados de la orden ya están completos, ya se pueden validar.'
        );
        return;
      }
      setSaving(true);
      try {
        const updated = await postCargarResultados(orden.id, [], {
          observaciones: observacionesOrden,
          informar_parcial: true,
          orden_grupos_informe: ordenGrupos,
        });
        if (updated.estado === 'INFORMADO_PARCIAL') {
          toast.success('Resultados guardados — Informe parcial');
        } else if (updated.estado === 'LISTO_PARA_VALIDAR') {
          toast.success(
            'Los resultados de la orden ya están completos, ya se pueden validar.'
          );
        } else {
          toast.success('Avance guardado');
        }
        onGuardado(updated);
      } catch (e) {
        toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarResultado));
      } finally {
        setSaving(false);
      }
      return;
    }

    if (iqcBloqueaCarga) {
      toast.error(
        iqcPrecheck?.problemas?.length
          ? `IQC no vigente: ${iqcPrecheck.problemas.join('; ')}`
          : 'IQC no vigente. Ejecutá control de calidad antes de cargar resultados.'
      );
      return;
    }

    if (!filasAGuardar.length) {
      toastSinFilasAGuardar();
      return;
    }

    // Re-asociar tubo al guardar: catálogo tardío, varios tubos, o vínculos legacy
    // (p. ej. química en heparina cuando el catálogo ya exige suero).
    const draftSave: Record<number, DraftCargaRow> = { ...draft };
    for (const r of filasAGuardar) {
      let prev = normalizeDraftRow(draftSave[r.id] || emptyDraft());
      // Borrado explícito: forzar vacío aunque el autofill haya dejado basura.
      if (clearedIdsRef.current.has(r.id) && resultadoTieneValorGuardado(r)) {
        prev = {
          ...prev,
          valor: '',
          valor_sysmex: '',
          valor_numerico: '',
        };
        draftSave[r.id] = prev;
      }
      const resolved = suggestMuestraIdForResultado(
        r,
        muestrasProcesables,
        tiposExamenMap,
        prev.muestra_id ?? r.muestra_id ?? null
      );
      if (resolved !== prev.muestra_id) {
        draftSave[r.id] = { ...prev, muestra_id: resolved };
      }
    }
    setDraft(draftSave);

    // No reenviar resultados ya informados que siguen sin tubo (bloqueaban otros paneles).
    const filasPayload = filasAGuardar.filter((r) => {
      const te = getTipoExamenCatalog(r.tipo_examen, tiposExamenMap);
      const row = normalizeDraftRow(draftSave[r.id] || emptyDraft());
      return !resultadoPuedeOmitirseSinMuestra(r, row, te);
    });

    if (!filasPayload.length) {
      if (resultadosYaCompletos) {
        toast.success(
          'Los resultados de la orden ya están completos, ya se pueden validar.'
        );
        return;
      }
      const hayValorGuardado = resultados.some((r) => resultadoTieneValorGuardado(r));
      if (hayValorGuardado) {
        toast.success(
          'No hay cambios nuevos para guardar. Completá el resto de ensayos o informá parcialmente.'
        );
        return;
      }
      toast.error(
        'Ingresá al menos un valor para guardar, o asociá la muestra requerida en los exámenes pendientes.'
      );
      return;
    }

    const payload = filasPayload.map((r) => {
      const te = getTipoExamenCatalog(r.tipo_examen, tiposExamenMap);
      return buildCargarResultadoPayload(
        r.id,
        draftSave[r.id] || emptyDraft(),
        te,
        r.tipo_examen_codigo
      );
    });

    const errMuestra = validateCargaResultadosMuestra(
      resultados,
      draftSave,
      tiposExamenMap,
      muestras,
      filasPayload.map((r) => r.id)
    );
    if (errMuestra) {
      toast.error(errMuestra);
      return;
    }

    const errValores = validateCargaResultadosValores(
      resultados,
      draftSave,
      tiposExamenMap,
      filasPayload.map((r) => r.id)
    );
    if (errValores) {
      toast.error(errValores);
      return;
    }

    setSaving(true);
    try {
      const updated = await postCargarResultados(orden.id, payload, {
        observaciones: observacionesOrden,
        informar_parcial: informarParcial,
        orden_grupos_informe: ordenGrupos,
      });
      if (informarParcial && updated.estado === 'INFORMADO_PARCIAL') {
        toast.success('Resultados guardados — Informe parcial');
      } else if (updated.estado === 'LISTO_PARA_VALIDAR') {
        toast.success(
          'Los resultados de la orden ya están completos, ya se pueden validar.'
        );
      } else {
        toast.success('Avance guardado');
      }
      for (const r of filasPayload) {
        clearedIdsRef.current.delete(r.id);
      }
      onGuardado(updated);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarResultado));
    } finally {
      setSaving(false);
    }
  };

  const resolveUnidad = useCallback(
    (r: (typeof resultados)[number], te?: LimsTipoExamen) => {
      const row = draft[r.id];
      const codigo = r.tipo_examen_codigo ?? te?.codigo;
      return (
        row?.unidad?.trim() ||
        r.unidad?.trim() ||
        te?.unidad_default?.trim() ||
        getSysmexUnidad(codigo) ||
        '—'
      );
    },
    [draft]
  );

  const fechaSolicitudLabel = useMemo(() => {
    if (!orden.fecha_solicitud) return '—';
    try {
      return new Date(orden.fecha_solicitud).toLocaleString('es-AR');
    } catch {
      return orden.fecha_solicitud;
    }
  }, [orden.fecha_solicitud]);

  const fechaExtraccionLabel = useMemo(() => {
    if (orden.fecha_toma_muestra) {
      try {
        return new Date(orden.fecha_toma_muestra).toLocaleString('es-AR');
      } catch {
        return orden.fecha_toma_muestra;
      }
    }
    const fromMuestras = muestras
      .map((m) => m.fecha_toma)
      .filter((f): f is string => Boolean(f))
      .sort()
      .at(-1);
    if (fromMuestras) {
      try {
        return new Date(fromMuestras).toLocaleString('es-AR');
      } catch {
        return fromMuestras;
      }
    }
    if (orden.fecha_programada_toma) {
      return `${orden.fecha_programada_toma} (programada)`;
    }
    return '—';
  }, [orden.fecha_toma_muestra, orden.fecha_programada_toma, muestras]);

  const fechaExtraccionPorResultado = useMemo(() => {
    const map = new Map<number, string>();
    for (const r of resultados) {
      let iso: string | null | undefined = r.muestra_fecha_toma;
      if (!iso && r.muestra_id != null) {
        iso = muestras.find((m) => m.id === r.muestra_id)?.fecha_toma;
      }
      if (!iso && r.tipo_examen_muestra_codigo) {
        const code = r.tipo_examen_muestra_codigo.toUpperCase();
        const match = muestras
          .filter(
            (m) =>
              (m.tipo_muestra_codigo || '').toUpperCase() === code && Boolean(m.fecha_toma)
          )
          .sort((a, b) => String(a.fecha_toma).localeCompare(String(b.fecha_toma)))
          .at(-1);
        iso = match?.fecha_toma;
      }
      if (iso) {
        try {
          map.set(r.id, new Date(iso).toLocaleString('es-AR'));
        } catch {
          map.set(r.id, iso);
        }
      }
    }
    return map;
  }, [resultados, muestras]);

  const renderEditRow = useCallback(
    (
      r: (typeof resultados)[number],
      ordenOpts?: { ordenRowSpan?: number; grupoKey?: string; grupoIndex?: number }
    ) => {
      const row = draft[r.id] || emptyDraft();
      const te = getTipoExamenCatalog(r.tipo_examen, tiposExamenMap);
      const ticketEntry = usesTicketEntry(te, r.tipo_examen_codigo);
      const informePreview = ticketEntry
        ? previewTicketInforme(te, row.valor_sysmex, r.tipo_examen_codigo)
        : null;
      const unidadLabel = resolveUnidad(r, te);
      const sysmexFocusKey = `sysmex-${r.id}`;
      const valorFocusKey = `valor-${r.id}`;
      const esFormula = isFormulaPercent(te, r.tipo_examen_codigo);
      const esCalculado = isCalculadoEntrada(te, r.tipo_examen_codigo);
      const mostrarIndicadorFormula = esFormula && focusedSysmexKey === sysmexFocusKey;
      const showOrden = ordenOpts?.ordenRowSpan !== undefined;
      const previos = previosPorTipo.get(r.tipo_examen) || [];
      const codigoUpper = (r.tipo_examen_codigo || te?.codigo || '').toUpperCase();
      let valorDisplayExtra = '';
      if (FORMULA_LEUCO_CODIGOS.has(codigoUpper)) {
        const leucoRow = resultados.find((x) => {
          const c = (x.tipo_examen_codigo || tiposExamenMap.get(x.tipo_examen)?.codigo || '').toUpperCase();
          return c === 'LEUCO';
        });
        if (leucoRow) {
          const pct = Number(row.valor_numerico || row.valor || informePreview || '');
          const leucoDraft = draft[leucoRow.id];
          const leucoN = Number(
            leucoDraft?.valor_numerico || leucoDraft?.valor || leucoRow.valor_numerico || ''
          );
          if (Number.isFinite(pct) && Number.isFinite(leucoN)) {
            const abs = calcAbsolutoFormula(pct, leucoN);
            if (abs != null) valorDisplayExtra = ` · ${formatAbsolutoMm3(abs)}`;
          }
        }
      } else if (esCodigoElpFraccion(codigoUpper)) {
        const protRow = resultados.find((x) => {
          const c = (x.tipo_examen_codigo || tiposExamenMap.get(x.tipo_examen)?.codigo || '').toUpperCase();
          return c === CODIGO_PROT_T;
        });
        if (protRow) {
          const fracN = draftValorClinicoNumerico(r, draft, tiposExamenMap, dilucionOpts);
          const protN = draftValorClinicoNumerico(protRow, draft, tiposExamenMap, dilucionOpts);
          const pct = porcentajeFraccionElp(fracN, protN);
          const label = formatPctElp(pct);
          if (label) valorDisplayExtra = ` · ${label}`;
        }
      } else if (dilucionCreatinuria && esCreatininuria(codigoUpper)) {
        const equipo = parseNumeroCarga(row.valor || row.valor_numerico);
        if (equipo != null) {
          valorDisplayExtra = ` · ×20 → ${formatCreatinuriaNumero(clinicoDesdeEquipoCreatinuria(equipo))} mg/dL`;
        }
      }

      let chipCaIonEstimado = false;
      if (codigoUpper === 'CA_ION' && !indicesManualRef.current.has(r.id) && row.valor) {
        const rCa = resultados.find((x) => {
          const c = (x.tipo_examen_codigo || tiposExamenMap.get(x.tipo_examen)?.codigo || '').toUpperCase();
          return c === 'CA';
        });
        const rProt = resultados.find((x) => {
          const c = (x.tipo_examen_codigo || tiposExamenMap.get(x.tipo_examen)?.codigo || '').toUpperCase();
          return c === 'PROT_T';
        });
        if (rCa && rProt) {
          const caN = draftValorClinicoNumerico(rCa, draft, tiposExamenMap, dilucionOpts);
          const protN = draftValorClinicoNumerico(rProt, draft, tiposExamenMap, dilucionOpts);
          const est =
            caN != null && protN != null ? calcCaIonZeislerMmolL(caN, protN) : null;
          const actual = Number(row.valor_numerico || row.valor || '');
          chipCaIonEstimado =
            est != null &&
            Number.isFinite(actual) &&
            Math.round(actual * 100) === Math.round(est * 100);
        }
      }

      return (
        <TableRow key={r.id}>
          <TableCell>
            <Typography variant="body2" fontWeight={600}>
              {r.tipo_examen_nombre || r.tipo_examen}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              {r.tipo_examen_codigo}
            </Typography>
            {chipCaIonEstimado && (
              <Chip
                size="small"
                variant="outlined"
                label="Estimado (Zeisler)"
                sx={{ mt: 0.5, height: 22 }}
              />
            )}
            {fechaExtraccionPorResultado.get(r.id) && (
              <Typography variant="caption" color="text.secondary" display="block">
                Extracción: {fechaExtraccionPorResultado.get(r.id)}
              </Typography>
            )}
            {r.estado_derivacion && r.estado_derivacion !== 'LOCAL' && (
              <Box sx={{ mt: 0.5, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                <Chip
                  size="small"
                  color="info"
                  variant="outlined"
                  label={`Derivado ${r.laboratorio_derivacion_codigo || ''}: ${r.estado_derivacion}${
                    r.estado_derivacion === 'PENDIENTE_ENVIO' || r.estado_derivacion === 'ENVIADO'
                      ? ' · cargar al llegar por correo'
                      : ''
                  }`}
                />
              </Box>
            )}
            {previos.length > 0 && (
              <Box sx={{ mt: 0.75, display: 'flex', flexWrap: 'wrap', gap: 0.5, alignItems: 'center' }}>
                <Typography variant="caption" color="text.secondary" sx={{ mr: 0.25 }}>
                  Previos:
                </Typography>
                {previos.slice(0, 10).map((p) => (
                  <Chip
                    key={p.resultado_id}
                    component="a"
                    href={`/laboratorio/ordenes/${p.solicitud_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    clickable
                    title={`Ver orden ${p.solicitud_numero || p.solicitud_id} en otra pestaña`}
                    size="small"
                    variant="outlined"
                    label={`${formatFechaHistorialCorta(p.fecha)} ${p.valor}${p.unidad ? ` ${p.unidad}` : ''}`}
                    sx={{ height: 22, '& .MuiChip-label': { px: 0.75, fontSize: '0.7rem' } }}
                  />
                ))}
              </Box>
            )}
          </TableCell>
          {esCalculado ? (
            <TableCell>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="body2" fontWeight={row.valor ? 600 : 400}>
                  {row.valor || '—'}
                </Typography>
                <Chip size="small" variant="outlined" label={esResultadoNoCalculable(row.valor) ? 'No calculable' : 'Calculado'} sx={{ height: 22 }} />
              </Box>
            </TableCell>
          ) : ticketEntry ? (
            <>
              <TableCell>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, flexWrap: 'nowrap' }}>
                  <TextField
                    size="small"
                    value={row.valor_sysmex}
                    onChange={(ev) => {
                      const v = ev.target.value.replace(/\D/g, '');
                      setRow(r.id, { valor_sysmex: v });
                    }}
                    onFocus={() => setFocusedSysmexKey(sysmexFocusKey)}
                    onKeyDown={handleEnterNext(sysmexFocusKey)}
                    placeholder={esFormula ? 'Ej. 70' : 'Ej. 93'}
                    inputMode="numeric"
                    inputProps={{ 'data-carga-focus': sysmexFocusKey }}
                    helperText={
                      esFormula
                        ? 'Enter → siguiente'
                        : 'Ticket Sysmex sin decimal · Enter → siguiente'
                    }
                    sx={{ minWidth: 88, flex: '1 1 auto', width: '100%' }}
                  />
                  {mostrarIndicadorFormula && (
                    <Chip
                      size="small"
                      variant="outlined"
                      color={
                        formulaProgress.isComplete
                          ? 'success'
                          : formulaProgress.isOver
                            ? 'warning'
                            : 'primary'
                      }
                      label={formatFormulaProgressLabel(formulaProgress)}
                      sx={{ mt: 0.75, flexShrink: 0, fontWeight: 600 }}
                    />
                  )}
                </Box>
              </TableCell>
              <TableCell>
                <Typography variant="body2" fontWeight={informePreview ? 600 : 400} color={informePreview ? 'text.primary' : 'text.secondary'}>
                  {informePreview
                    ? `${informePreview}${esFormula && valorDisplayExtra ? '%' : ''}${valorDisplayExtra}`
                    : '—'}
                </Typography>
              </TableCell>
            </>
          ) : (
            <TableCell>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                <TextField
                  size="small"
                  fullWidth
                  value={row.valor}
                  onChange={(ev) => setRow(r.id, { valor: ev.target.value, valor_numerico: '' })}
                  onKeyDown={handleEnterNext(valorFocusKey)}
                  placeholder={
                    dilucionCreatinuria && esCreatininuria(codigoUpper)
                      ? 'Valor CM260 · Enter → siguiente'
                      : esFormula
                        ? 'Ej. 70 · Enter → siguiente'
                        : 'Ej. 120 o Positivo · Enter → siguiente'
                  }
                  helperText={
                    dilucionCreatinuria && esCreatininuria(codigoUpper)
                      ? 'Orina 1:20 — se informa ×20'
                      : undefined
                  }
                  inputProps={{ 'data-carga-focus': valorFocusKey }}
                  InputProps={
                    esFormula
                      ? {
                          endAdornment: (
                            <InputAdornment position="end">%</InputAdornment>
                          ),
                        }
                      : undefined
                  }
                  sx={{ flex: '1 1 120px', minWidth: 100 }}
                />
                {valorDisplayExtra ? (
                  <Typography variant="caption" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
                    {valorDisplayExtra.replace(/^ · /, '')}
                  </Typography>
                ) : null}
              </Box>
            </TableCell>
          )}
          <TableCell sx={{ whiteSpace: 'nowrap' }}>
            <Typography variant="body2">
              {esFormula && FORMULA_LEUCO_CODIGOS.has(codigoUpper) && valorDisplayExtra
                ? '—'
                : unidadLabel}
            </Typography>
          </TableCell>
          <TableCell>
            <ResultadoRangoInfo resultado={r} />
          </TableCell>
          {showOrden && (
            <TableCell
              rowSpan={ordenOpts.ordenRowSpan}
              align="left"
              sx={{ verticalAlign: 'middle', width: 52, px: 0.5 }}
            >
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
                <IconButton
                  size="small"
                  aria-label="Subir en informe"
                  disabled={savingOrden || (ordenOpts.grupoIndex ?? 0) <= 0}
                  onClick={() => void moveGrupoInforme(ordenOpts.grupoKey!, 'up')}
                >
                  <KeyboardArrowUpIcon fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  aria-label="Bajar en informe"
                  disabled={
                    savingOrden || (ordenOpts.grupoIndex ?? 0) >= ordenGrupos.length - 1
                  }
                  onClick={() => void moveGrupoInforme(ordenOpts.grupoKey!, 'down')}
                >
                  <KeyboardArrowDownIcon fontSize="small" />
                </IconButton>
              </Box>
            </TableCell>
          )}
        </TableRow>
      );
    },
    [
      draft,
      tiposExamenMap,
      resolveUnidad,
      handleEnterNext,
      formulaProgress,
      focusedSysmexKey,
      moveGrupoInforme,
      ordenGrupos.length,
      savingOrden,
      previosPorTipo,
      fechaExtraccionPorResultado,
    ]
  );

  const diagnosticoLabel = (orden.diagnostico || '').trim() || '—';

  if (resultados.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 2 }}>
        Esta orden no tiene resultados generados (tipos/paneles vacíos al crear).
      </Typography>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Typography variant="body2" color="text.secondary">
          <strong>Fecha de solicitud:</strong> {fechaSolicitudLabel}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          <strong>Fecha de extracción:</strong> {fechaExtraccionLabel}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          <strong>Diagnóstico:</strong> {diagnosticoLabel}
        </Typography>
      </Box>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Typography variant="subtitle2">Resultados anteriores del paciente</Typography>
        <Button size="small" disabled={loadingHistorial} onClick={actualizarHistorial}>
          {loadingHistorial ? 'Consultando historial…' : 'Actualizar historial'}
        </Button>
      </Box>
      {errorHistorial && <Alert severity="warning" sx={{ mb: 2 }}>{errorHistorial}</Alert>}
      {!loadingHistorial && !errorHistorial && resultados.length > 0 &&
        Array.from(previosPorTipo.values()).every((previos) => previos.length === 0) && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            No se encontraron resultados anteriores informados para los ensayos de esta orden.
          </Typography>
        )}
      {editable ? (
        <>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1, mb: 1 }}>
            <Typography variant="h6">Resultados</Typography>
            <Chip
              size="small"
              label={`${progreso.conValor}/${progreso.total} resultados`}
              color={progreso.conValor === progreso.total ? 'success' : 'default'}
              variant="outlined"
            />
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Fuera de rango y crítico se calculan al guardar. Usá las flechas a la derecha para ordenar
            paneles en el informe (por defecto: hemograma primero, orina al final).
          </Typography>
          {muestrasProcesables.length === 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              No hay muestras listas para asociar. Usá <strong>Imprimir etiquetas</strong> y luego
              confirmá el ingreso escaneando en <strong>Recepción</strong>.
            </Alert>
          )}
          {iqcBloqueaCarga && (
            <Alert severity="error" sx={{ mb: 2 }}>
              <Typography variant="body2" fontWeight={600}>
                IQC no vigente — no se pueden guardar resultados
                {iqcPrecheck?.equipos?.length
                  ? ` (${iqcPrecheck.equipos.map((e) => e.codigo).join(', ')})`
                  : iqcPrecheck?.equipo
                    ? ` (${iqcPrecheck.equipo.codigo})`
                    : ''}
                .
              </Typography>
              <Typography variant="body2" component="span">
                {(iqcPrecheck?.problemas || []).join('; ')}. Andá a{' '}
                <strong>Control de calidad</strong>, registrá corridas ACEPTADAS en cada equipo
                indicado y volvé a intentar.
              </Typography>
            </Alert>
          )}
          {!iqcBloqueaCarga && iqcSinConfiguracion && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              <Typography variant="body2" fontWeight={600}>
                IQC no configurado
              </Typography>
              <Typography variant="body2">
                Esta orden no tiene materiales ni productos de control asociados a sus ensayos.
                No implica control satisfactorio: configurá QC en Control de calidad cuando
                corresponda.
              </Typography>
            </Alert>
          )}
          {grupos.map((grupo) => {
            const grupoIndex = ordenGrupos.indexOf(grupo.key);
            const usaTicket = grupo.resultados.some((r) => {
              const te = tiposExamenMap.get(r.tipo_examen);
              return usesTicketEntry(te, r.tipo_examen_codigo);
            });
            const usaFormula = grupo.resultados.some((r) => {
              const te = tiposExamenMap.get(r.tipo_examen);
              return isFormulaPercent(te, r.tipo_examen_codigo);
            });
            const esGrupoHemograma = grupo.codigo === PANEL_HEMOGRAMA;
            return (
              <Box key={grupo.key} sx={{ mb: 3 }}>
                <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1 }}>
                  {grupo.titulo}
                  {grupo.codigo ? (
                    <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                      ({grupo.codigo})
                    </Typography>
                  ) : null}
                </Typography>
                {usaTicket && (
                  <Alert severity="info" sx={{ mb: 1 }}>
                    Entrada por ticket analizador: ingrese sin punto decimal
                    (WBC 9,3 → <strong>93</strong>; HGB 7,3 → <strong>73</strong>; RBC 2,37 → <strong>237</strong>).
                    {usaFormula && (
                      <>
                        {' '}
                        En la <strong>fórmula leucocitaria</strong> (%), ingrese el entero directo
                        (cayados <strong>70</strong> → informe <strong>70</strong>). Al lado del %
                        se muestra el recuento <strong>absoluto</strong> (abs. …/mm³). Al escribir
                        verás cuánto falta para <strong>100%</strong>.
                      </>
                    )}
                  </Alert>
                )}
                <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto' }}>
                  <Table
                    size="small"
                    sx={{
                      tableLayout: 'fixed',
                      width: '100%',
                      '& .MuiTableCell-root': {
                        textAlign: 'left',
                        verticalAlign: 'top',
                      },
                      '& tbody .MuiTableCell-root[rowspan]': {
                        verticalAlign: 'middle',
                      },
                    }}
                  >
                    <CargaColGroup ticket={usaTicket} />
                    <TableHead>
                      <TableRow>
                        <TableCell>Examen</TableCell>
                        {usaTicket ? (
                          <>
                            <TableCell>Valor ticket</TableCell>
                            <TableCell>Informe</TableCell>
                          </>
                        ) : (
                          <TableCell>Valor</TableCell>
                        )}
                        <TableCell>Unidad</TableCell>
                        <TableCell>Referencia</TableCell>
                        <TableCell align="left">Informe</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {grupo.resultados.map((r, idx) =>
                        renderEditRow(
                          r,
                          idx === 0
                            ? {
                                ordenRowSpan: grupo.resultados.length,
                                grupoKey: grupo.key,
                                grupoIndex,
                              }
                            : undefined
                        )
                      )}
                    </TableBody>
                  </Table>
                </TableContainer>

                {esGrupoHemograma && (
                  <Box sx={{ mt: 2 }}>
                    <Box sx={{ mb: 1, display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
                      <Button
                        variant="outlined"
                        size="small"
                        onClick={() => void handleSugerirConclusion()}
                        disabled={sugeriendo || saving}
                      >
                        {sugeriendo ? 'Sugiriendo…' : 'Sugerir conclusión'}
                      </Button>
                      {sugerenciaMeta?.marcado && (
                        <Chip
                          size="small"
                          color="info"
                          variant="outlined"
                          label={`Sugerencia (no validada) · ${sugerenciaMeta.fuente}`}
                        />
                      )}
                    </Box>
                    <TextField
                      fullWidth
                      multiline
                      minRows={2}
                      label="Conclusión / observaciones del hemograma"
                      value={observacionesOrden}
                      onChange={(ev) => {
                        setObservacionesOrden(ev.target.value);
                        if (sugerenciaMeta) {
                          setSugerenciaMeta((m) => (m ? { ...m, marcado: true } : m));
                        }
                      }}
                      onKeyDown={(ev) => {
                        if (ev.key === 'Enter' && !ev.shiftKey && !ev.nativeEvent.isComposing) {
                          ev.preventDefault();
                          focusNextField('observaciones');
                        }
                      }}
                      placeholder="Ej.: Anemia normocítica normocrómica, con trombocitopenia leve y anisocitosis."
                      helperText="Enter → siguiente · Shift+Enter → nueva línea. La sugerencia es borrador; el bioquímico debe revisar y guardar."
                      inputProps={{ 'data-carga-focus': 'observaciones' }}
                    />
                  </Box>
                )}
              </Box>
            );
          })}

          {!esHemograma && (
            <TextField
              fullWidth
              multiline
              minRows={2}
              label="Observaciones de la muestra / orden"
              value={observacionesOrden}
              onChange={(ev) => setObservacionesOrden(ev.target.value)}
              onKeyDown={(ev) => {
                if (ev.key === 'Enter' && !ev.shiftKey && !ev.nativeEvent.isComposing) {
                  ev.preventDefault();
                  focusNextField('observaciones');
                }
              }}
              placeholder="Notas generales del informe (aplican a toda la orden)"
              helperText="Enter → guardar · Shift+Enter → nueva línea"
              inputProps={{ 'data-carga-focus': 'observaciones' }}
              sx={{ mb: 2 }}
            />
          )}

          <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'center' }}>
            <Button
              ref={guardarBtnRef}
              variant="contained"
              onClick={() => void handleGuardar(false)}
              disabled={saving || iqcBloqueaCarga}
              onKeyDown={(ev) => {
                if (ev.key === 'Enter' && !saving && !iqcBloqueaCarga) {
                  ev.preventDefault();
                  void handleGuardar(false);
                }
              }}
            >
              Guardar avance
            </Button>
            <Button
              variant="outlined"
              color="info"
              onClick={() => void handleGuardar(true)}
              disabled={saving || !puedeInformarParcial}
            >
              Guardar e informar parcialmente
            </Button>
            {mostrarValidar && onValidar && (
              <Tooltip title={validarDeshabilitado ? validarDeshabilitadoMotivo || '' : ''}>
                <span>
                  <Button
                    variant="contained"
                    color="success"
                    disabled={saving || validando || validarDeshabilitado}
                    onClick={() => void onValidar()}
                  >
                    {validando ? 'Validando…' : 'Validar y liberar'}
                  </Button>
                </span>
              </Tooltip>
            )}
          </Box>
          {progresoPantalla.conValor < progresoPantalla.total && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Guardá solo los valores que tengas listos. Usá{' '}
            <strong>Guardar e informar parcialmente</strong> para marcar{' '}
            <strong>Informe parcial</strong> (el médico lo ve en pantalla; habilita
            descargar/enviar PDF parcial). Al completar todos los ensayos exigibles, la orden
            pasa a <strong>Listo para validar</strong>; el informe definitivo tras{' '}
            <strong>Validar y liberar</strong>.
          </Typography>
          )}
          {orden.estado === 'LISTO_PARA_VALIDAR' && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Orden <strong>lista para validar</strong>. Podés corregir valores; el bioquímico libera con{' '}
            <strong>Validar y liberar</strong>.
          </Typography>
          )}
        </>
      ) : (
        <>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Resultados
          </Typography>
          <Box sx={{ mb: 2 }}>
            <ResultadosOrdenLista
              resultados={resultados}
              orden={orden}
              observaciones={orden.observaciones}
              modo="clinico"
            />
          </Box>
          <Alert severity="info" sx={{ mb: 2 }}>
            {orden.estado === 'PENDIENTE' ? (
              <>
                La orden está <strong>pendiente</strong>. Usá <strong>Imprimir etiquetas</strong> y confirmá
                la recepción escaneando cada tubo en <strong>Recepción</strong> antes de cargar resultados.
              </>
            ) : orden.estado === 'INFORMADO_PARCIAL' && !permitirEdicion ? (
              <>
                La orden está en <strong>Informe parcial</strong>. Podés seguir cargando resultados.
                El médico ve estos valores en pantalla; ya se puede descargar o enviar el PDF
                parcial. El informe definitivo es tras <strong>Validar y liberar</strong>.
              </>
            ) : orden.estado === 'FINALIZADO' ? (
              <>
                Orden <strong>validada</strong>
                {(() => {
                  const val = (orden.resultados || []).find((r) => r.validado_por_nombre || r.fecha_validacion);
                  if (!val) return null;
                  const quien = val.validado_por_nombre || 'bioquímico';
                  const cuando = val.fecha_validacion
                    ? new Date(val.fecha_validacion).toLocaleString('es-AR')
                    : '';
                  return (
                    <>
                      {' '}
                      — Validado por <strong>{quien}</strong>
                      {cuando ? ` (${cuando})` : ''}.
                    </>
                  );
                })()}{' '}
                Los resultados están bloqueados. Un bioquímico o admin puede usar{' '}
                <strong>Reabrir para corregir</strong> y volver a validar.
              </>
            ) : !canOperate ? (
              'Solo lectura: se requiere rol laboratorio, bioquímico o administrador para cargar resultados.'
            ) : (
              'La carga de valores no está disponible en el estado actual de la orden.'
            )}
          </Alert>
        </>
      )}

      <AnalisisLongitudinalPanel
        ordenId={orden.id}
        estadoOrden={orden.estado}
        totalResultados={progreso.conValor}
        resultadosFingerprint={analisisFingerprint}
      />
    </Box>
  );
};

function emptyDraft(): DraftCargaRow {
  return {
    valor: '',
    valor_sysmex: '',
    valor_numerico: '',
    unidad: '',
    muestra_id: null,
  };
}

export default CargaResultadosLims;
