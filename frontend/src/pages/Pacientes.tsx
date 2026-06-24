import React, { useMemo, useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
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
  Chip,
  Avatar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress,
  Alert,
  Tooltip,
  TextField,
  MenuItem,
} from '@mui/material';
import {
  Phone,
  Email,
  Assignment,
  Close,
} from '@mui/icons-material';
import { useData } from '../contexts/DataContext';
import { Paciente } from '../types';
import SearchAndFilters from '../components/SearchAndFilters';
import { createPaciente } from '../services/apiService';
import { canCreatePaciente } from '../utils/permissions';
import { getSafeApiErrorMessage } from '../utils/apiError';
import {
  extractSearchWords,
  pacienteMatchesSearch,
  genericMatchesSearch,
} from '../utils/search';

const Pacientes: React.FC = () => {
  const { pacientes, loading, loadPacientes, currentUser } = useData();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const searchWords = useMemo(() => extractSearchWords(searchTerm), [searchTerm]);

  useEffect(() => {
    const q = searchParams.get('q');
    if (q !== null) {
      setSearchTerm(q);
    }
  }, [searchParams]);

  // Cargar pacientes cuando el componente se monta
  useEffect(() => {
    // Cargar pacientes si no se está cargando actualmente
    // Esto asegura que siempre se carguen los datos al entrar a la página
    if (!loading.pacientes) {
      // Solo cargar si no hay pacientes o si hay muy pocos (posible carga incompleta)
      if (pacientes.length === 0) {
        console.log('📋 Cargando pacientes al montar el componente...');
        loadPacientes();
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Solo ejecutar al montar el componente

  const [selectedPaciente] = useState<Paciente | null>(null);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState('');
  const [newPaciente, setNewPaciente] = useState({
    nombre: '',
    apellido: '',
    dni: '',
    fecha_nacimiento: '',
    sexo: '' as 'M' | 'F' | '',
    telefono: '',
    email: '',
    direccion: '',
    obra_social: '',
    numero_afiliado: '',
    observaciones: ''
  });

  // Filtrar pacientes
  const filteredPacientes = useMemo(() => {
    if (searchWords.length === 0) {
      return pacientes;
    }

    return pacientes.filter((paciente) => {
      if (pacienteMatchesSearch(paciente, searchWords)) {
        return true;
      }

      if (genericMatchesSearch(
        [paciente.email, paciente.direccion, paciente.obra_social],
        searchWords
      )) {
        return true;
      }

      return false;
    });
  }, [pacientes, searchWords]);

  const paginatedPacientes = filteredPacientes.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleChangePage = (event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const openPatient360 = (paciente: Paciente) => {
    navigate(`/paciente/${paciente.id}`);
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('es-ES');
  };

  const getSexoColor = (sexo: string | undefined) => {
    return sexo === 'M' ? 'primary' : 'secondary';
  };

  const canCreate = canCreatePaciente(currentUser);

  if (loading.pacientes) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Cargando pacientes...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }} className="fade-in">
      {/* Header */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
          Gestión de Pacientes
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Administra la información de todos los pacientes del sistema
        </Typography>
      </Box>



      {/* Search and Filters */}
      <SearchAndFilters
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        searchPlaceholder="Buscar por nombre, apellido, DNI o email..."
        filters={{}}
        onRefresh={loadPacientes}
        onAdd={canCreate ? () => { setCreateError(''); setShowCreateDialog(true); } : undefined}
        addButtonText="Nuevo Paciente"
        totalItems={pacientes.length}
        filteredItems={filteredPacientes.length}
      />

      {/* Patients Table */}
      <Paper sx={{ width: '100%', overflow: 'hidden' }}>
        <TableContainer sx={{ maxHeight: 600 }}>
          <Table stickyHeader>
            <TableHead>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Paciente</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>DNI</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Fecha Nac.</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Sexo</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Contacto</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Obra Social</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Acciones</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedPacientes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                    <Typography variant="body1" color="text.secondary">
                      {searchTerm ? 'No se encontraron pacientes con los filtros aplicados' : 'No hay pacientes registrados'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                paginatedPacientes.map((paciente) => (
                  <TableRow key={paciente.id} hover>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <Avatar sx={{ bgcolor: 'primary.main' }}>
                          {paciente.nombre?.charAt(0)}{paciente.apellido?.charAt(0)}
                        </Avatar>
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {paciente.nombre} {paciente.apellido}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            ID: {paciente.id}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        {paciente.dni || 'N/A'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {formatDate(paciente.fecha_nacimiento)}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={paciente.sexo === 'M' ? 'Masculino' : 'Femenino'}
                        color={getSexoColor(paciente.sexo)}
                        size="small"
                      />
                    </TableCell>
                    <TableCell>
                      <Box>
                        <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Phone sx={{ fontSize: 14 }} />
                          {paciente.telefono || 'N/A'}
                        </Typography>
                        <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                          <Email sx={{ fontSize: 14 }} />
                          {paciente.email || 'N/A'}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {paciente.obra_social || 'Sin obra social'}
                      </Typography>
                      {paciente.numero_afiliado && (
                        <Typography variant="caption" color="text.secondary">
                          N° {paciente.numero_afiliado}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Tooltip title="Ficha del paciente (vista 360)">
                        <IconButton
                          size="small"
                          onClick={() => openPatient360(paciente)}
                          color="primary"
                          sx={{ 
                            backgroundColor: 'primary.main',
                            color: 'white',
                            '&:hover': {
                              backgroundColor: 'primary.dark',
                            }
                          }}
                        >
                          <Assignment />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[5, 10, 25, 50]}
          component="div"
          count={filteredPacientes.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          labelRowsPerPage="Filas por página:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} de ${count}`}
        />
      </Paper>

      {/* Details Dialog */}
      <Dialog
        open={showDetailsDialog}
        onClose={() => setShowDetailsDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Avatar sx={{ bgcolor: 'primary.main' }}>
              {selectedPaciente?.nombre?.charAt(0)}{selectedPaciente?.apellido?.charAt(0)}
            </Avatar>
            <Typography variant="h6">
              Detalles del Paciente
            </Typography>
            </Box>
            <IconButton onClick={() => setShowDetailsDialog(false)} sx={{ color: 'grey.500' }}>
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedPaciente && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 3, mt: 1 }}>
              <Box sx={{ flex: '1 1 300px', minWidth: 300 }}>
                <Typography variant="subtitle2" color="text.secondary">Nombre Completo</Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {selectedPaciente.nombre} {selectedPaciente.apellido}
                </Typography>
                
                <Typography variant="subtitle2" color="text.secondary">DNI</Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {selectedPaciente.dni || 'No especificado'}
                </Typography>
                
                <Typography variant="subtitle2" color="text.secondary">Fecha de Nacimiento</Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {formatDate(selectedPaciente.fecha_nacimiento)}
                </Typography>
                
                <Typography variant="subtitle2" color="text.secondary">Sexo</Typography>
                <Chip
                  label={selectedPaciente.sexo === 'M' ? 'Masculino' : 'Femenino'}
                  color={getSexoColor(selectedPaciente.sexo)}
                  sx={{ mb: 2 }}
                />
              </Box>
              <Box sx={{ flex: '1 1 300px', minWidth: 300 }}>
                <Typography variant="subtitle2" color="text.secondary">Teléfono</Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {selectedPaciente.telefono || 'No especificado'}
                </Typography>
                
                <Typography variant="subtitle2" color="text.secondary">Email</Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {selectedPaciente.email || 'No especificado'}
                </Typography>
                
                <Typography variant="subtitle2" color="text.secondary">Dirección</Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {selectedPaciente.direccion || 'No especificada'}
                </Typography>
              </Box>
              <Box sx={{ flex: '1 1 100%', width: '100%' }}>
                <Typography variant="subtitle2" color="text.secondary">Obra Social</Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  {selectedPaciente.obra_social || 'Sin obra social'}
                  {selectedPaciente.numero_afiliado && ` - N° ${selectedPaciente.numero_afiliado}`}
                </Typography>
                
                {selectedPaciente.observaciones && (
                  <>
                    <Typography variant="subtitle2" color="text.secondary">Observaciones</Typography>
                    <Typography variant="body1" sx={{ mb: 2 }}>
                      {selectedPaciente.observaciones}
                    </Typography>
                  </>
                )}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDetailsDialog(false)}>Cerrar</Button>
          <Button
            variant="contained"
            onClick={() => {
              setShowDetailsDialog(false);
              if (selectedPaciente) openPatient360(selectedPaciente);
            }}
          >
            Vista Completa
          </Button>
        </DialogActions>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog
        open={showEditDialog}
        onClose={() => setShowEditDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="h6">Editar Paciente</Typography>
            <IconButton onClick={() => setShowEditDialog(false)} sx={{ color: 'grey.500' }}>
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            Funcionalidad de edición en desarrollo
          </Alert>
          <Typography>
            Aquí se implementará el formulario de edición del paciente.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowEditDialog(false)}>Cancelar</Button>
          <Button variant="contained" disabled>
            Guardar Cambios
          </Button>
        </DialogActions>
      </Dialog>

      {/* Create Dialog */}
      <Dialog
        open={showCreateDialog}
        onClose={() => setShowCreateDialog(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Typography variant="h6">Nuevo Paciente</Typography>
            <IconButton onClick={() => setShowCreateDialog(false)} sx={{ color: 'grey.500' }}>
              <Close />
            </IconButton>
          </Box>
        </DialogTitle>
        <DialogContent>
          {createError && (
            <Alert severity="error" sx={{ mb: 2 }}>{createError}</Alert>
          )}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, mt: 1 }}>
            <TextField
              label="Nombre *"
              value={newPaciente.nombre}
              onChange={(e) => setNewPaciente(prev => ({ ...prev, nombre: e.target.value }))}
              required
              sx={{ flex: '1 1 200px' }}
            />
            <TextField
              label="Apellido *"
              value={newPaciente.apellido}
              onChange={(e) => setNewPaciente(prev => ({ ...prev, apellido: e.target.value }))}
              required
              sx={{ flex: '1 1 200px' }}
            />
            <TextField
              label="DNI *"
              value={newPaciente.dni}
              onChange={(e) => setNewPaciente(prev => ({ ...prev, dni: e.target.value }))}
              required
              sx={{ flex: '1 1 150px' }}
            />
            <TextField
              label="Fecha de Nacimiento"
              type="date"
              value={newPaciente.fecha_nacimiento}
              onChange={(e) => setNewPaciente(prev => ({ ...prev, fecha_nacimiento: e.target.value }))}
              InputLabelProps={{ shrink: true }}
              sx={{ flex: '1 1 180px' }}
            />
            <TextField
              select
              label="Sexo"
              value={newPaciente.sexo}
              onChange={(e) => setNewPaciente(prev => ({ ...prev, sexo: e.target.value as 'M' | 'F' | '' }))}
              sx={{ flex: '1 1 150px' }}
            >
              <MenuItem value="">Seleccionar</MenuItem>
              <MenuItem value="M">Masculino</MenuItem>
              <MenuItem value="F">Femenino</MenuItem>
            </TextField>
            <TextField
              label="Teléfono"
              value={newPaciente.telefono}
              onChange={(e) => setNewPaciente(prev => ({ ...prev, telefono: e.target.value }))}
              sx={{ flex: '1 1 180px' }}
            />
            <TextField
              label="Email"
              type="email"
              value={newPaciente.email}
              onChange={(e) => setNewPaciente(prev => ({ ...prev, email: e.target.value }))}
              sx={{ flex: '1 1 260px' }}
            />
            <TextField
              label="Dirección"
              value={newPaciente.direccion}
              onChange={(e) => setNewPaciente(prev => ({ ...prev, direccion: e.target.value }))}
              fullWidth
            />
            <TextField
              label="Obra Social"
              value={newPaciente.obra_social}
              onChange={(e) => setNewPaciente(prev => ({ ...prev, obra_social: e.target.value }))}
              sx={{ flex: '1 1 260px' }}
            />
            <TextField
              label="N° Afiliado"
              value={newPaciente.numero_afiliado}
              onChange={(e) => setNewPaciente(prev => ({ ...prev, numero_afiliado: e.target.value }))}
              sx={{ flex: '1 1 180px' }}
            />
            <TextField
              label="Observaciones"
              value={newPaciente.observaciones}
              onChange={(e) => setNewPaciente(prev => ({ ...prev, observaciones: e.target.value }))}
              fullWidth
              multiline
              minRows={2}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowCreateDialog(false)} disabled={isCreating}>Cancelar</Button>
          <Button
            variant="contained"
            disabled={isCreating}
            onClick={async () => {
              setCreateError('');
              if (!newPaciente.nombre || !newPaciente.apellido || !newPaciente.dni) {
                setCreateError('Nombre, Apellido y DNI son obligatorios');
                return;
              }
              try {
                setIsCreating(true);
                await createPaciente(newPaciente as any);
                setShowCreateDialog(false);
                setNewPaciente({
                  nombre: '', apellido: '', dni: '', fecha_nacimiento: '', sexo: '', telefono: '', email: '', direccion: '', obra_social: '', numero_afiliado: '', observaciones: ''
                } as any);
                await loadPacientes();
                alert('Paciente creado correctamente');
              } catch (e: unknown) {
                setCreateError(getSafeApiErrorMessage(e, 'Error al crear el paciente'));
              } finally {
                setIsCreating(false);
              }
            }}
          >
            {isCreating ? 'Creando...' : 'Crear Paciente'}
          </Button>
        </DialogActions>
      </Dialog>

    </Box>
  );
};

export default Pacientes;
