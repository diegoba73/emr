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
  FormControl,
  FormControlLabel,
  IconButton,
  InputAdornment,
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
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import SearchIcon from '@mui/icons-material/Search';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { LimsPanelExamen, LimsTipoExamen } from '../../types/lims';
import {
  ContextoPaqueteMovil,
  createPaqueteLabMovil,
  listPaquetesLabMovil,
  listPanelesLims,
  listTiposExamenLims,
  patchPaqueteLabMovil,
  type PaqueteLabMovilWeb,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canAccessLimsCatalogos, canEditLimsCatalogos } from '../../utils/limsAccess';

type FormState = {
  codigo: string;
  nombre: string;
  contexto: ContextoPaqueteMovil;
  descripcion: string;
  activo: boolean;
  orden: string;
  paneles: LimsPanelExamen[];
  examenes: LimsTipoExamen[];
};

const CONTEXTOS: Array<{ value: ContextoPaqueteMovil; label: string }> = [
  { value: 'GUARDIA', label: 'Guardia' },
  { value: 'AMBULATORIO', label: 'Ambulatorio' },
  { value: 'INTERNACION', label: 'Internación' },
];

const emptyForm = (): FormState => ({
  codigo: '',
  nombre: '',
  contexto: 'GUARDIA',
  descripcion: '',
  activo: true,
  orden: '0',
  paneles: [],
  examenes: [],
});

