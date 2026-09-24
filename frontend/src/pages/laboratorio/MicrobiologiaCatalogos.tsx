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
  IconButton,
  InputAdornment,
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
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import EditOutlinedIcon from '@mui/icons-material/EditOutlined';
import SearchIcon from '@mui/icons-material/Search';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type {
  Antibiotico,
  FraseRapidaMicrobiologia,
  MedioCultivo,
  Microorganismo,
} from '../../types/lims';
import {
  createAntibiotico,
  createFraseRapidaMicro,
  createMedioCultivo,
  createMicroorganismo,
  listAntibioticos,
  listFrasesRapidasMicro,
  listMediosCultivo,
  listMicroorganismos,
  updateAntibiotico,
  updateFraseRapidaMicro,
  updateMedioCultivo,
  updateMicroorganismo,
} from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { canAccessMicrobiologia, canEditMicroCatalogos } from '../../utils/limsAccess';
import FrasesRapidasCatalogSection from '../../components/lims/micro/FrasesRapidasCatalogSection';

type CatalogTab = 0 | 1 | 2 | 3;

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

type FraseForm = {
  abreviatura: string;
  texto: string;
  categoria: string;
  activo: boolean;
};

type DeleteTarget = {
  tab: CatalogTab;
  id: number;
  codigo: string;
  nombre: string;
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

const emptyFraseForm = (): FraseForm => ({
  abreviatura: '',
  texto: '',
  categoria: 'GENERAL',
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

const fraseFromRow = (row: FraseRapidaMicrobiologia): FraseForm => ({
  abreviatura: row.abreviatura,
  texto: row.texto,
  categoria: row.categoria ?? 'GENERAL',
  activo: row.activo !== false,
});

const TAB_NOUN = ['medio', 'microorganismo', 'antibiótico', 'frase'] as const;
const TAB_NOUN_PLURAL = ['medios', 'microorganismos', 'antibióticos', 'frases'] as const;

const MicrobiologiaCatalogos: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [tab, setTab] = useState<CatalogTab>(0);
  const [medios, setMedios] = useState<MedioCultivo[]>([]);
  const [micros, setMicros] = useState<Microorganismo[]>([]);
  const [abs, setAbs] = useState<Antibiotico[]>([]);
  const [frases, setFrases] = useState<FraseRapidaMicrobiologia[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [saving, setSaving] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [medioForm, setMedioForm] = useState<MedioForm>(emptyMedioForm);
  const [microForm, setMicroForm] = useState<MicroForm>(emptyMicroForm);
  const [antibioticoForm, setAntibioticoForm] = useState<AntibioticoForm>(emptyAntibioticoForm);
  const [fraseForm, setFraseForm] = useState<FraseForm>(emptyFraseForm);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget | null>(null);
  const [deleting, setDeleting] = useState(false);

  const allowed = canAccessMicrobiologia(currentUser);
  const canEdit = canEditMicroCatalogos(currentUser);

  const load = useCallback(async () => {
    setLoading(true);
    const params = { search: search.trim() || undefined };
    try {
      const [m, mi, a, f] = await Promise.all([
        listMediosCultivo(params),
        listMicroorganismos(params),
        listAntibioticos(params),
        listFrasesRapidasMicro(params),
      ]);
      setMedios(m);
      setMicros(mi);
      setAbs(a);
      setFrases(f);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCargarCatalogo));
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    if (allowed) load();
  }, [allowed, load]);

  const rows =
    tab === 0 ? medios : tab === 1 ? micros : tab === 2 ? abs : frases;
  const colSpan = canEdit ? (tab === 1 ? 6 : 5) : tab === 1 ? 5 : 4;

  const openCreate = () => {
    setEditingId(null);
    setMedioForm(emptyMedioForm());
    setMicroForm(emptyMicroForm());
    setAntibioticoForm(emptyAntibioticoForm());
    setFraseForm(emptyFraseForm());
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

  const openEditFrase = (row: FraseRapidaMicrobiologia) => {
    setEditingId(row.id);
    setFraseForm(fraseFromRow(row));
    setDialogOpen(true);
  };

  const handleTabChange = (_: unknown, v: CatalogTab) => {
    setTab(v);
    setDialogOpen(false);
    setDeleteTarget(null);
  };

  const handleSave = async () => {
    if (tab === 0 && (!medioForm.codigo.trim() || !medioForm.nombre.trim())) {
      toast.error('Código y nombre son obligatorios');
      return;
    }
    if (tab === 1 && (!microForm.codigo.trim() || !microForm.nombre.trim())) {
      toast.error('Código y nombre son obligatorios');
      return;
    }
    if (tab === 2 && (!antibioticoForm.codigo.trim() || !antibioticoForm.nombre.trim())) {
      toast.error('Código y nombre son obligatorios');
      return;
    }
    if (tab === 3 && (!fraseForm.abreviatura.trim() || !fraseForm.texto.trim())) {
      toast.error('Abreviatura y texto son obligatorios');
      return;
    }
    setSaving(true);
    try {
      if (tab === 0) {
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
      } else if (tab === 2) {
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
      } else {
        const body = {
          abreviatura: fraseForm.abreviatura.trim(),
          texto: fraseForm.texto.trim(),
          categoria: fraseForm.categoria.trim() || 'GENERAL',
          activo: fraseForm.activo,
          editado_manualmente: true,
        };
        if (editingId) {
          await updateFraseRapidaMicro(editingId, body);
          toast.success('Frase actualizada');
        } else {
          await createFraseRapidaMicro(body);
          toast.success('Frase creada');
        }
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
      if (deleteTarget.tab === 0) {
        await updateMedioCultivo(deleteTarget.id, { activo: false });
      } else if (deleteTarget.tab === 1) {
        await updateMicroorganismo(deleteTarget.id, { activo: false });
      } else if (deleteTarget.tab === 2) {
        await updateAntibiotico(deleteTarget.id, { activo: false });
      } else {
        await updateFraseRapidaMicro(deleteTarget.id, {
          activo: false,
          editado_manualmente: true,
        });
      }
      toast.success(`«${deleteTarget.nombre}» eliminado (desactivado)`);
      setDeleteTarget(null);
      await load();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarCatalogo));
    } finally {
      setDeleting(false);
    }
  };

  const createLabels = ['Nuevo medio', 'Nuevo microorganismo', 'Nuevo antibiótico', 'Nueva frase'] as const;
  const dialogTitle = editingId
    ? `Editar ${
        tab === 0
          ? medioForm.codigo
          : tab === 1
            ? microForm.codigo
            : tab === 2
              ? antibioticoForm.codigo
              : fraseForm.abreviatura
      }`
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
        Medios, microorganismos, antibióticos y frases rápidas (LabWin NEMOTEC) usados en
        siembras, identificación, antibiogramas e informes.
      </Typography>

      <Tabs value={tab} onChange={handleTabChange} sx={{ mb: 2 }}>
        <Tab label="Medios" />
        <Tab label="Microorganismos" />
        <Tab label="Antibióticos" />
        <Tab label="Frases rápidas" />
      </Tabs>

      {tab === 3 ? (
        <Box>
          <TextField
            size="small"
            label="Buscar frases"
            value={search}
            onChange={(ev) => setSearch(ev.target.value)}
            placeholder="Abreviatura o texto…"
            sx={{ minWidth: 260, mb: 2 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" color="action" />
                </InputAdornment>
              ),
            }}
          />
          <FrasesRapidasCatalogSection search={search} canEdit={canEdit} />
        </Box>
      ) : (
      <>
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
                : tab === 2
                  ? 'Código, nombre, familia…'
                  : 'Abreviatura, texto…'
          }
          sx={{ minWidth: 260 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" color="action" />
              </InputAdornment>
            ),
          }}
        />
        <Button variant="outlined" onClick={() => load()} disabled={loading}>
          Actualizar
        </Button>
        {canEdit && (
          <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
            {createLabels[tab]}
          </Button>
        )}
        <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
          {rows.length} {TAB_NOUN_PLURAL[tab]}
        </Typography>
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
              {canEdit && <TableCell align="right">Acciones</TableCell>}
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={colSpan}>
                  <Typography color="text.secondary">Cargando…</Typography>
                </TableCell>
              </TableRow>
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={colSpan}>
                  <Typography color="text.secondary">
                    {search.trim() ? 'Sin resultados para la búsqueda.' : 'Sin registros.'}
                  </Typography>
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
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      <IconButton size="small" aria-label={`Editar ${r.nombre}`} onClick={() => openEditMedio(r)}>
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        aria-label={`Eliminar ${r.nombre}`}
                        color="error"
                        disabled={r.activo === false}
                        onClick={() =>
                          setDeleteTarget({ tab: 0, id: r.id, codigo: r.codigo, nombre: r.nombre })
                        }
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
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
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      <IconButton size="small" aria-label={`Editar ${r.nombre}`} onClick={() => openEditMicro(r)}>
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        aria-label={`Eliminar ${r.nombre}`}
                        color="error"
                        disabled={r.activo === false}
                        onClick={() =>
                          setDeleteTarget({ tab: 1, id: r.id, codigo: r.codigo, nombre: r.nombre })
                        }
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  )}
                </TableRow>
              ))
            ) : tab === 2 ? (
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
                    <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                      <IconButton
                        size="small"
                        aria-label={`Editar ${r.nombre}`}
                        onClick={() => openEditAntibiotico(r)}
                      >
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        aria-label={`Eliminar ${r.nombre}`}
                        color="error"
                        disabled={r.activo === false}
                        onClick={() =>
                          setDeleteTarget({ tab: 2, id: r.id, codigo: r.codigo, nombre: r.nombre })
                        }
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  )}
                </TableRow>
              ))
            ) : (
              frases.map((r) => (
                <TableRow key={r.id} sx={{ opacity: r.activo === false ? 0.6 : 1 }}>
                  <TableCell>{r.abreviatura}</TableCell>
                  <TableCell sx={{ maxWidth: 360, whiteSpace: 'pre-wrap' }}>
                    {(r.texto || '').slice(0, 160)}
                    {(r.texto || '').length > 160 ? '…' : ''}
                    {r.requiere_revision ? (
                      <Chip size="small" label="Revisión" color="warning" sx={{ ml: 1 }} />
                    ) : null}
                  </TableCell>
                  <TableCell>{r.categoria || '—'}</TableCell>
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
                        aria-label={`Editar ${r.abreviatura}`}
                        onClick={() => openEditFrase(r)}
                      >
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                      <IconButton
                        size="small"
                        aria-label={`Eliminar ${r.abreviatura}`}
                        color="error"
                        disabled={r.activo === false}
                        onClick={() =>
                          setDeleteTarget({
                            tab: 3,
                            id: r.id,
                            codigo: r.abreviatura,
                            nombre: (r.texto || '').slice(0, 40),
                          })
                        }
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
          Solo lectura: agregar, editar o eliminar requiere rol laboratorio, bioquímico o administrador.
        </Typography>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{dialogTitle}</DialogTitle>
        <DialogContent dividers>
          {tab === 0 && (
            <Box sx={{ display: 'grid', gap: 2, pt: 1 }}>
              <TextField
                label="Código"
                value={medioForm.codigo}
                onChange={(ev) => setMedioForm((f) => ({ ...f, codigo: ev.target.value.toUpperCase() }))}
                required
                disabled={!!editingId}
                inputProps={{ maxLength: 30 }}
              />
              <TextField
                label="Nombre"
                value={medioForm.nombre}
                onChange={(ev) => setMedioForm((f) => ({ ...f, nombre: ev.target.value }))}
                required
                inputProps={{ maxLength: 200 }}
              />
              <TextField
                label="Tipo"
                value={medioForm.tipo}
                onChange={(ev) => setMedioForm((f) => ({ ...f, tipo: ev.target.value }))}
                inputProps={{ maxLength: 50 }}
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
              <TextField
                label="Código"
                value={microForm.codigo}
                onChange={(ev) => setMicroForm((f) => ({ ...f, codigo: ev.target.value.toUpperCase() }))}
                required
                disabled={!!editingId}
                inputProps={{ maxLength: 40 }}
              />
              <TextField
                label="Nombre"
                value={microForm.nombre}
                onChange={(ev) => setMicroForm((f) => ({ ...f, nombre: ev.target.value }))}
                required
                inputProps={{ maxLength: 200 }}
              />
              <TextField
                label="Género"
                value={microForm.genero}
                onChange={(ev) => setMicroForm((f) => ({ ...f, genero: ev.target.value }))}
                inputProps={{ maxLength: 120 }}
              />
              <TextField
                label="Especie"
                value={microForm.especie}
                onChange={(ev) => setMicroForm((f) => ({ ...f, especie: ev.target.value }))}
                inputProps={{ maxLength: 120 }}
              />
              <TextField
                label="Grupo"
                value={microForm.grupo}
                onChange={(ev) => setMicroForm((f) => ({ ...f, grupo: ev.target.value }))}
                inputProps={{ maxLength: 80 }}
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
              <TextField
                label="Código"
                value={antibioticoForm.codigo}
                onChange={(ev) =>
                  setAntibioticoForm((f) => ({ ...f, codigo: ev.target.value.toUpperCase() }))
                }
                required
                disabled={!!editingId}
                inputProps={{ maxLength: 40 }}
              />
              <TextField
                label="Nombre"
                value={antibioticoForm.nombre}
                onChange={(ev) => setAntibioticoForm((f) => ({ ...f, nombre: ev.target.value }))}
                required
                inputProps={{ maxLength: 200 }}
              />
              <TextField
                label="Familia"
                value={antibioticoForm.familia}
                onChange={(ev) => setAntibioticoForm((f) => ({ ...f, familia: ev.target.value }))}
                inputProps={{ maxLength: 120 }}
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
          <Button onClick={() => setDialogOpen(false)} disabled={saving}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={() => void handleSave()} disabled={saving}>
            {saving ? 'Guardando…' : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!deleteTarget} onClose={() => !deleting && setDeleteTarget(null)}>
        <DialogTitle>Eliminar {deleteTarget ? TAB_NOUN[deleteTarget.tab] : ''}</DialogTitle>
        <DialogContent>
          <Typography>
            ¿Desactivar «{deleteTarget?.codigo} — {deleteTarget?.nombre}»? No se borra de la base
            (para no romper estudios históricos); quedará inactivo y dejará de usarse en nuevas
            siembras, identificaciones, antibiogramas o informes.
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
      </>
      )}
    </Box>
  );
};

export default MicrobiologiaCatalogos;
