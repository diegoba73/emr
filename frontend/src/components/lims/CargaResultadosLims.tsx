import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  FormControl,
  IconButton,
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
  TextField,
  Typography,
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import toast from 'react-hot-toast';
import type { LimsTipoExamen, LimsTipoMuestra, MuestraTransaccional, SolicitudExamenLims } from '../../types/lims';
import {
  getTiposExamenMap,
  listTiposMuestraLims,
  patchOrdenInformeOrden,
  postCargarResultados,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { groupResultadosPorPanel } from '../../utils/limsResultadosPanel';
import {
  applyOrdenGrupos,
  reorderOrdenGrupos,
  resolveOrdenGrupos,
} from '../../utils/limsOrdenInforme';
import ResultadoRangoInfo from './ResultadoRangoInfo';
import ResultadosOrdenLista from './ResultadosOrdenLista';
import AnalisisLongitudinalPanel from './AnalisisLongitudinalPanel';
import {
  buildCargarResultadoPayload,
  draftRowHasValue,
  draftSysmexTicketFromResultado,
  filterMuestrasProcesables,
  formatMuestraSelectLabel,
  getTipoExamenCatalog,
  muestrasCompatiblesParaTipo,
  suggestMuestraIdForResultado,
  validateCargaResultadosMuestra,
  validateCargaResultadosValores,
  type DraftCargaRow,
} from '../../utils/limsCargaMuestra';
import { countResultadosConValor } from '../../utils/limsOrdenResultados';
import { ordenPuedeCargarResultados } from '../../utils/limsEstadosOrden';
import {
  computeFormulaProgress,
  formatFormulaProgressLabel,
  isFormulaPercent,
  previewTicketInforme,
  usesTicketEntry,
} from '../../utils/entradaResultados';
import { getSysmexUnidad } from '../../utils/sysmexHemograma';

export interface CargaResultadosLimsProps {
  orden: SolicitudExamenLims;
  muestras: MuestraTransaccional[];
  canOperate: boolean;
  /** Si false, oculta el formulario de carga/edición (solo lectura). */
  permitirEdicion?: boolean;
  onGuardado: (o: SolicitudExamenLims) => void;
}

/** Claves de foco para navegación con Enter en la grilla de carga. */
function buildCargaFocusOrder(
  grupos: ReturnType<typeof groupResultadosPorPanel>,
  tiposExamenMap: Map<number, LimsTipoExamen>
): string[] {
  const keys: string[] = [];
  for (const grupo of grupos) {
    for (const r of grupo.resultados) {
      const te = tiposExamenMap.get(r.tipo_examen);
      if (usesTicketEntry(te, r.tipo_examen_codigo)) {
        keys.push(`sysmex-${r.id}`);
      } else {
        keys.push(`valor-${r.id}`, `num-${r.id}`);
      }
    }
  }
  keys.push('observaciones');
  return keys;
}

function focusCargaField(key: string): void {
  const input = document.querySelector<HTMLInputElement | HTMLTextAreaElement>(
    `[data-carga-focus="${key}"]`
  );
  if (!input) return;
  input.focus();
  if (input instanceof HTMLInputElement && input.type !== 'hidden') {
    input.select();
  } else if (input instanceof HTMLTextAreaElement) {
    input.select();
  }
}

const CargaResultadosLims: React.FC<CargaResultadosLimsProps> = ({
  orden,
  muestras,
  canOperate,
  permitirEdicion = true,
  onGuardado,
}) => {
  const resultados = orden.resultados || [];
  const [draft, setDraft] = useState<Record<number, DraftCargaRow>>({});
  const [observacionesOrden, setObservacionesOrden] = useState('');
  const [saving, setSaving] = useState(false);
  const [tiposExamenMap, setTiposExamenMap] = useState<Map<number, LimsTipoExamen>>(new Map());
  const [tiposMuestraMap, setTiposMuestraMap] = useState<Map<number, LimsTipoMuestra>>(new Map());

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
      if (idx < focusOrder.length - 1) {
        focusCargaField(focusOrder[idx + 1]);
        return;
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
        const [te, tm] = await Promise.all([getTiposExamenMap(), listTiposMuestraLims()]);
        if (cancelled) return;
        setTiposExamenMap(te);
        setTiposMuestraMap(new Map(tm.map((t) => [t.id, t])));
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
        const built: DraftCargaRow = {
          valor: r.valor_obtenido ?? '',
          valor_sysmex: draftSysmexTicketFromResultado(r, te, codigo),
          valor_numerico:
            r.valor_numerico !== null && r.valor_numerico !== undefined ? String(r.valor_numerico) : '',
          unidad: unidadCatalogo,
          muestra_id: muestraId,
        };
        const prevRow = prev[r.id];
        if (prevRow) {
          if (prevRow.valor_sysmex.trim()) built.valor_sysmex = prevRow.valor_sysmex;
          if (prevRow.valor.trim()) built.valor = prevRow.valor;
          if (prevRow.valor_numerico.trim()) built.valor_numerico = prevRow.valor_numerico;
          if (prevRow.unidad.trim()) built.unidad = prevRow.unidad;
          if (prevRow.muestra_id != null) built.muestra_id = prevRow.muestra_id;
        }
        next[r.id] = built;
      }
      return next;
    });
    setObservacionesOrden(orden.observaciones ?? '');
  }, [orden, resultados, muestrasProcesables, tiposExamenMap]);

  const progreso = useMemo(() => countResultadosConValor(orden), [orden]);

  const editable =
    permitirEdicion &&
    canOperate &&
    ordenPuedeCargarResultados(orden.estado) &&
    resultados.length > 0;

  const setRow = (id: number, patch: Partial<DraftCargaRow>) => {
    setDraft((d) => ({ ...d, [id]: { ...d[id], ...patch } }));
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

  const handleGuardar = async (informarParcial = false) => {
    const filasAGuardar = resultados.filter((r) => {
      const te = getTipoExamenCatalog(r.tipo_examen, tiposExamenMap);
      const row = draft[r.id] || emptyDraft();
      return draftRowHasValue(row, te, r.tipo_examen_codigo);
    });

    if (!filasAGuardar.length) {
      toast.error('Ingresá al menos un valor para guardar.');
      return;
    }

    const payload = filasAGuardar.map((r) => {
      const te = getTipoExamenCatalog(r.tipo_examen, tiposExamenMap);
      return buildCargarResultadoPayload(r.id, draft[r.id] || emptyDraft(), te, r.tipo_examen_codigo);
    });

    const errMuestra = validateCargaResultadosMuestra(
      resultados,
      draft,
      tiposExamenMap,
      muestras,
      filasAGuardar.map((r) => r.id)
    );
    if (errMuestra) {
      toast.error(errMuestra);
      return;
    }

    const errValores = validateCargaResultadosValores(
      resultados,
      draft,
      tiposExamenMap,
      filasAGuardar.map((r) => r.id)
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
        toast.success('Resultados guardados e informados parcialmente');
      } else if (countResultadosConValor(updated).conValor === (updated.resultados || []).length) {
        toast.success('Resultados completos — listos para validación del bioquímico');
      } else {
        toast.success('Avance guardado');
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

  const renderEditRow = useCallback(
    (
      r: (typeof resultados)[number],
      ordenOpts?: { ordenRowSpan?: number; grupoKey?: string; grupoIndex?: number }
    ) => {
      const row = draft[r.id] || emptyDraft();
      const te = getTipoExamenCatalog(r.tipo_examen, tiposExamenMap);
      const requiereMuestra = !!te?.requiere_muestra;
      const opcionesMuestra = muestrasCompatiblesParaTipo(
        muestrasProcesables,
        te?.tipo_muestra_requerida,
        te?.tipo_contenedor
      );
      const sinOpciones = requiereMuestra && opcionesMuestra.length === 0;
      const ticketEntry = usesTicketEntry(te, r.tipo_examen_codigo);
      const informePreview = ticketEntry
        ? previewTicketInforme(te, row.valor_sysmex, r.tipo_examen_codigo)
        : null;
      const unidadLabel = resolveUnidad(r, te);
      const sysmexFocusKey = `sysmex-${r.id}`;
      const valorFocusKey = `valor-${r.id}`;
      const numFocusKey = `num-${r.id}`;
      const esFormula = isFormulaPercent(te, r.tipo_examen_codigo);
      const mostrarIndicadorFormula = esFormula && focusedSysmexKey === sysmexFocusKey;
      const showOrden = ordenOpts?.ordenRowSpan !== undefined;

      return (
        <TableRow key={r.id}>
          <TableCell>
            <Typography variant="body2" fontWeight={600}>
              {r.tipo_examen_nombre || r.tipo_examen}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              {r.tipo_examen_codigo}
            </Typography>
            <Box sx={{ mt: 0.5, display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {requiereMuestra && (
                <Chip size="small" color="warning" label="Requiere muestra" variant="outlined" />
              )}
              {te?.tipo_muestra_nombre && (
                <Chip size="small" label={`Tipo requerido: ${te.tipo_muestra_nombre}`} variant="outlined" />
              )}
            </Box>
          </TableCell>
          <TableCell sx={{ maxWidth: 140 }}>
            <ResultadoRangoInfo resultado={r} />
          </TableCell>
          <TableCell sx={{ whiteSpace: 'nowrap' }}>
            <Typography variant="body2">{unidadLabel}</Typography>
          </TableCell>
          {ticketEntry ? (
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
                    sx={{ minWidth: 88, flex: '1 1 auto' }}
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
                  {informePreview ?? '—'}
                </Typography>
              </TableCell>
            </>
          ) : (
            <>
              <TableCell>
                <TextField
                  size="small"
                  value={row.valor}
                  onChange={(ev) => setRow(r.id, { valor: ev.target.value })}
                  onKeyDown={handleEnterNext(valorFocusKey)}
                  placeholder="Ej. 120 o Positivo"
                  inputProps={{ 'data-carga-focus': valorFocusKey }}
                />
              </TableCell>
              <TableCell>
                <TextField
                  size="small"
                  type="text"
                  inputMode="decimal"
                  value={row.valor_numerico}
                  onChange={(ev) => setRow(r.id, { valor_numerico: ev.target.value })}
                  onKeyDown={handleEnterNext(numFocusKey)}
                  placeholder="Opcional"
                  inputProps={{ 'data-carga-focus': numFocusKey }}
                />
              </TableCell>
            </>
          )}
          <TableCell sx={{ minWidth: 220 }}>
            <FormControl size="small" fullWidth error={sinOpciones && row.muestra_id == null}>
              <InputLabel>Muestra</InputLabel>
              <Select
                label="Muestra"
                value={row.muestra_id == null ? '' : String(row.muestra_id)}
                onChange={(ev) => {
                  const raw = ev.target.value;
                  const str = typeof raw === 'number' ? String(raw) : raw;
                  setRow(r.id, { muestra_id: str === '' ? null : Number(str) });
                }}
              >
                {!requiereMuestra && (
                  <MenuItem value="">
                    <em>Sin muestra</em>
                  </MenuItem>
                )}
                {opcionesMuestra.map((m) => (
                  <MenuItem key={m.id} value={m.id}>
                    {formatMuestraSelectLabel(m, tiposMuestraMap.get(m.tipo_muestra)?.nombre)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {sinOpciones && (
              <Typography variant="caption" color="error" display="block">
                Sin muestras compatibles. Tomá la muestra desde acciones de orden.
              </Typography>
            )}
          </TableCell>
          {showOrden && (
            <TableCell
              rowSpan={ordenOpts.ordenRowSpan}
              align="right"
              sx={{ verticalAlign: 'middle', width: 52, px: 0.5 }}
            >
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
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
      muestrasProcesables,
      tiposExamenMap,
      tiposMuestraMap,
      resolveUnidad,
      handleEnterNext,
      formulaProgress,
      focusedSysmexKey,
      moveGrupoInforme,
      ordenGrupos.length,
      savingOrden,
    ]
  );

  if (resultados.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 2 }}>
        Esta orden no tiene resultados generados (tipos/paneles vacíos al crear).
      </Typography>
    );
  }

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Resultados cargados
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Patológico y crítico se calculan automáticamente al guardar, según los rangos del catálogo.
      </Typography>
      <Box sx={{ mb: 3 }}>
        <ResultadosOrdenLista
          resultados={resultados}
          muestras={muestras}
          tiposMuestraMap={tiposMuestraMap}
          orden={orden}
        />
      </Box>

      <AnalisisLongitudinalPanel
        ordenId={orden.id}
        estadoOrden={orden.estado}
        totalResultados={progreso.conValor}
        resultadosFingerprint={analisisFingerprint}
      />

      {editable && (
        <>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1, mb: 2 }}>
            <Typography variant="h6">Cargar / editar</Typography>
            <Chip
              size="small"
              label={`${progreso.conValor}/${progreso.total} resultados`}
              color={progreso.conValor === progreso.total ? 'success' : 'default'}
              variant="outlined"
            />
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Usá las flechas a la derecha para ordenar paneles y exámenes en el informe (los paneles se
            mueven completos). Por defecto: hemograma primero, orina al final.
          </Typography>
          {muestrasProcesables.length === 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              No hay muestras listas para asociar. Usá <strong>Imprimir etiquetas</strong> y luego
              confirmá el ingreso escaneando en <strong>Recepción</strong>.
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
                        (cayados <strong>70</strong> → informe <strong>70</strong>). Al escribir verás
                        al lado cuánto falta para <strong>100%</strong>.
                      </>
                    )}
                  </Alert>
                )}
                <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto' }}>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Examen</TableCell>
                        <TableCell>Referencia</TableCell>
                        <TableCell>Unidad</TableCell>
                        {usaTicket ? (
                          <>
                            <TableCell>Valor ticket</TableCell>
                            <TableCell>Informe</TableCell>
                          </>
                        ) : (
                          <>
                            <TableCell>Valor</TableCell>
                            <TableCell>Valor num.</TableCell>
                          </>
                        )}
                        <TableCell>Muestra</TableCell>
                        <TableCell align="right" sx={{ width: 52 }}>
                          Informe
                        </TableCell>
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
              </Box>
            );
          })}

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
            sx={{ mt: 2, mb: 2 }}
          />

          <Box sx={{ mt: 2, display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Button
              ref={guardarBtnRef}
              variant="contained"
              onClick={() => void handleGuardar(false)}
              disabled={saving}
              onKeyDown={(ev) => {
                if (ev.key === 'Enter' && !saving) {
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
              disabled={saving}
            >
              Guardar e informar parcialmente
            </Button>
          </Box>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Guardá solo los valores que tengas listos. Usá{' '}
            <strong>Guardar e informar parcialmente</strong> cuando el médico solicite los resultados
            disponibles antes de completar la orden; después podés enviar el PDF desde acciones de orden.
          </Typography>
        </>
      )}

      {!editable && (
        <Alert severity="info" sx={{ mt: 2 }}>
          {orden.estado === 'PENDIENTE' ? (
            <>
              La orden está <strong>pendiente</strong>. Usá <strong>Imprimir etiquetas</strong> y confirmá
              la recepción escaneando cada tubo en <strong>Recepción</strong> antes de cargar resultados.
            </>
          ) : orden.estado === 'INFORMADO_PARCIAL' && !permitirEdicion ? (
            <>
              La orden está <strong>informada parcialmente</strong>. Podés seguir cargando resultados o enviar el
              informe parcial al paciente desde acciones de orden.
            </>
          ) : orden.estado === 'FINALIZADO' ? (
            <>
              Orden <strong>validada y bloqueada</strong>
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
              Los resultados no se pueden modificar.
            </>
          ) : !canOperate ? (
            'Solo lectura: se requiere rol laboratorio, bioquímico o administrador para cargar resultados.'
          ) : (
            'La carga de valores no está disponible en el estado actual de la orden.'
          )}
        </Alert>
      )}

      {!editable && orden.observaciones?.trim() && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Observaciones
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap' }}>
            {orden.observaciones}
          </Typography>
        </Box>
      )}
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
