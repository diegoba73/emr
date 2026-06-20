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
import {
  Add,
  Edit,
  Delete,
  Search,
} from '@mui/icons-material';
import { useData } from '../contexts/DataContext';
import { Medico, Especialidad } from '../types';
import {
  getMedicos,
  createMedico,
  updateMedico,
  deleteMedico,
  getEspecialidades,
} from '../services/apiService';

const Medicos: React.FC = () => {
  const { currentUser } = useData();
  const [medicos, setMedicos] = useState<Medico[]>([]);
  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingMedico, setEditingMedico] = useState<Medico | null>(null);
  const [formData, setFormData] = useState({
    nombre: '',
    apellido: '',
    matricula: '',
    especialidad_id: '',
    telefono: '',
    email: '',
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  // Verificar permisos - solo admin
  const isAdmin = currentUser?.rol === 'ADMIN' || currentUser?.is_superuser;

  useEffect(() => {
    if (!isAdmin) {
      return;
    }
    loadData();
  }, [isAdmin]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [medicosData, especialidadesData] = await Promise.all([
        getMedicos(),
        getEspecialidades(),
      ]);
      setMedicos(medicosData);
      setEspecialidades(especialidadesData);
    } catch (error) {
      console.error('Error loading data:', error);
      setError('Error al cargar los datos');
    } finally {
      setLoading(false);
    }
  };

  const filteredMedicos = useMemo(() => {
    if (!searchTerm.trim()) return medicos;
    const search = searchTerm.toLowerCase();
    return medicos.filter(
      (medico) =>
        medico.nombre?.toLowerCase().includes(search) ||
        medico.apellido?.toLowerCase().includes(search) ||
        medico.matricula?.toLowerCase().includes(search) ||
        medico.especialidad?.nombre?.toLowerCase().includes(search)
    );
  }, [medicos, searchTerm]);

  const paginatedMedicos = filteredMedicos.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleOpenDialog = (medico?: Medico) => {
    if (medico) {
      setEditingMedico(medico);
      setFormData({
        nombre: medico.nombre || '',
        apellido: medico.apellido || '',
        matricula: medico.matricula || '',
        especialidad_id: medico.especialidad?.id?.toString() || '',
        telefono: medico.telefono || '',
        email: medico.email || '',
      });
    } else {
      setEditingMedico(null);
      setFormData({
        nombre: '',
        apellido: '',
        matricula: '',
        especialidad_id: '',
        telefono: '',
        email: '',
      });
    }
    setError('');
    setShowDialog(true);
  };

  const handleCloseDialog = () => {
    setShowDialog(false);
    setEditingMedico(null);
    setError('');
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');
      
      const data = {
        ...formData,
        especialidad_id: formData.especialidad_id ? parseInt(formData.especialidad_id) : undefined,
      };

      if (editingMedico) {
        await updateMedico(editingMedico.id, data);
      } else {
        await createMedico(data);
      }

      await loadData();
      handleCloseDialog();
    } catch (error: any) {
      console.error('Error saving medico:', error);
      setError(error.response?.data?.error || error.message || 'Error al guardar el médico');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('¿Está seguro de que desea eliminar este médico?')) {
      return;
    }

    try {
      await deleteMedico(id);
      await loadData();
    } catch (error: any) {
      console.error('Error deleting medico:', error);
      alert(error.response?.data?.error || error.message || 'Error al eliminar el médico');
    }
  };

  if (!isAdmin) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">No tiene permisos para acceder a esta sección. Solo los administradores pueden gestionar médicos.</Alert>
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
          Médicos
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => handleOpenDialog()}
        >
          Nuevo Médico
        </Button>
      </Box>

      <Paper sx={{ mb: 2 }}>
        <Box sx={{ p: 2, display: 'flex', gap: 2 }}>
          <TextField
            size="small"
            placeholder="Buscar por nombre, apellido, matrícula o especialidad..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />,
            }}
            sx={{ flex: 1 }}
          />
        </Box>
      </Paper>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell><strong>Nombre</strong></TableCell>
              <TableCell><strong>Apellido</strong></TableCell>
              <TableCell><strong>Matrícula</strong></TableCell>
              <TableCell><strong>Especialidad</strong></TableCell>
              <TableCell><strong>Teléfono</strong></TableCell>
              <TableCell><strong>Email</strong></TableCell>
              <TableCell><strong>Acciones</strong></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {paginatedMedicos.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">
                    {searchTerm ? 'No se encontraron médicos' : 'No hay médicos registrados'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              paginatedMedicos.map((medico) => (
                <TableRow key={medico.id} hover>
                  <TableCell>{medico.nombre || '-'}</TableCell>
                  <TableCell>{medico.apellido || '-'}</TableCell>
                  <TableCell>{medico.matricula || '-'}</TableCell>
                  <TableCell>
                    {medico.especialidad ? (
                      <Chip label={medico.especialidad.nombre} size="small" color="primary" />
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell>{medico.telefono || '-'}</TableCell>
                  <TableCell>{medico.email || '-'}</TableCell>
                  <TableCell>
                    <IconButton
                      size="small"
                      color="primary"
                      onClick={() => handleOpenDialog(medico)}
                    >
                      <Edit />
                    </IconButton>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDelete(medico.id)}
                    >
                      <Delete />
                    </IconButton>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
        <TablePagination
          component="div"
          count={filteredMedicos.length}
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

      <Dialog open={showDialog} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingMedico ? 'Editar Médico' : 'Nuevo Médico'}
        </DialogTitle>
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
              label="Matrícula"
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
            <TextField
              label="Teléfono"
              value={formData.telefono}
              onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
              fullWidth
              type="tel"
            />
            <TextField
              label="Email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              fullWidth
              type="email"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog} disabled={saving}>
            Cancelar
          </Button>
          <Button
            onClick={handleSave}
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

export default Medicos;






