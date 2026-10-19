import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  List,
  ListItemButton,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Add, Delete, Edit } from '@mui/icons-material';
import { useData } from '../../contexts/DataContext';
import {
  createCirugiaAbordaje,
  createCirugiaEspecialidad,
  createCirugiaProcedimiento,
  deleteCirugiaAbordaje,
  deleteCirugiaEspecialidad,
  deleteCirugiaProcedimiento,
  getCirugiaAbordajes,
  getCirugiaEspecialidades,
  getCirugiaProcedimientos,
  updateCirugiaAbordaje,
  updateCirugiaEspecialidad,
  updateCirugiaProcedimiento,
} from '../../services/apiService';
import type {
  CirugiaAbordajeCatalogo,
  CirugiaEspecialidadCatalogo,
  CirugiaProcedimientoCatalogo,
} from '../../types/estudios';
import { canAccessCatalogosClinicos, canEditCirugiaCatalogo } from '../../utils/permissions';

type EditKind = 'especialidad' | 'procedimiento' | 'abordaje';

const Cirugias: React.FC = () => {
  const { currentUser } = useData();
  const canView = canAccessCatalogosClinicos(currentUser);
  const canEdit = canEditCirugiaCatalogo(currentUser);

  const [especialidades, setEspecialidades] = useState<CirugiaEspecialidadCatalogo[]>([]);
  const [procedimientos, setProcedimientos] = useState<CirugiaProcedimientoCatalogo[]>([]);
  const [abordajes, setAbordajes] = useState<CirugiaAbordajeCatalogo[]>([]);
  const [espId, setEspId] = useState<number | null>(null);
  const [procId, setProcId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editKind, setEditKind] = useState<EditKind>('especialidad');
  const [editId, setEditId] = useState<number | null>(null);
  const [nombre, setNombre] = useState('');
  const [activo, setActivo] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadEspecialidades = useCallback(async () => {
    const rows = (await getCirugiaEspecialidades(false)) as CirugiaEspecialidadCatalogo[];
    setEspecialidades(rows);
  }, []);

  const loadProcedimientos = useCallback(async (especialidad: number) => {
    const rows = (await getCirugiaProcedimientos(especialidad, false)) as CirugiaProcedimientoCatalogo[];
    setProcedimientos(rows);
  }, []);

  const loadAbordajes = useCallback(async (procedimiento: number) => {
    const rows = (await getCirugiaAbordajes(procedimiento, false)) as CirugiaAbordajeCatalogo[];
    setAbordajes(rows);
  }, []);

  useEffect(() => {
    if (!canView) return;
    setLoading(true);
    setError(null);
    loadEspecialidades()
      .catch(() => setError('No se pudo cargar el catálogo de especialidades quirúrgicas.'))
      .finally(() => setLoading(false));
  }, [canView, loadEspecialidades]);

  useEffect(() => {
    if (!espId) {
      setProcedimientos([]);
      setProcId(null);
      setAbordajes([]);
      return;
    }
    void loadProcedimientos(espId).catch(() => setError('No se pudieron cargar procedimientos.'));
  }, [espId, loadProcedimientos]);

  useEffect(() => {
    if (!procId) {
      setAbordajes([]);
      return;
    }
    void loadAbordajes(procId).catch(() => setError('No se pudieron cargar abordajes.'));
  }, [procId, loadAbordajes]);

  const openCreate = (kind: EditKind) => {
    setEditKind(kind);
    setEditId(null);
    setNombre('');
    setActivo(true);
    setDialogOpen(true);
  };

  const openEdit = (kind: EditKind, item: { id: number; nombre: string; activo?: boolean }) => {
    setEditKind(kind);
    setEditId(item.id);
    setNombre(item.nombre);
    setActivo(item.activo !== false);
    setDialogOpen(true);
  };

  const handleSave = async () => {
    if (!nombre.trim()) {
      setError('El nombre es obligatorio.');
      return;
    }
    if (editKind === 'procedimiento' && !espId) {
      setError('Seleccioná una especialidad.');
      return;
    }
    if (editKind === 'abordaje' && !procId) {
      setError('Seleccioná un procedimiento.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (editKind === 'especialidad') {
        if (editId) {
          await updateCirugiaEspecialidad(editId, { nombre: nombre.trim(), activo });
        } else {
          await createCirugiaEspecialidad({ nombre: nombre.trim(), activo, orden: 0 });
        }
        await loadEspecialidades();
      } else if (editKind === 'procedimiento' && espId) {
        if (editId) {
          await updateCirugiaProcedimiento(editId, { nombre: nombre.trim(), activo });
        } else {
          await createCirugiaProcedimiento({
            especialidad: espId,
            nombre: nombre.trim(),
            activo,
          });
        }
        await loadProcedimientos(espId);
      } else if (editKind === 'abordaje' && procId) {
        if (editId) {
          await updateCirugiaAbordaje(editId, { nombre: nombre.trim(), activo });
        } else {
          await createCirugiaAbordaje({
            procedimiento: procId,
            nombre: nombre.trim(),
            activo,
          });
        }
        await loadAbordajes(procId);
      }
      setDialogOpen(false);
    } catch {
      setError('No se pudo guardar. Revisá permisos o nombres duplicados.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (kind: EditKind, id: number) => {
    if (!window.confirm('¿Eliminar este registro del catálogo?')) return;
    setError(null);
    try {
      if (kind === 'especialidad') {
        await deleteCirugiaEspecialidad(id);
        if (espId === id) setEspId(null);
        await loadEspecialidades();
      } else if (kind === 'procedimiento' && espId) {
        await deleteCirugiaProcedimiento(id);
        if (procId === id) setProcId(null);
        await loadProcedimientos(espId);
      } else if (kind === 'abordaje' && procId) {
        await deleteCirugiaAbordaje(id);
        await loadAbordajes(procId);
      }
    } catch {
      setError('No se pudo eliminar (puede estar en uso o sin permiso).');
    }
  };

  if (!canView) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="warning">No tiene permisos para acceder a esta sección.</Alert>
      </Box>
    );
  }

  const dialogTitle =
    editKind === 'especialidad'
      ? editId
        ? 'Editar especialidad'
        : 'Nueva especialidad'
      : editKind === 'procedimiento'
        ? editId
          ? 'Editar procedimiento'
          : 'Nuevo procedimiento'
        : editId
          ? 'Editar abordaje'
          : 'Nuevo abordaje';

  return (
    <Box sx={{ p: 3 }} className="fade-in">
      <Typography variant="h5" gutterBottom>
        Cirugías (especialidad → procedimiento → abordaje)
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Catálogo usado en altas de Cirugía. El abordaje es opcional al indicar.
        {!canEdit && ' Solo administradores pueden editar.'}
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {loading ? (
        <Typography color="text.secondary">Cargando…</Typography>
      ) : (
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems="stretch">
          <Paper sx={{ flex: 1, p: 1.5, minHeight: 320 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="subtitle1">Especialidades</Typography>
              {canEdit && (
                <Button size="small" startIcon={<Add />} onClick={() => openCreate('especialidad')}>
                  Agregar
                </Button>
              )}
            </Stack>
            <List dense>
              {especialidades.map((e) => (
                <ListItemButton
                  key={e.id}
                  selected={espId === e.id}
                  onClick={() => {
                    setEspId(e.id);
                    setProcId(null);
                  }}
                >
                  <ListItemText
                    primary={e.nombre}
                    secondary={e.activo === false ? 'Inactivo' : undefined}
                  />
                  {canEdit && (
                    <Stack direction="row" spacing={0.5} onClick={(ev) => ev.stopPropagation()}>
                      <Button size="small" onClick={() => openEdit('especialidad', e)}>
                        <Edit fontSize="small" />
                      </Button>
                      <Button size="small" color="error" onClick={() => void handleDelete('especialidad', e.id)}>
                        <Delete fontSize="small" />
                      </Button>
                    </Stack>
                  )}
                </ListItemButton>
              ))}
            </List>
          </Paper>

          <Paper sx={{ flex: 1, p: 1.5, minHeight: 320 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="subtitle1">Procedimientos</Typography>
              {canEdit && (
                <Button
                  size="small"
                  startIcon={<Add />}
                  disabled={!espId}
                  onClick={() => openCreate('procedimiento')}
                >
                  Agregar
                </Button>
              )}
            </Stack>
            {!espId ? (
              <Typography variant="body2" color="text.secondary">
                Seleccioná una especialidad.
              </Typography>
            ) : (
              <List dense>
                {procedimientos.map((p) => (
                  <ListItemButton
                    key={p.id}
                    selected={procId === p.id}
                    onClick={() => setProcId(p.id)}
                  >
                    <ListItemText
                      primary={p.nombre}
                      secondary={p.activo === false ? 'Inactivo' : undefined}
                    />
                    {canEdit && (
                      <Stack direction="row" spacing={0.5} onClick={(ev) => ev.stopPropagation()}>
                        <Button size="small" onClick={() => openEdit('procedimiento', p)}>
                          <Edit fontSize="small" />
                        </Button>
                        <Button
                          size="small"
                          color="error"
                          onClick={() => void handleDelete('procedimiento', p.id)}
                        >
                          <Delete fontSize="small" />
                        </Button>
                      </Stack>
                    )}
                  </ListItemButton>
                ))}
              </List>
            )}
          </Paper>

          <Paper sx={{ flex: 1, p: 1.5, minHeight: 320 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
              <Typography variant="subtitle1">Abordajes</Typography>
              {canEdit && (
                <Button
                  size="small"
                  startIcon={<Add />}
                  disabled={!procId}
                  onClick={() => openCreate('abordaje')}
                >
                  Agregar
                </Button>
              )}
            </Stack>
            {!procId ? (
              <Typography variant="body2" color="text.secondary">
                Seleccioná un procedimiento.
              </Typography>
            ) : (
              <List dense>
                {abordajes.map((a) => (
                  <ListItemButton key={a.id} disableRipple>
                    <ListItemText
                      primary={a.nombre}
                      secondary={a.activo === false ? 'Inactivo' : undefined}
                    />
                    {canEdit && (
                      <Stack direction="row" spacing={0.5}>
                        <Button size="small" onClick={() => openEdit('abordaje', a)}>
                          <Edit fontSize="small" />
                        </Button>
                        <Button
                          size="small"
                          color="error"
                          onClick={() => void handleDelete('abordaje', a.id)}
                        >
                          <Delete fontSize="small" />
                        </Button>
                      </Stack>
                    )}
                  </ListItemButton>
                ))}
                {abordajes.length === 0 && (
                  <Typography variant="body2" color="text.secondary" sx={{ px: 2 }}>
                    Sin abordajes (opcional en el alta).
                  </Typography>
                )}
              </List>
            )}
          </Paper>
        </Stack>
      )}

      <Dialog open={dialogOpen} onClose={() => !saving && setDialogOpen(false)} fullWidth maxWidth="xs">
        <DialogTitle>{dialogTitle}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Nombre"
            fullWidth
            required
            value={nombre}
            onChange={(e) => setNombre(e.target.value)}
          />
          <FormControlLabel
            control={<Checkbox checked={activo} onChange={(e) => setActivo(e.target.checked)} />}
            label="Activo"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} disabled={saving}>
            Cancelar
          </Button>
          <Button variant="contained" onClick={() => void handleSave()} disabled={saving}>
            Guardar
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Cirugias;
