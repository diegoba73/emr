import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { LimsTipoExamen, LimsTipoMuestra, TipoExamenLimsWriteBody } from '../../types/lims';
import {
  createTipoExamenLims,
  formatDrfError,
  listTiposExamenLims,
  listTiposMuestraLims,
  patchTipoExamenLims,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import {
  FORMATO_INFORME_LABELS,
  MODO_ENTRADA_LABELS,
  modoEntradaResumen,
  type FormatoInformeEntrada,
  type ModoEntradaResultado,
} from '../../utils/entradaResultados';
import { canAccessLimsModule, canEditLimsCatalogos } from '../../utils/limsAccess';

type ExamenForm = {
  codigo: string;
  nombre: string;
  abreviatura: string;
  tipo_muestra_requerida: number | '';
  tipo_resultado: 'TEXTO' | 'NUMERICO' | 'CUALITATIVO';
  metodo: string;
  unidad_default: string;
  modo_entrada: ModoEntradaResultado;
  ticket_decimales: number;
  multiplicador_clinico: string;
  formato_informe_entrada: FormatoInformeEntrada | '';
  rango_referencia_texto: string;
  rango_min: string;
  rango_max: string;
  requiere_muestra: boolean;
  activo: boolean;
};

const emptyForm = (): ExamenForm => ({
  codigo: '',
  nombre: '',
  abreviatura: '',
  tipo_muestra_requerida: '',
  tipo_resultado: 'NUMERICO',
  metodo: '',
  unidad_default: '',
  modo_entrada: 'ESTANDAR',
  ticket_decimales: 0,
  multiplicador_clinico: '1',
  formato_informe_entrada: '',
  rango_referencia_texto: '',
  rango_min: '',
  rango_max: '',
  requiere_muestra: false,
  activo: true,
});

const formFromRow = (row: LimsTipoExamen): ExamenForm => ({
  codigo: row.codigo,
  nombre: row.nombre,
  abreviatura: row.abreviatura ?? '',
  tipo_muestra_requerida: row.tipo_muestra_requerida,
  tipo_resultado: row.tipo_resultado ?? 'NUMERICO',
  metodo: row.metodo ?? '',
  unidad_default: row.unidad_default ?? '',
  modo_entrada: row.modo_entrada ?? 'ESTANDAR',
  ticket_decimales: row.ticket_decimales ?? 0,
  multiplicador_clinico: String(row.multiplicador_clinico ?? 1),
  formato_informe_entrada: (row.formato_informe_entrada ?? '') as FormatoInformeEntrada | '',
  rango_referencia_texto: row.rango_referencia_texto ?? '',
  rango_min: row.rango_min != null ? String(row.rango_min) : '',
  rango_max: row.rango_max != null ? String(row.rango_max) : '',
  requiere_muestra: !!row.requiere_muestra,
  activo: row.activo !== false,
});

const ExamenesCatalogo: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<LimsTipoExamen[]>([]);
  const [tiposMuestra, setTiposMuestra] = useState<LimsTipoMuestra[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [saving, setSaving] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<ExamenForm>(emptyForm());

  const allowed = canAccessLimsModule(currentUser);
  const canEdit = canEditLimsCatalogos(currentUser);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [examenes, muestras] = await Promise.all([
        listTiposExamenLims({ search: search.trim() || undefined }),
        listTiposMuestraLims(),
      ]);
      setRows(examenes);
      setTiposMuestra(muestras);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarCatalogo));
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    if (allowed) load();
  }, [allowed, load]);

  const muestraNombre = useMemo(() => {
    const map = new Map(tiposMuestra.map((t) => [t.id, t.nombre]));
    return (id: number) => map.get(id) ?? `#${id}`;
  }, [tiposMuestra]);

  const patchForm = (patch: Partial<ExamenForm>) => setForm((f) => ({ ...f, ...patch }));

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setDialogOpen(true);
  };

  const openEdit = (row: LimsTipoExamen) => {
    setEditingId(row.id);
    setForm(formFromRow(row));
    setDialogOpen(true);
  };

  const buildPayload = (): TipoExamenLimsWriteBody & { codigo?: string } => {
    const formatoInforme: LimsTipoExamen['formato_informe_entrada'] =
      form.modo_entrada === 'ESTANDAR'
        ? ''
        : form.formato_informe_entrada || undefined;

    const base: TipoExamenLimsWriteBody = {
      nombre: form.nombre.trim(),
      abreviatura: form.abreviatura.trim() || undefined,
      tipo_muestra_requerida: Number(form.tipo_muestra_requerida),
      tipo_resultado: form.tipo_resultado,
      metodo: form.metodo.trim() || undefined,
      unidad_default: form.unidad_default.trim() || undefined,
      modo_entrada: form.modo_entrada,
      ticket_decimales: form.modo_entrada === 'ESTANDAR' ? 0 : form.ticket_decimales,
      multiplicador_clinico:
        form.modo_entrada === 'ESTANDAR' ? 1 : form.multiplicador_clinico.trim() || '1',
      formato_informe_entrada: formatoInforme,
      rango_referencia_texto: form.rango_referencia_texto.trim() || undefined,
      rango_min: form.rango_min.trim() || undefined,
      rango_max: form.rango_max.trim() || undefined,
      requiere_muestra: form.requiere_muestra,
      activo: form.activo,
    };
    if (!editingId) {
      return { ...base, codigo: form.codigo.trim().toUpperCase() };
    }
    return base;
  };

  const handleSave = async () => {
    if (!form.nombre.trim()) {
      toast.error('El nombre es obligatorio');
      return;
    }
    if (!form.tipo_muestra_requerida) {
      toast.error('Seleccioná el tipo de muestra requerida');
      return;
    }
    if (!editingId && !form.codigo.trim()) {
      toast.error('El código es obligatorio');
      return;
    }
    if (
      form.modo_entrada !== 'ESTANDAR' &&
      !(form.formato_informe_entrada as string)
    ) {
      toast.error('Seleccioná el formato de informe para modo ticket/fórmula');
      return;
    }

    setSaving(true);
    try {
      const body = buildPayload();
      if (editingId) {
        await patchTipoExamenLims(editingId, body);
        toast.success('Examen actualizado');
      } else {
        await createTipoExamenLims(
          body as TipoExamenLimsWriteBody & {
            codigo: string;
            nombre: string;
            tipo_muestra_requerida: number;
          }
        );
        toast.success('Examen creado');
      }
      setDialogOpen(false);
      await load();
    } catch (e) {
      toast.error(formatDrfError(e) || CLINICAL_ACTION_ERRORS.limsGuardarCatalogo);
    } finally {
      setSaving(false);
    }
  };

  const ticketMode = form.modo_entrada !== 'ESTANDAR';

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>Sin acceso al módulo LIMS.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Button size="small" onClick={() => navigate('/laboratorio/ordenes')} sx={{ mb: 1 }}>
        ← Órdenes LIMS
      </Button>
      <Typography variant="h5" gutterBottom>
        Catálogo de exámenes
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Configurá método, tipo de muestra, unidad, rangos y modo de ingreso de resultados (estándar, ticket
        analizador o fórmula %). La carga de resultados usa esta configuración por examen.
      </Typography>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2, alignItems: 'center' }}>
        <TextField
          size="small"
          label="Buscar"
          value={search}
          onChange={(ev) => setSearch(ev.target.value)}
          placeholder="Código, nombre, método…"
          sx={{ minWidth: 260 }}
        />
        <Button variant="outlined" onClick={() => load()} disabled={loading}>
          Actualizar
        </Button>
        {canEdit && (
          <Button variant="contained" onClick={openCreate}>
            Nuevo examen
          </Button>
        )}
      </Box>

      {rows.length === 0 && !loading && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No hay exámenes cargados. Ejecutá{' '}
          <code>python manage.py seed_catalogo_solicitud_papel</code> en el servidor o creá uno manualmente.
        </Alert>
      )}

      <TableContainer component={Paper} variant="outlined">
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Código</TableCell>
              <TableCell>Nombre</TableCell>
              <TableCell>Método</TableCell>
              <TableCell>Muestra</TableCell>
              <TableCell>Unidad</TableCell>
              <TableCell>Modo ingreso</TableCell>
              <TableCell>Estado</TableCell>
              {canEdit && <TableCell align="right">Acción</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={canEdit ? 8 : 7}>
                  <Typography color="text.secondary">Cargando…</Typography>
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={canEdit ? 8 : 7}>
                  <Typography color="text.secondary">Sin registros.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              rows.map((r) => (
                <TableRow key={r.id} sx={{ opacity: r.activo === false ? 0.6 : 1 }}>
                  <TableCell>{r.codigo}</TableCell>
                  <TableCell>{r.nombre}</TableCell>
                  <TableCell>{r.metodo || '—'}</TableCell>
                  <TableCell>{r.tipo_muestra_nombre || muestraNombre(r.tipo_muestra_requerida)}</TableCell>
                  <TableCell>{r.unidad_default || '—'}</TableCell>
                  <TableCell>
                    <Typography variant="body2">{modoEntradaResumen(r)}</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      size="small"
                      label={r.activo === false ? 'Inactivo' : 'Activo'}
                      color={r.activo === false ? 'default' : 'success'}
                      variant="outlined"
                    />
                  </TableCell>
                  {canEdit && (
                    <TableCell align="right">
                      <Button size="small" onClick={() => openEdit(r)}>
                        Editar
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {!canEdit && (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 2, display: 'block' }}>
          Solo lectura: la edición requiere rol laboratorio o administrador.
        </Typography>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingId ? `Editar ${form.codigo}` : 'Nuevo examen'}</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2, pt: 1 }}>
            {!editingId && (
              <TextField
                label="Código"
                value={form.codigo}
                onChange={(ev) => patchForm({ codigo: ev.target.value.toUpperCase() })}
                required
              />
            )}
            <TextField
              label="Nombre"
              value={form.nombre}
              onChange={(ev) => patchForm({ nombre: ev.target.value })}
              required
              sx={{ gridColumn: editingId ? 'span 2' : undefined }}
            />
            <TextField
              label="Abreviatura"
              value={form.abreviatura}
              onChange={(ev) => patchForm({ abreviatura: ev.target.value })}
            />
            <FormControl required>
              <InputLabel>Tipo de muestra</InputLabel>
              <Select
                label="Tipo de muestra"
                value={form.tipo_muestra_requerida === '' ? '' : String(form.tipo_muestra_requerida)}
                onChange={(ev) =>
                  patchForm({ tipo_muestra_requerida: Number(ev.target.value) })
                }
              >
                {tiposMuestra.map((t) => (
                  <MenuItem key={t.id} value={t.id}>
                    {t.codigo} — {t.nombre}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl>
              <InputLabel>Tipo de resultado</InputLabel>
              <Select
                label="Tipo de resultado"
                value={form.tipo_resultado}
                onChange={(ev) =>
                  patchForm({ tipo_resultado: ev.target.value as ExamenForm['tipo_resultado'] })
                }
              >
                <MenuItem value="NUMERICO">Numérico</MenuItem>
                <MenuItem value="TEXTO">Texto</MenuItem>
                <MenuItem value="CUALITATIVO">Cualitativo</MenuItem>
              </Select>
            </FormControl>
            <TextField
              label="Método analítico"
              value={form.metodo}
              onChange={(ev) => patchForm({ metodo: ev.target.value })}
              sx={{ gridColumn: 'span 2' }}
            />
            <TextField
              label="Unidad por defecto"
              value={form.unidad_default}
              onChange={(ev) => patchForm({ unidad_default: ev.target.value })}
              placeholder="ej. g/dL, /mm³, %"
            />
            <FormControl>
              <InputLabel>Modo de ingreso</InputLabel>
              <Select
                label="Modo de ingreso"
                value={form.modo_entrada}
                onChange={(ev) => {
                  const modo = ev.target.value as ModoEntradaResultado;
                  patchForm({
                    modo_entrada: modo,
                    ...(modo === 'ESTANDAR'
                      ? {
                          ticket_decimales: 0,
                          multiplicador_clinico: '1',
                          formato_informe_entrada: '',
                        }
                      : {
                          ticket_decimales: form.ticket_decimales || 0,
                          multiplicador_clinico: form.multiplicador_clinico || '1',
                          formato_informe_entrada:
                            form.formato_informe_entrada || ('decimal1' as FormatoInformeEntrada),
                        }),
                  });
                }}
              >
                {(Object.keys(MODO_ENTRADA_LABELS) as ModoEntradaResultado[]).map((k) => (
                  <MenuItem key={k} value={k}>
                    {MODO_ENTRADA_LABELS[k]}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            {ticketMode && (
              <>
                <TextField
                  label="Decimales implícitos del ticket"
                  type="number"
                  inputProps={{ min: 0, max: 4 }}
                  value={form.ticket_decimales}
                  onChange={(ev) => patchForm({ ticket_decimales: Number(ev.target.value) || 0 })}
                  helperText="9.3 con 1 decimal → operador tipea 93"
                />
                <TextField
                  label="Multiplicador clínico"
                  value={form.multiplicador_clinico}
                  onChange={(ev) => patchForm({ multiplicador_clinico: ev.target.value })}
                  helperText="Valor ticket × multiplicador = valor numérico"
                />
                <FormControl required={ticketMode}>
                  <InputLabel>Formato en informe</InputLabel>
                  <Select
                    label="Formato en informe"
                    value={form.formato_informe_entrada}
                    onChange={(ev) =>
                      patchForm({
                        formato_informe_entrada: ev.target.value as FormatoInformeEntrada,
                      })
                    }
                  >
                    {(Object.keys(FORMATO_INFORME_LABELS) as FormatoInformeEntrada[]).map((k) => (
                      <MenuItem key={k} value={k}>
                        {FORMATO_INFORME_LABELS[k]}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </>
            )}
            <TextField
              label="Rango referencia (texto)"
              value={form.rango_referencia_texto}
              onChange={(ev) => patchForm({ rango_referencia_texto: ev.target.value })}
              sx={{ gridColumn: 'span 2' }}
            />
            <TextField
              label="Rango mínimo"
              value={form.rango_min}
              onChange={(ev) => patchForm({ rango_min: ev.target.value })}
            />
            <TextField
              label="Rango máximo"
              value={form.rango_max}
              onChange={(ev) => patchForm({ rango_max: ev.target.value })}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={form.requiere_muestra}
                  onChange={(ev) => patchForm({ requiere_muestra: ev.target.checked })}
                />
              }
              label="Requiere muestra física en carga"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={form.activo}
                  onChange={(ev) => patchForm({ activo: ev.target.checked })}
                />
              }
              label="Activo en catálogo"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancelar</Button>
          <Button variant="contained" onClick={handleSave} disabled={saving}>
            {saving ? 'Guardando…' : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ExamenesCatalogo;
