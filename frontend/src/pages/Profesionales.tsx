import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Button,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Alert,
  Chip,
  CircularProgress,
} from '@mui/material';
import { Add, Edit, Delete, Search } from '@mui/icons-material';
import { useData } from '../contexts/DataContext';
import {
  canAccessMedicos,
  canCreateMedico,
  isLaboratorioRole,
  normalizeRol,
} from '../utils/permissions';
import type { Especialidad, Profesional } from '../types';
import {
  getProfesionales,
  createProfesional,
  updateProfesional,
  deleteProfesional,
  getEspecialidades,
} from '../services/apiService';

const Profesionales: React.FC = () => {
  const { currentUser } = useData();
  const [rows, setRows] = useState<Profesional[]>([]);
  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editing, setEditing] = useState<Profesional | null>(null);
  const [formData, setFormData] = useState({
    nombre: '',
    apellido: '',
    matricula: '',
    especialidad_id: '',
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const canAccess = canAccessMedicos(currentUser);
  const canCreate = canCreateMedico(currentUser);
  const canDelete =
    normalizeRol(currentUser) === 'admin' ||
    Boolean(currentUser?.is_superuser) ||
    (Boolean(currentUser?.is_staff) && !isLaboratorioRole(currentUser));

  useEffect(() => {
    if (!canAccess) return;
    void loadData();
  }, [canAccess]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [list, especialidadesData] = await Promise.all([
        getProfesionales(),
        getEspecialidades(),
      ]);
      setRows(list);
      setEspecialidades(especialidadesData);
    } catch {
      setError('Error al cargar los datos');
    } finally {
      setLoading(false);
    }
  };

  const filtered = useMemo(() => {
    if (!searchTerm.trim()) return rows;
    const search = searchTerm.toLowerCase();
    return rows.filter(
      (p) =>
        p.nombre?.toLowerCase().includes(search) ||
        p.apellido?.toLowerCase().includes(search) ||
        p.matricula?.toLowerCase().includes(search) ||
        (p.especialidad_nombre || p.especialidad?.nombre || '').toLowerCase().includes(search)
    );
  }, [rows, searchTerm]);

  const paginated = filtered.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  const handleOpenDialog = (row?: Profesional) => {
    if (row) {
      setEditing(row);
      setFormData({
        nombre: row.nombre || '',
        apellido: row.apellido || '',
        matricula: row.matricula || '',
        especialidad_id: row.especialidad?.id?.toString() || '',
      });
    } else {
      setEditing(null);
      setFormData({ nombre: '', apellido: '', matricula: '', especialidad_id: '' });
    }
    setError('');
    setShowDialog(true);
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');
      const data = {
        nombre: formData.nombre,
        apellido: formData.apellido,
        matricula: formData.matricula,
        especialidad_id: formData.especialidad_id ? parseInt(formData.especialidad_id, 10) : undefined,
      };
      if (editing) {
        await updateProfesional(editing.id, data);
      } else {
        await createProfesional(data);
      }
      await loadData();
      setShowDialog(false);
    } catch (e: unknown) {
      const ax = e as { response?: { data?: { error?: string; detail?: string } }; message?: string };
      setError(ax.response?.data?.error || ax.response?.data?.detail || ax.message || 'Error al guardar');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('¿Eliminar este profesional?')) return;
    try {
      await deleteProfesional(id);
      await loadData();
    } catch (e: unknown) {
      const ax = e as { response?: { data?: { error?: string } }; message?: string };
      alert(ax.response?.data?.error || ax.message || 'Error al eliminar');
    }
  };

  if (!canAccess) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">No tiene permisos para acceder a esta sección.</Alert>
      </Box>
    );
  }

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" fontWeight={600}>
          Profesionales
        </Typography>
        {canCreate && (
          <Button variant="contained" startIcon={<Add />} onClick={() => handleOpenDialog()}>
            Nuevo profesional
          </Button>
        )}
      </Box>

      <Paper sx={{ mb: 2 }}>
        <Box sx={{ p: 2 }}>
          <TextField
            size="small"
            fullWidth
            placeholder="Buscar por nombre, apellido, matrícula o especialidad…"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />,
            }}
          />
        </Box>
      </Paper>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Nombre</strong></TableCell>
              <TableCell><strong>Apellido</strong></TableCell>
              <TableCell><strong>Código</strong></TableCell>
              <TableCell><strong>Especialidad</strong></TableCell>
              <TableCell><strong>Acciones</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginated.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">
                    {searchTerm ? 'Sin coincidencias' : 'No hay profesionales registrados'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              paginated.map((p) => (
                <TableRow key={p.id} hover>
                  <TableCell>{p.nombre || '—'}</TableCell>
                  <TableCell>{p.apellido || '—'}</TableCell>
                  <TableCell>{p.matricula || '—'}</TableCell>
                  <TableCell>
                    {p.especialidad_nombre || p.especialidad?.nombre ? (
                      <Chip
                        label={p.especialidad_nombre || p.especialidad?.nombre}
                        size="small"
                        color="primary"
                      />
                    ) : (
                      '—'
                    )}
                  </TableCell>
                  <TableCell>
                    {canCreate && (
                      <IconButton size="small" color="primary" onClick={() => handleOpenDialog(p)}>
                        <Edit />
                      </IconButton>
                    )}
                    {canDelete && (
                      <IconButton size="small" color="error" onClick={() => void handleDelete(p.id)}>
                        <Delete />
                      </IconButton>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={filtered.length}
          page={page}
          onPageChange={(_, newPage) => setPage(newPage)}
          rowsPerPage={rowsPerPage}
          onRowsPerPageChange={(e) => {
            setRowsPerPage(parseInt(e.target.value, 10));
            setPage(0);
          }}
          rowsPerPageOptions={[5, 10, 25, 50]}
        />
      </TableContainer>

      <Dialog open={showDialog} onClose={() => !saving && setShowDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? 'Editar profesional' : 'Nuevo profesional'}</DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
              {error}
            </Alert>
          )}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField
              label="Nombre"
              value={formData.nombre}
              onChange={(e) => setFormData({ ...formData, nombre: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Apellido"
              value={formData.apellido}
              onChange={(e) => setFormData({ ...formData, apellido: e.target.value })}
              fullWidth
              required
            />
            <TextField
              label="Código / matrícula"
              value={formData.matricula}
              onChange={(e) => setFormData({ ...formData, matricula: e.target.value })}
              fullWidth
              required
            />
            <TextField
              select
              label="Especialidad"
              value={formData.especialidad_id}
              onChange={(e) => setFormData({ ...formData, especialidad_id: e.target.value })}
              fullWidth
            >
              <MenuItem value="">Sin especialidad</MenuItem>
              {especialidades.map((esp) => (
                <MenuItem key={esp.id} value={esp.id.toString()}>
                  {esp.nombre}
                </MenuItem>
              ))}
            </TextField>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDialog(false)} disabled={saving}>
            Cancelar
          </Button>
          <Button
            onClick={() => void handleSave()}
            variant="contained"
            disabled={saving || !formData.nombre || !formData.apellido || !formData.matricula}
          >
            {saving ? <CircularProgress size={20} /> : 'Guardar'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Profesionales;
