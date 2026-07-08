import React, { useCallback, useEffect, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Paper,
  Switch,
  Tab,
  Tabs,
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
import type { Antibiotico, MedioCultivo, Microorganismo } from '../../types/lims';
import {
  createAntibiotico,
  createMedioCultivo,
  createMicroorganismo,
  formatDrfError,
  listAntibioticos,
  listMediosCultivo,
  listMicroorganismos,
  updateAntibiotico,
  updateMedioCultivo,
  updateMicroorganismo,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canAccessMicrobiologia, canEditMicroCatalogos } from '../../utils/limsAccess';

type CatalogTab = 0 | 1 | 2;

type MedioForm = {
  codigo: string;
  nombre: string;
  tipo: string;
  descripcion: string;
  activo: boolean;
};

type MicroForm = {
  codigo: string;
  nombre: string;
  genero: string;
  especie: string;
  grupo: string;
  descripcion: string;
  activo: boolean;
};

type AntibioticoForm = {
  codigo: string;
  nombre: string;
  familia: string;
  descripcion: string;
  activo: boolean;
};

const emptyMedioForm = (): MedioForm => ({
  codigo: '',
  nombre: '',
  tipo: '',
  descripcion: '',
  activo: true,
});

const emptyMicroForm = (): MicroForm => ({
  codigo: '',
  nombre: '',
  genero: '',
  especie: '',
  grupo: '',
  descripcion: '',
  activo: true,
});

const emptyAntibioticoForm = (): AntibioticoForm => ({
  codigo: '',
  nombre: '',
  familia: '',
  descripcion: '',
  activo: true,
});

const medioFromRow = (row: MedioCultivo): MedioForm => ({
  codigo: row.codigo,
  nombre: row.nombre,
  tipo: row.tipo ?? '',
  descripcion: row.descripcion ?? '',
  activo: row.activo !== false,
});

const microFromRow = (row: Microorganismo): MicroForm => ({
  codigo: row.codigo,
  nombre: row.nombre,
  genero: row.genero ?? '',
  especie: row.especie ?? '',
  grupo: row.grupo ?? '',
  descripcion: row.descripcion ?? '',
  activo: row.activo !== false,
});

const antibioticoFromRow = (row: Antibiotico): AntibioticoForm => ({
  codigo: row.codigo,
  nombre: row.nombre,
  familia: row.familia ?? '',
  descripcion: row.descripcion ?? '',
  activo: row.activo !== false,
});

const MicrobiologiaCatalogos: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [tab, setTab] = useState<CatalogTab>(0);
  const [medios, setMedios] = useState<MedioCultivo[]>([]);
  const [micros, setMicros] = useState<Microorganismo[]>([]);
  const [abs, setAbs] = useState<Antibiotico[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [saving, setSaving] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [medioForm, setMedioForm] = useState<MedioForm>(emptyMedioForm);
  const [microForm, setMicroForm] = useState<MicroForm>(emptyMicroForm);
  const [antibioticoForm, setAntibioticoForm] = useState<AntibioticoForm>(emptyAntibioticoForm);

  const allowed = canAccessMicrobiologia(currentUser);
  const canEdit = canEditMicroCatalogos(currentUser);

  const load = useCallback(async () => {
    setLoading(true);
    const params = { search: search.trim() || undefined };
    try {
      const [m, mi, a] = await Promise.all([
        listMediosCultivo(params),
        listMicroorganismos(params),
        listAntibioticos(params),
      ]);
      setMedios(m);
      setMicros(mi);
      setAbs(a);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarCatalogo));
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    if (allowed) load();
  }, [allowed, load]);

  const rows = tab === 0 ? medios : tab === 1 ? micros : abs;

  const openCreate = () => {
    setEditingId(null);
    setMedioForm(emptyMedioForm());
    setMicroForm(emptyMicroForm());
    setAntibioticoForm(emptyAntibioticoForm());
    setDialogOpen(true);
  };

  const openEditMedio = (row: MedioCultivo) => {
    setEditingId(row.id);
    setMedioForm(medioFromRow(row));
    setDialogOpen(true);
  };

  const openEditMicro = (row: Microorganismo) => {
    setEditingId(row.id);
    setMicroForm(microFromRow(row));
    setDialogOpen(true);
  };

  const openEditAntibiotico = (row: Antibiotico) => {
    setEditingId(row.id);
    setAntibioticoForm(antibioticoFromRow(row));
    setDialogOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      if (tab === 0) {
        if (!medioForm.codigo.trim() || !medioForm.nombre.trim()) {
          toast.error('Código y nombre son obligatorios');
          return;
        }
        const body = {
          codigo: medioForm.codigo.trim().toUpperCase(),
          nombre: medioForm.nombre.trim(),
          tipo: medioForm.tipo.trim() || undefined,
          descripcion: medioForm.descripcion.trim() || undefined,
          activo: medioForm.activo,
        };
        if (editingId) {
          await updateMedioCultivo(editingId, body);
          toast.success('Medio actualizado');
        } else {
          await createMedioCultivo(body);
          toast.success('Medio creado');
        }
      } else if (tab === 1) {
        if (!microForm.codigo.trim() || !microForm.nombre.trim()) {
          toast.error('Código y nombre son obligatorios');
          return;
        }
        const body = {
          codigo: microForm.codigo.trim().toUpperCase(),
          nombre: microForm.nombre.trim(),
          genero: microForm.genero.trim() || undefined,
          especie: microForm.especie.trim() || undefined,
          grupo: microForm.grupo.trim() || undefined,
          descripcion: microForm.descripcion.trim() || undefined,
          activo: microForm.activo,
        };
        if (editingId) {
          await updateMicroorganismo(editingId, body);
          toast.success('Microorganismo actualizado');
        } else {
          await createMicroorganismo(body);
          toast.success('Microorganismo creado');
        }
      } else {
        if (!antibioticoForm.codigo.trim() || !antibioticoForm.nombre.trim()) {
          toast.error('Código y nombre son obligatorios');
          return;
        }
        const body = {
          codigo: antibioticoForm.codigo.trim().toUpperCase(),
          nombre: antibioticoForm.nombre.trim(),
          familia: antibioticoForm.familia.trim() || undefined,
          descripcion: antibioticoForm.descripcion.trim() || undefined,
          activo: antibioticoForm.activo,
        };
        if (editingId) {
          await updateAntibiotico(editingId, body);
          toast.success('Antibiótico actualizado');
        } else {
          await createAntibiotico(body);
          toast.success('Antibiótico creado');
        }
      }
      setDialogOpen(false);
      await load();
    } catch (e) {
      toast.error(formatDrfError(e) || CLINICAL_ACTION_ERRORS.limsGuardarCatalogo);
    } finally {
      setSaving(false);
    }
  };

  const createLabels = ['Nuevo medio', 'Nuevo microorganismo', 'Nuevo antibiótico'] as const;
  const dialogTitle = editingId
    ? `Editar ${tab === 0 ? medioForm.codigo : tab === 1 ? microForm.codigo : antibioticoForm.codigo}`
    : createLabels[tab];

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>Sin acceso.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <Button size="small" onClick={() => navigate('/laboratorio/microbiologia/estudios')} sx={{ mb: 1 }}>
        ← Estudios
      </Button>
      <Typography variant="h5" gutterBottom>
        Catálogos microbiología
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Medios, microorganismos y antibióticos usados en siembras, identificación y antibiogramas.
      </Typography>

      <Tabs value={tab} onChange={(_, v) => setTab(v as CatalogTab)} sx={{ mb: 2 }}>
        <Tab label="Medios" />
        <Tab label="Microorganismos" />
        <Tab label="Antibióticos" />
      </Tabs>

      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mb: 2, alignItems: 'center' }}>
        <TextField
          size="small"
          label="Buscar"
          value={search}
          onChange={(ev) => setSearch(ev.target.value)}
          placeholder={
            tab === 0
              ? 'Código, nombre, tipo…'
              : tab === 1
                ? 'Código, nombre, género, especie…'
                : 'Código, nombre, familia…'
          }
          sx={{ minWidth: 260 }}
        />
        <Button variant="outlined" onClick={() => load()} disabled={loading}>
          Actualizar
        </Button>
        {canEdit && (
          <Button variant="contained" onClick={openCreate}>
            {tab === 0 ? 'Nuevo medio' : tab === 1 ? 'Nuevo microorganismo' : 'Nuevo antibiótico'}
          </Button>
        )}
      </Box>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>Código</TableCell>
              <TableCell>Nombre</TableCell>
              {tab === 0 && <TableCell>Tipo</TableCell>}
              {tab === 1 && (
                <>
                  <TableCell>Género</TableCell>
                  <TableCell>Especie</TableCell>
                </>
              )}
              {tab === 2 && <TableCell>Familia</TableCell>}
              <TableCell>Estado</TableCell>
              {canEdit && <TableCell align="right">Acción</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={canEdit ? (tab === 1 ? 6 : 5) : tab === 1 ? 5 : 4}>
                  <Typography color="text.secondary">Cargando…</Typography>
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={canEdit ? (tab === 1 ? 6 : 5) : tab === 1 ? 5 : 4}>
                  <Typography color="text.secondary">Sin registros.</Typography>
                </TableCell>
              </TableRow>
            ) : tab === 0 ? (
              medios.map((r) => (
                <TableRow key={r.id} sx={{ opacity: r.activo === false ? 0.6 : 1 }}>
                  <TableCell>{r.codigo}</TableCell>
                  <TableCell>{r.nombre}</TableCell>
                  <TableCell>{r.tipo || '—'}</TableCell>
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
                      <Button size="small" onClick={() => openEditMedio(r)}>
                        Editar
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))
            ) : tab === 1 ? (
              micros.map((r) => (
                <TableRow key={r.id} sx={{ opacity: r.activo === false ? 0.6 : 1 }}>
                  <TableCell>{r.codigo}</TableCell>
                  <TableCell>{r.nombre}</TableCell>
                  <TableCell>{r.genero || '—'}</TableCell>
                  <TableCell>{r.especie || '—'}</TableCell>
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
                      <Button size="small" onClick={() => openEditMicro(r)}>
                        Editar
                      </Button>
                    </TableCell>
                  )}
                </TableRow>
              ))
            ) : (
              abs.map((r) => (
                <TableRow key={r.id} sx={{ opacity: r.activo === false ? 0.6 : 1 }}>
                  <TableCell>{r.codigo}</TableCell>
                  <TableCell>{r.nombre}</TableCell>
                  <TableCell>{r.familia || '—'}</TableCell>
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
                      <Button size="small" onClick={() => openEditAntibiotico(r)}>
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
          Solo lectura: la edición de catálogos requiere rol administrador.
        </Typography>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{dialogTitle}</DialogTitle>
        <DialogContent dividers>
          {tab === 0 && (
            <Box sx={{ display: 'grid', gap: 2, pt: 1 }}>
              {!editingId && (
                <TextField
                  label="Código"
                  value={medioForm.codigo}
                  onChange={(ev) => setMedioForm((f) => ({ ...f, codigo: ev.target.value.toUpperCase() }))}
                  required
                />
              )}
              <TextField
                label="Nombre"
                value={medioForm.nombre}
                onChange={(ev) => setMedioForm((f) => ({ ...f, nombre: ev.target.value }))}
                required
              />
              <TextField
                label="Tipo"
                value={medioForm.tipo}
                onChange={(ev) => setMedioForm((f) => ({ ...f, tipo: ev.target.value }))}
              />
              <TextField
                label="Descripción"
                value={medioForm.descripcion}
                onChange={(ev) => setMedioForm((f) => ({ ...f, descripcion: ev.target.value }))}
                multiline
                minRows={2}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={medioForm.activo}
                    onChange={(ev) => setMedioForm((f) => ({ ...f, activo: ev.target.checked }))}
                  />
                }
                label="Activo en catálogo"
              />
            </Box>
          )}
          {tab === 1 && (
            <Box sx={{ display: 'grid', gap: 2, pt: 1 }}>
              {!editingId && (
                <TextField
                  label="Código"
                  value={microForm.codigo}
                  onChange={(ev) => setMicroForm((f) => ({ ...f, codigo: ev.target.value.toUpperCase() }))}
                  required
                />
              )}
              <TextField
                label="Nombre"
                value={microForm.nombre}
                onChange={(ev) => setMicroForm((f) => ({ ...f, nombre: ev.target.value }))}
                required
              />
              <TextField
                label="Género"
                value={microForm.genero}
                onChange={(ev) => setMicroForm((f) => ({ ...f, genero: ev.target.value }))}
              />
              <TextField
                label="Especie"
                value={microForm.especie}
                onChange={(ev) => setMicroForm((f) => ({ ...f, especie: ev.target.value }))}
              />
              <TextField
                label="Grupo"
                value={microForm.grupo}
                onChange={(ev) => setMicroForm((f) => ({ ...f, grupo: ev.target.value }))}
              />
              <TextField
                label="Descripción"
                value={microForm.descripcion}
                onChange={(ev) => setMicroForm((f) => ({ ...f, descripcion: ev.target.value }))}
                multiline
                minRows={2}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={microForm.activo}
                    onChange={(ev) => setMicroForm((f) => ({ ...f, activo: ev.target.checked }))}
                  />
                }
                label="Activo en catálogo"
              />
            </Box>
          )}
          {tab === 2 && (
            <Box sx={{ display: 'grid', gap: 2, pt: 1 }}>
              {!editingId && (
                <TextField
                  label="Código"
                  value={antibioticoForm.codigo}
                  onChange={(ev) =>
                    setAntibioticoForm((f) => ({ ...f, codigo: ev.target.value.toUpperCase() }))
                  }
                  required
                />
              )}
              <TextField
                label="Nombre"
                value={antibioticoForm.nombre}
                onChange={(ev) => setAntibioticoForm((f) => ({ ...f, nombre: ev.target.value }))}
                required
              />
              <TextField
                label="Familia"
                value={antibioticoForm.familia}
                onChange={(ev) => setAntibioticoForm((f) => ({ ...f, familia: ev.target.value }))}
              />
              <TextField
                label="Descripción"
                value={antibioticoForm.descripcion}
                onChange={(ev) => setAntibioticoForm((f) => ({ ...f, descripcion: ev.target.value }))}
                multiline
                minRows={2}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={antibioticoForm.activo}
                    onChange={(ev) => setAntibioticoForm((f) => ({ ...f, activo: ev.target.checked }))}
                  />
                }
                label="Activo en catálogo"
              />
            </Box>
          )}
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

export default MicrobiologiaCatalogos;