const PaquetesMovilCatalogo: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [rows, setRows] = useState<PaqueteLabMovilWeb[]>([]);
  const [paneles, setPaneles] = useState<LimsPanelExamen[]>([]);
  const [examenes, setExamenes] = useState<LimsTipoExamen[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<PaqueteLabMovilWeb | null>(null);
  const [deleting, setDeleting] = useState(false);

  const allowed = canAccessLimsCatalogos(currentUser);
  const canEdit = canEditLimsCatalogos(currentUser);

  const load = async () => {
    setLoading(true);
    try {
      const [paquetes, panList, exList] = await Promise.all([
        listPaquetesLabMovil(),
        listPanelesLims({ activo: true }),
        listTiposExamenLims({ activo: true }),
      ]);
      setRows(paquetes);
      setPaneles(panList.filter((p) => p.activo !== false));
      setExamenes(exList.filter((e) => e.activo !== false));
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
      const comps = [
        ...(r.paneles_detalle || []).map((p) => p.nombre),
        ...(r.examenes_detalle || []).map((e) => e.nombre),
      ].join(' ');
      return `${r.codigo} ${r.nombre} ${r.contexto_display} ${r.descripcion} ${comps}`
        .toLowerCase()
        .includes(q);
    });
  }, [rows, search]);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setDialogOpen(true);
  };

  const openEdit = (row: PaqueteLabMovilWeb) => {
    setEditingId(row.id);
    const panById = new Map(paneles.map((p) => [p.id, p]));
    const exById = new Map(examenes.map((e) => [e.id, e]));
    setForm({
      codigo: row.codigo,
      nombre: row.nombre,
      contexto: row.contexto,
      descripcion: row.descripcion || '',
      activo: row.activo,
      orden: String(row.orden ?? 0),
      paneles: (row.paneles_ids || [])
        .map((id) => panById.get(id))
        .filter((p): p is LimsPanelExamen => Boolean(p)),
      examenes: (row.examenes_ids || [])
        .map((id) => exById.get(id))
        .filter((e): e is LimsTipoExamen => Boolean(e)),
    });
    setDialogOpen(true);
  };

  const save = async () => {
    if (!form.codigo.trim() || !form.nombre.trim()) {
      toast.error('Código y nombre son obligatorios.');
      return;
    }
    if (!form.paneles.length && !form.examenes.length) {
      toast.error('Agregá al menos un panel o un examen.');
      return;
    }
    setSaving(true);
    try {
      const body = {
        nombre: form.nombre.trim(),
        contexto: form.contexto,
        descripcion: form.descripcion.trim(),
        activo: form.activo,
        orden: Number(form.orden) || 0,
        paneles_ids: form.paneles.map((p) => p.id),
        examenes_ids: form.examenes.map((e) => e.id),
      };
      if (editingId) {
        await patchPaqueteLabMovil(editingId, body);
        toast.success('Paquete actualizado');
      } else {
        await createPaqueteLabMovil({
          codigo: form.codigo.trim().toUpperCase(),
          ...body,
        });
        toast.success('Paquete creado');
      }
      setDialogOpen(false);
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarCatalogo));
    } finally {
      setSaving(false);
    }
  };

  const softDelete = async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await patchPaqueteLabMovil(deleteTarget.id, { activo: false });
      toast.success('Paquete desactivado');
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
      <Box p={3}>
        <Alert severity="warning">No tenés acceso a este catálogo.</Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate('/laboratorio/ordenes')}>
          Volver
        </Button>
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={2} gap={2} flexWrap="wrap">
        <Box>
          <Typography variant="h5" fontWeight={700}>
            Paquetes app móvil
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Armá combos por contexto (guardia, ambulatorio, internación) para que el médico pida
            rápido desde el celular. Siempre puede complementar con exámenes sueltos.
          </Typography>
        </Box>
        {canEdit && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
            Nuevo paquete
          </Button>
        )}
      </Box>

      <TextField
        size="small"
        placeholder="Buscar…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        sx={{ mb: 2, minWidth: 280 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon fontSize="small" />
            </InputAdornment>
          ),
        }}
      />

      {!canEdit && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Solo lectura: editar requiere rol laboratorio, bioquímico o administrador.
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Código</TableCell>
              <TableCell>Nombre</TableCell>
              <TableCell>Contexto</TableCell>
              <TableCell>Contenido</TableCell>
              <TableCell>Estado</TableCell>
              <TableCell align="right">Acciones</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading && (
              <TableRow>
                <TableCell colSpan={6}>Cargando…</TableCell>
              </TableRow>
            )}
            {!loading && !filtered.length && (
              <TableRow>
                <TableCell colSpan={6}>
                  No hay paquetes. Creá uno para Guardia, Ambulatorio o Internación.
                </TableCell>
              </TableRow>
            )}
            {filtered.map((row) => (
              <TableRow key={row.id} hover>
                <TableCell>{row.codigo}</TableCell>
                <TableCell>
                  <Typography fontWeight={600}>{row.nombre}</Typography>
                  {row.descripcion ? (
                    <Typography variant="caption" color="text.secondary">
                      {row.descripcion}
                    </Typography>
                  ) : null}
                </TableCell>
                <TableCell>
                  <Chip size="small" label={row.contexto_display} />
                </TableCell>
                <TableCell>
                  <Box display="flex" gap={0.5} flexWrap="wrap">
                    {(row.paneles_detalle || []).map((p) => (
                      <Chip key={`p-${p.id}`} size="small" variant="outlined" label={`Panel: ${p.nombre}`} />
                    ))}
                    {(row.examenes_detalle || []).map((e) => (
                      <Chip key={`e-${e.id}`} size="small" variant="outlined" label={e.nombre} />
                    ))}
                  </Box>
                </TableCell>
                <TableCell>{row.activo ? 'Activo' : 'Inactivo'}</TableCell>
                <TableCell align="right">
                  {canEdit && (
                    <>
                      <IconButton aria-label="Editar" onClick={() => openEdit(row)}>
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      {row.activo && (
                        <IconButton aria-label="Desactivar" onClick={() => setDeleteTarget(row)}>
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      )}
                    </>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} fullWidth maxWidth="md">
        <DialogTitle>{editingId ? 'Editar paquete' : 'Nuevo paquete'}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField
            label="Código"
            value={form.codigo}
            disabled={Boolean(editingId)}
            onChange={(e) => setForm((f) => ({ ...f, codigo: e.target.value.toUpperCase() }))}
          />
          <TextField
            label="Nombre"
            value={form.nombre}
            onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
          />
          <FormControl>
            <InputLabel id="ctx-label">Contexto</InputLabel>
            <Select
              labelId="ctx-label"
              label="Contexto"
              value={form.contexto}
              onChange={(e) =>
                setForm((f) => ({ ...f, contexto: e.target.value as ContextoPaqueteMovil }))
              }
            >
              {CONTEXTOS.map((c) => (
                <MenuItem key={c.value} value={c.value}>
                  {c.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Descripción"
            value={form.descripcion}
            onChange={(e) => setForm((f) => ({ ...f, descripcion: e.target.value }))}
          />
          <TextField
            label="Orden"
            type="number"
            value={form.orden}
            onChange={(e) => setForm((f) => ({ ...f, orden: e.target.value }))}
            helperText="Menor número aparece primero en la app"
          />
          <Autocomplete
            multiple
            options={paneles}
            value={form.paneles}
            getOptionLabel={(o) => `${o.codigo} — ${o.nombre}`}
            onChange={(_, value) => setForm((f) => ({ ...f, paneles: value }))}
            renderInput={(params) => <TextField {...params} label="Paneles" />}
          />
          <Autocomplete
            multiple
            options={examenes}
            value={form.examenes}
            getOptionLabel={(o) => `${o.codigo} — ${o.nombre}`}
            onChange={(_, value) => setForm((f) => ({ ...f, examenes: value }))}
            renderInput={(params) => (
              <TextField {...params} label="Exámenes sueltos" helperText="Complemento al paquete" />
            )}
          />
          <FormControlLabel
            control={
              <Switch
                checked={form.activo}
                onChange={(e) => setForm((f) => ({ ...f, activo: e.target.checked }))}
              />
            }
            label="Activo"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancelar</Button>
          <Button variant="contained" disabled={saving} onClick={() => void save()}>
            {saving ? 'Guardando…' : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(deleteTarget)} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Desactivar paquete</DialogTitle>
        <DialogContent>
          ¿Desactivar «{deleteTarget?.nombre}»? Dejará de mostrarse en la app móvil.
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancelar</Button>
          <Button color="error" disabled={deleting} onClick={() => void softDelete()}>
            Desactivar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default PaquetesMovilCatalogo;
