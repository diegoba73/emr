import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  InputAdornment,
  Paper,
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
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import SearchIcon from '@mui/icons-material/Search';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { LimsPanelExamen, LimsTipoExamen } from '../../types/lims';
import {
  createPanelExamenLims,
  listPanelesLims,
  listTiposExamenLims,
  patchPanelExamenLims,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canAccessLimsCatalogos, canEditLimsCatalogos } from '../../utils/limsAccess';

type FormState = {
  codigo: string;
  nombre: string;
  codigo_nbu: string;
  ub_nbu: string;
  activo: boolean;
  componentes: LimsTipoExamen[];
};

const emptyForm = (): FormState => ({
  codigo: '',
  nombre: '',
  codigo_nbu: '',
  ub_nbu: '',
  activo: true,
  componentes: [],
});

const PanelesCatalogo: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<LimsPanelExamen[]>([]);
  const [examenes, setExamenes] = useState<LimsTipoExamen[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<LimsPanelExamen | null>(null);
  const [deleting, setDeleting] = useState(false);

  const allowed = canAccessLimsCatalogos(currentUser);
  const canEdit = canEditLimsCatalogos(currentUser);

  const examenesById = useMemo(() => {
    const m = new Map<number, LimsTipoExamen>();
    for (const e of examenes) m.set(e.id, e);
    return m;
  }, [examenes]);

  const load = async () => {
    setLoading(true);
    try {
      const [paneles, exams] = await Promise.all([
        listPanelesLims(),
        listTiposExamenLims(),
      ]);
      setRows(paneles);
      setExamenes(exams);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarCatalogo));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (allowed) void load();
  }, [allowed]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((r) => {
      const comps = (r.tipos_examen_nombres ?? []).join(' ');
      const hay = `${r.codigo} ${r.codigo_nbu ?? ''} ${r.nombre} ${comps}`.toLowerCase();
      return hay.includes(q);
    });
  }, [rows, search]);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setDialogOpen(true);
  };

  const openEdit = (row: LimsPanelExamen) => {
    const comps: LimsTipoExamen[] = [];
    if (row.tipos_examen_detalle?.length) {
      for (const d of row.tipos_examen_detalle) {
        const full = examenesById.get(d.id);
        comps.push(
          full ?? {
            id: d.id,
            codigo: d.codigo,
            nombre: d.nombre,
            tipo_muestra_requerida: 0,
          }
        );
      }
    } else {
      for (const id of row.tipos_examen ?? []) {
        const full = examenesById.get(id);
        if (full) comps.push(full);
      }
    }
    setEditingId(row.id);
    setForm({
      codigo: row.codigo,
      nombre: row.nombre,
      codigo_nbu: row.codigo_nbu ?? '',
      ub_nbu: row.ub_nbu != null && row.ub_nbu !== '' ? String(row.ub_nbu) : '',
      activo: row.activo !== false,
      componentes: comps,
    });
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!form.nombre.trim()) {
      toast.error('El nombre es obligatorio');
      return;
    }
    if (!editingId && !form.codigo.trim()) {
      toast.error('El código es obligatorio');
      return;
    }
    if (form.componentes.length === 0) {
      toast.error('Seleccioná al menos un examen componente');
      return;
    }
    setSaving(true);
    try {
      const body = {
        nombre: form.nombre.trim(),
        activo: form.activo,
        tipos_examen_ids: form.componentes.map((c) => c.id),
        codigo_nbu: form.codigo_nbu.trim() || null,
        ub_nbu: form.ub_nbu.trim() || null,
      };
      if (editingId) {
        await patchPanelExamenLims(editingId, body);
        toast.success('Panel actualizado');
      } else {
        await createPanelExamenLims({
          ...body,
          codigo: form.codigo.trim().toUpperCase(),
        });
        toast.success('Panel creado');
      }
      setDialogOpen(false);
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarCatalogo));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await patchPanelExamenLims(deleteTarget.id, { activo: false });
      toast.success(`Panel «${deleteTarget.nombre}» desactivado`);
      setDeleteTarget(null);
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarCatalogo));
    } finally {
      setDeleting(false);
    }
  };

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
        Paneles de examen
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Un panel agrupa analitos (ej. Hemograma = hematíes, Hb, Hto…; Ionograma = Na, K, Cl).
        Al pedirlo en una orden se generan resultados para cada componente. El código NBU / U.B.
        del panel es el de facturación del perfil; los componentes pueden tener NBU propio si se
        piden sueltos.
      </Typography>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2, alignItems: 'center' }}>
        <TextField
          size="small"
          label="Buscar"
          value={search}
          onChange={(ev) => setSearch(ev.target.value)}
          placeholder="Código, NBU, nombre, componente…"
          sx={{ minWidth: 280 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" color="action" />
              </InputAdornment>
            ),
          }}
        />
        <Button variant="outlined" onClick={() => void load()} disabled={loading}>
          Actualizar
        </Button>
        {canEdit && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
            Agregar
          </Button>
        )}
        <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
          {filtered.length} de {rows.length}
        </Typography>
      </Box>

      {rows.length === 0 && !loading && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No hay paneles. Creá uno o ejecutá{' '}
          <code>python manage.py reparar_paneles_iaca</code> /{' '}
          <code>seed_catalogo_solicitud_papel</code>.
        </Alert>
      )}

      <TableContainer component={Paper} variant="outlined">
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Código</TableCell>
              <TableCell>NBU</TableCell>
              <TableCell>U.B.</TableCell>
              <TableCell>Nombre</TableCell>
              <TableCell>Componentes</TableCell>
              <TableCell>Estado</TableCell>
              {canEdit && <TableCell align="right">Acciones</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={canEdit ? 7 : 6}>
                  <Typography color="text.secondary">Cargando…</Typography>
                </TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={canEdit ? 7 : 6}>
                  <Typography color="text.secondary">
                    {search.trim() ? 'Sin resultados para la búsqueda.' : 'Sin registros.'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((r) => (
                <TableRow key={r.id} sx={{ opacity: r.activo === false ? 0.6 : 1 }}>
                  <TableCell>{r.codigo}</TableCell>
                  <TableCell>{r.codigo_nbu || '—'}</TableCell>
                  <TableCell>{r.ub_nbu != null && r.ub_nbu !== '' ? r.ub_nbu : '—'}</TableCell>
                  <TableCell>{r.nombre}</TableCell>
                  <TableCell sx={{ maxWidth: 480 }}>
                    <Typography variant="body2" color="text.secondary">
                      {(r.tipos_examen_detalle ?? [])
                        .map((c) => c.codigo)
                        .join(', ') ||
                        (r.tipos_examen_nombres ?? []).join(', ') ||
                        '—'}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {(r.tipos_examen_detalle?.length ??
                        r.tipos_examen_nombres?.length ??
                        r.tipos_examen?.length ??
                        0)}{' '}
                      ítems
                    </Typography>
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
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      <IconButton size="small" aria-label={`Editar ${r.nombre}`} onClick={() => openEdit(r)}>
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        color="error"
                        aria-label={`Eliminar ${r.nombre}`}
                        disabled={r.activo === false}
                        onClick={() => setDeleteTarget(r)}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
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
          Solo lectura: editar paneles requiere rol laboratorio o administrador.
        </Typography>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{editingId ? `Editar ${form.codigo}` : 'Agregar panel'}</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: 'grid', gap: 2, pt: 1 }}>
            {!editingId && (
              <TextField
                label="Código"
                value={form.codigo}
                onChange={(ev) => setForm((p) => ({ ...p, codigo: ev.target.value.toUpperCase() }))}
                required
                helperText="Ej. PAN_HEMO, PAN_IONO"
                inputProps={{ maxLength: 20 }}
              />
            )}
            <TextField
              label="Nombre"
              value={form.nombre}
              onChange={(ev) => setForm((p) => ({ ...p, nombre: ev.target.value }))}
              required
            />
            <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr' }, gap: 2 }}>
              <TextField
                label="Código NBU"
                value={form.codigo_nbu}
                onChange={(ev) => setForm((p) => ({ ...p, codigo_nbu: ev.target.value.replace(/\D/g, '').slice(0, 6) }))}
                helperText="Práctica CUBRA del perfil (6 dígitos). Ej. Hemograma 660475."
                inputProps={{ inputMode: 'numeric', maxLength: 6 }}
              />
              <TextField
                label="U.B. (NBU)"
                value={form.ub_nbu}
                onChange={(ev) => setForm((p) => ({ ...p, ub_nbu: ev.target.value }))}
                helperText="Se completa solo si el nomenclador no tiene U.B. para ese código."
              />
            </Box>
            <Autocomplete
              multiple
              options={examenes.filter((e) => e.activo !== false)}
              value={form.componentes}
              onChange={(_, value) => setForm((p) => ({ ...p, componentes: value }))}
              getOptionLabel={(o) => `${o.codigo} — ${o.nombre}`}
              isOptionEqualToValue={(a, b) => a.id === b.id}
              filterSelectedOptions
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Exámenes que lo componen"
                  placeholder="Buscar por código o nombre"
                  helperText="Orden de carga/informe: el definido al guardar (podés reordenar quitando y volviendo a agregar)."
                />
              )}
            />
            {editingId && (
              <FormControlLabel
                control={
                  <Switch
                    checked={form.activo}
                    onChange={(ev) => setForm((p) => ({ ...p, activo: ev.target.checked }))}
                  />
                }
                label={form.activo ? 'Activo' : 'Inactivo'}
              />
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} disabled={saving}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={() => void handleSave()} disabled={saving}>
            {saving ? 'Guardando…' : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!deleteTarget} onClose={() => !deleting && setDeleteTarget(null)}>
        <DialogTitle>Eliminar panel</DialogTitle>
        <DialogContent>
          <Typography>
            ¿Desactivar «{deleteTarget?.codigo} — {deleteTarget?.nombre}»? No se borra de la base;
            dejará de aparecer al solicitar análisis.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)} disabled={deleting}>
            Cancelar
          </Button>
          <Button color="error" variant="contained" onClick={() => void handleDelete()} disabled={deleting}>
            {deleting ? 'Eliminando…' : 'Eliminar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PanelesCatalogo;