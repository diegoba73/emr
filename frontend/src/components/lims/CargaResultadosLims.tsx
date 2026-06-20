import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { LimsTipoExamen, LimsTipoMuestra, MuestraTransaccional, SolicitudExamenLims } from '../../types/lims';
import {
  formatLimsHttpError,
  getTiposExamenMap,
  listTiposMuestraLims,
  postCargarResultados,
} from '../../services/limsApi';
import ResultadoRangoInfo from './ResultadoRangoInfo';
import ResultadosOrdenLista from './ResultadosOrdenLista';
import {
  buildCargarResultadoPayload,
  filterMuestrasProcesables,
  formatMuestraSelectLabel,
  getTipoExamenCatalog,
  muestrasCompatiblesParaTipo,
  validateCargaResultadosMuestra,
  type DraftCargaRow,
} from '../../utils/limsCargaMuestra';

export interface CargaResultadosLimsProps {
  orden: SolicitudExamenLims;
  muestras: MuestraTransaccional[];
  canOperate: boolean;
  onGuardado: (o: SolicitudExamenLims) => void;
}

const CargaResultadosLims: React.FC<CargaResultadosLimsProps> = ({ orden, muestras, canOperate, onGuardado }) => {
  const resultados = orden.resultados || [];
  const [draft, setDraft] = useState<Record<number, DraftCargaRow>>({});
  const [saving, setSaving] = useState(false);
  const [tiposExamenMap, setTiposExamenMap] = useState<Map<number, LimsTipoExamen>>(new Map());
  const [tiposMuestraMap, setTiposMuestraMap] = useState<Map<number, LimsTipoMuestra>>(new Map());

  const muestrasProcesables = useMemo(() => filterMuestrasProcesables(muestras), [muestras]);

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
    const next: Record<number, DraftCargaRow> = {};
    for (const r of resultados) {
      next[r.id] = {
        valor: r.valor_obtenido ?? '',
        valor_numerico:
          r.valor_numerico !== null && r.valor_numerico !== undefined ? String(r.valor_numerico) : '',
        unidad: r.unidad ?? '',
        es_patologico: !!r.es_patologico,
        es_critico: !!r.es_critico,
        observaciones: r.observaciones ?? '',
        muestra_id: r.muestra_id ?? null,
      };
    }
    setDraft(next);
  }, [orden]);

  const editable =
    canOperate && ['PENDIENTE', 'TOMA_MUESTRA', 'EN_PROCESO'].includes(orden.estado) && resultados.length > 0;

  const setRow = (id: number, patch: Partial<DraftCargaRow>) => {
    setDraft((d) => ({ ...d, [id]: { ...d[id], ...patch } }));
  };

  const handleGuardar = async () => {
    const payload = resultados.map((r) => buildCargarResultadoPayload(r.id, draft[r.id] || emptyDraft()));

    const sinValor = payload.filter((p) => !p.valor.trim());
    if (sinValor.length) {
      toast.error(
        'Cada resultado debe tener valor textual. Si solo ingresás valor numérico, se copiará al guardar; revisá las filas vacías.'
      );
      return;
    }

    const errMuestra = validateCargaResultadosMuestra(resultados, draft, tiposExamenMap, muestras);
    if (errMuestra) {
      toast.error(errMuestra);
      return;
    }

    setSaving(true);
    try {
      const updated = await postCargarResultados(orden.id, payload);
      toast.success('Resultados guardados');
      onGuardado(updated);
    } catch (e) {
      toast.error(formatLimsHttpError(e, 'cargar_resultados'));
    } finally {
      setSaving(false);
    }
  };

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
        El backend calcula patológico, crítico y rangos al guardar. Los valores mostrados reflejan el último guardado.
      </Typography>
      <Box sx={{ mb: 3 }}>
        <ResultadosOrdenLista resultados={resultados} muestras={muestras} tiposMuestraMap={tiposMuestraMap} />
      </Box>

      {editable && (
        <>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Cargar / editar
          </Typography>
          {muestrasProcesables.length === 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              No hay muestras en estado RECIBIDA, CONSERVADA o EN_PROCESO para esta orden. Registre y reciba muestras
              antes de asociarlas a resultados que lo requieran.
            </Alert>
          )}
          <Alert severity="info" sx={{ mb: 2 }}>
            El valor textual es obligatorio para considerar el resultado cargado. Si dejás el texto vacío pero completás
            valor numérico, al guardar se usará el número como texto. Unidad vacía: el backend puede aplicar la unidad
            por defecto del examen. Los exámenes marcados como &quot;Requiere muestra&quot; deben tener una muestra
            asociada antes de guardar.
          </Alert>
          <TableContainer component={Paper} variant="outlined" sx={{ overflowX: 'auto' }}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Examen</TableCell>
                  <TableCell>Ref. catálogo</TableCell>
                  <TableCell>Valor texto</TableCell>
                  <TableCell>Valor num.</TableCell>
                  <TableCell>Unidad</TableCell>
                  <TableCell>Patológico</TableCell>
                  <TableCell>Crítico</TableCell>
                  <TableCell>Obs.</TableCell>
                  <TableCell>Muestra</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {resultados.map((r) => {
                  const row = draft[r.id] || emptyDraft();
                  const criticoRow = row.es_critico;
                  const te = getTipoExamenCatalog(r.tipo_examen, tiposExamenMap);
                  const requiereMuestra = !!te?.requiere_muestra;
                  const opcionesMuestra = muestrasCompatiblesParaTipo(
                    muestrasProcesables,
                    te?.tipo_muestra_requerida
                  );
                  const sinOpciones = requiereMuestra && opcionesMuestra.length === 0;

                  return (
                    <TableRow
                      key={r.id}
                      sx={{
                        bgcolor: criticoRow
                          ? 'rgba(211, 47, 47, 0.08)'
                          : row.es_patologico
                            ? 'rgba(237, 108, 2, 0.06)'
                            : undefined,
                      }}
                    >
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
                            <Chip
                              size="small"
                              label={`Tipo requerido: ${te.tipo_muestra_nombre}`}
                              variant="outlined"
                            />
                          )}
                        </Box>
                      </TableCell>
                      <TableCell sx={{ maxWidth: 140 }}>
                        <ResultadoRangoInfo resultado={r} />
                      </TableCell>
                      <TableCell>
                        <TextField
                          size="small"
                          value={row.valor}
                          onChange={(ev) => setRow(r.id, { valor: ev.target.value })}
                          placeholder="Ej. 120 o Positivo"
                        />
                      </TableCell>
                      <TableCell>
                        <TextField
                          size="small"
                          type="text"
                          inputMode="decimal"
                          value={row.valor_numerico}
                          onChange={(ev) => setRow(r.id, { valor_numerico: ev.target.value })}
                          placeholder="Opcional"
                        />
                      </TableCell>
                      <TableCell>
                        <TextField
                          size="small"
                          value={row.unidad}
                          onChange={(ev) => setRow(r.id, { unidad: ev.target.value })}
                          placeholder={r.unidad ? '' : 'Opcional'}
                        />
                      </TableCell>
                      <TableCell>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={row.es_patologico}
                              onChange={(ev) => setRow(r.id, { es_patologico: ev.target.checked })}
                            />
                          }
                          label=""
                        />
                      </TableCell>
                      <TableCell>
                        <FormControlLabel
                          control={
                            <Switch
                              color="error"
                              checked={row.es_critico}
                              onChange={(ev) => setRow(r.id, { es_critico: ev.target.checked })}
                            />
                          }
                          label=""
                        />
                      </TableCell>
                      <TableCell>
                        <TextField
                          size="small"
                          value={row.observaciones}
                          onChange={(ev) => setRow(r.id, { observaciones: ev.target.value })}
                        />
                      </TableCell>
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
                            Sin muestras compatibles procesables.
                          </Typography>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
          <Box sx={{ mt: 2 }}>
            <Button variant="contained" onClick={handleGuardar} disabled={saving}>
              Guardar resultados
            </Button>
          </Box>
        </>
      )}

      {!editable && canOperate && (
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
          La carga de valores solo está disponible en estados Pendiente, Toma de muestra o En proceso.
        </Typography>
      )}
    </Box>
  );
};

function emptyDraft(): DraftCargaRow {
  return {
    valor: '',
    valor_numerico: '',
    unidad: '',
    es_patologico: false,
    es_critico: false,
    observaciones: '',
    muestra_id: null,
  };
}

export default CargaResultadosLims;
