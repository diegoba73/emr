import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
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
import type { LimsTipoMuestra } from '../../types/lims';
import {
  createTipoMuestraLims,
  listTiposMuestraLims,
  patchTipoMuestraLims,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canAccessLimsCatalogos, canEditLimsCatalogos } from '../../utils/limsAccess';

type FormState = {
  codigo: string;
  nombre: string;
  color_tubo: string;
  activo: boolean;
};

const emptyForm = (): FormState => ({
  codigo: '',
  nombre: '',
  color_tubo: '',
  activo: true,
});

const formFromRow = (row: LimsTipoMuestra): FormState => ({
  codigo: row.codigo,
  nombre: row.nombre,
  color_tubo: row.color_tubo ?? '',
  activo: row.activo !== false,
});

const TiposMuestraCatalogo: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<LimsTipoMuestra[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<LimsTipoMuestra | null>(null);
  const [deleting, setDeleting] = useState(false);

  const allowed = canAccessLimsCatalogos(currentUser);
  const canEdit = canEditLimsCatalogos(currentUser);

  const load = async () => {
    setLoading(true);
    try {
      const all = await listTiposMuestraLims();
      setRows(all);
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
      const hay = `${r.codigo} ${r.nombre} ${r.color_tubo ?? ''}`.toLowerCase();
      return hay.includes(q);
    });
  }, [rows, search]);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setDialogOpen(true);
  };

  const openEdit = (row: LimsTipoMuestra) => {
    setEditingId(row.id);
    setForm(formFromRow(row));
    setDialogOpen(true);
  };

  const patchForm = (partial: Partial<FormState>) => {
    setForm((prev) => ({ ...prev, ...partial }));
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
    setSaving(true);
    try {
      if (editingId) {
        await patchTipoMuestraLims(editingId, {
          nombre: form.nombre.trim(),
          color_tubo: form.color_tubo.trim() || '',
          activo: form.activo,
        });
        toast.success('Tipo de muestra actualizado');
      } else {
        await createTipoMuestraLims({
          codigo: form.codigo.trim().toUpperCase(),
          nombre: form.nombre.trim(),
          color_tubo: form.color_tubo.trim() || undefined,
          activo: form.activo,
        });
        toast.success('Tipo de muestra agregado');
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
      await patchTipoMuestraLims(deleteTarget.id, { activo: false });
      toast.success(`«${deleteTarget.nombre}» eliminado (desactivado)`);
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
        Tipos de muestra
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Catálogo de muestras biológicas (sangre, orina, etc.). Se usan al generar tubos e imprimir
        etiquetas en una orden.
      </Typography>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2, alignItems: 'center' }}>
        <TextField
          size="small"
          label="Buscar"
          value={search}
          onChange={(ev) => setSearch(ev.target.value)}
          placeholder="Código, nombre, color…"
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
          No hay tipos de muestra cargados. Agregá al menos sangre y orina, o ejecutá{' '}
          <code>python manage.py seed_catalogo_solicitud_papel</code> en el servidor.
        </Alert>
      )}

      <TableContainer component={Paper} variant="outlined">
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Código</TableCell>
              <TableCell>Nombre</TableCell>
              <TableCell>Color / tubo</TableCell>
              <TableCell>Estado</TableCell>
              {canEdit && <TableCell align="right">Acciones</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={canEdit ? 5 : 4}>
                  <Typography color="text.secondary">Cargando…</Typography>
                </TableCell>
              </TableRow>
            ) : filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={canEdit ? 5 : 4}>
                  <Typography color="text.secondary">
                    {search.trim() ? 'Sin resultados para la búsqueda.' : 'Sin registros.'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((r) => (
                <TableRow key={r.id} sx={{ opacity: r.activo === false ? 0.6 : 1 }}>
                  <TableCell>{r.codigo}</TableCell>
                  <TableCell>{r.nombre}</TableCell>
                  <TableCell>{r.color_tubo || '—'}</TableCell>
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
                      <IconButton
                        size="small"
                        aria-label={`Editar ${r.nombre}`}
                        onClick={() => openEdit(r)}
                      >
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        aria-label={`Eliminar ${r.nombre}`}
                        color="error"
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
          Solo lectura: agregar, editar o eliminar requiere rol laboratorio o administrador.
        </Typography>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editingId ? `Editar ${form.codigo}` : 'Agregar tipo de muestra'}</DialogTitle>
        <DialogContent dividers>
          <Box sx={{ display: 'grid', gap: 2, pt: 1 }}>
            {!editingId && (
              <TextField
                label="Código"
                value={form.codigo}
                onChange={(ev) => patchForm({ codigo: ev.target.value.toUpperCase() })}
                required
                inputProps={{ maxLength: 64 }}
                helperText="Máx. 64 caracteres (ej. SANGRE_EDTA, ORINA)"
              />
            )}
            <TextField
              label="Nombre"
              value={form.nombre}
              onChange={(ev) => patchForm({ nombre: ev.target.value })}
              required
              inputProps={{ maxLength: 200 }}
            />
            <TextField
              label="Color / tubo (opcional)"
              value={form.color_tubo}
              onChange={(ev) => patchForm({ color_tubo: ev.target.value })}
              inputProps={{ maxLength: 50 }}
            />
            {editingId && (
              <FormControlLabel
                control={
                  <Switch
                    checked={form.activo}
                    onChange={(ev) => patchForm({ activo: ev.target.checked })}
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
        <DialogTitle>Eliminar tipo de muestra</DialogTitle>
        <DialogContent>
          <Typography>
            ¿Desactivar «{deleteTarget?.codigo} — {deleteTarget?.nombre}»? No se borra de la base
            (para no romper órdenes históricas); quedará inactivo y dejará de usarse en nuevas
            órdenes.
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

export default TiposMuestraCatalogo;