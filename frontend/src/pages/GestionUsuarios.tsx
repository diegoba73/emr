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
  Switch,
  FormControlLabel,
  InputAdornment,
  Autocomplete,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Add,
  Edit,
  Search,
  Lock,
  LockOpen,
} from '@mui/icons-material';
import { useData } from '../contexts/DataContext';
import { User, Paciente, Medico, Especialidad } from '../types';
import { apiService } from '../services/api';
import { getEspecialidades } from '../services/apiService';
import { formatPacienteLabel } from '../utils/pacienteFormat';

function mapUserManagementHttpError(status: number | undefined, fallback: string): string {
  if (status === 403) {
    return 'No tiene permisos para realizar esta acción.';
  }
  if (status === 405) {
    return 'No se permite eliminar usuarios. Podés desactivarlos para preservar la trazabilidad.';
  }
  if (status === 401) {
    return 'Sesión expirada o no autenticado. Inicie sesión nuevamente.';
  }
  return fallback;
}

function getErrorStatus(err: unknown): number | undefined {
  const e = err as { response?: { status?: number } };
  return e.response?.status;
}

interface UserFormData {
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  telefono: string;
  rol: string;
  password: string;
  password_confirm: string;
  is_active: boolean;
  is_staff: boolean;
}

const GestionUsuarios: React.FC = () => {
  const { currentUser } = useData();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchTerm, setSearchTerm] = useState('');
  const [showDialog, setShowDialog] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [formData, setFormData] = useState<UserFormData>({
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    telefono: '',
    rol: 'paciente',
    password: '',
    password_confirm: '',
    is_active: true,
    is_staff: false,
  });
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  
  // Estados para asociación con médico/paciente
  const [medicoSeleccionado, setMedicoSeleccionado] = useState<Medico | null>(null);
  const [pacienteSeleccionado, setPacienteSeleccionado] = useState<Paciente | null>(null);
  const [medicoOptions, setMedicoOptions] = useState<Medico[]>([]);
  const [pacienteOptions, setPacienteOptions] = useState<Paciente[]>([]);
  const [medicoInputValue, setMedicoInputValue] = useState('');
  const [pacienteInputValue, setPacienteInputValue] = useState('');
  const [searchingMedicos, setSearchingMedicos] = useState(false);
  const [searchingPacientes, setSearchingPacientes] = useState(false);
  const [crearNuevoMedico, setCrearNuevoMedico] = useState(false);
  const [crearNuevoPaciente, setCrearNuevoPaciente] = useState(false);
  const [especialidades, setEspecialidades] = useState<Especialidad[]>([]);
  
  // Datos para crear nuevo médico
  const [nuevoMedicoData, setNuevoMedicoData] = useState({
    matricula: '',
    especialidad_id: '',
    areas_interes_ia: '',
  });
  
  // Datos para crear nuevo paciente
  const [nuevoPacienteData, setNuevoPacienteData] = useState({
    dni: '',
    fecha_nacimiento: '',
    sexo: '',
    direccion: '',
    obra_social: '',
    numero_afiliado: '',
    observaciones: '',
    antecedentes_personales: '',
    antecedentes_familiares: '',
  });

  // Verificar permisos - solo admin
  const isAdmin = currentUser?.rol === 'ADMIN' || currentUser?.is_superuser;

  const ROL_CHOICES = [
    { value: 'paciente', label: 'Paciente' },
    { value: 'medico', label: 'Médico' },
    { value: 'secretaria', label: 'Secretaria' },
    { value: 'enfermeria', label: 'Enfermería' },
    { value: 'laboratorio', label: 'Laboratorio' },
    { value: 'bioquimico', label: 'Bioquímico' },
    { value: 'kinesiologo', label: 'Kinesiólogo' },
    { value: 'radiologo', label: 'Radiólogo' },
    { value: 'ecografista', label: 'Ecografista' },
    { value: 'fonoaudiologo', label: 'Fonoaudiólogo' },
    { value: 'admin', label: 'Administrador' },
  ];

  useEffect(() => {
    if (!isAdmin) {
      return;
    }
    loadUsers();
    loadEspecialidades();
  }, [isAdmin]);
  
  const loadEspecialidades = async () => {
    try {
      const data = await getEspecialidades();
      // getEspecialidades siempre devuelve un array
      setEspecialidades(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Error cargando especialidades:', error);
      setEspecialidades([]);
    }
  };
  
  // Búsqueda de médicos
  useEffect(() => {
    if (formData.rol !== 'medico' || !showDialog) {
      return;
    }
    
    const query = medicoInputValue.trim();
    if (query.length < 2) {
      setMedicoOptions([]);
      return;
    }
    
    // Debounce optimizado: 200ms para búsquedas más rápidas
    const timeoutId = setTimeout(async () => {
      setSearchingMedicos(true);
      try {
        const results = await apiService.buscarMedicos(query);
        setMedicoOptions(results);
      } catch (error) {
        console.error('Error buscando médicos:', error);
        setMedicoOptions([]);
      } finally {
        setSearchingMedicos(false);
      }
    }, 200);
    
    return () => clearTimeout(timeoutId);
  }, [medicoInputValue, formData.rol, showDialog]);
  
  // Búsqueda de pacientes
  useEffect(() => {
    if (formData.rol !== 'paciente' || !showDialog) {
      return;
    }
    
    const query = pacienteInputValue.trim();
    if (query.length < 2) {
      setPacienteOptions([]);
      return;
    }
    
    // Debounce optimizado: 200ms para búsquedas más rápidas
    const timeoutId = setTimeout(async () => {
      setSearchingPacientes(true);
      try {
        const results = await apiService.buscarPacientes(query);
        setPacienteOptions(results);
      } catch (error) {
        console.error('Error buscando pacientes:', error);
        setPacienteOptions([]);
      } finally {
        setSearchingPacientes(false);
      }
    }, 200);
    
    return () => clearTimeout(timeoutId);
  }, [pacienteInputValue, formData.rol, showDialog]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError('');
      const allUsers = await apiService.listUsersForManagement();
      setUsers(allUsers);
    } catch (err: unknown) {
      const status = getErrorStatus(err);
      const msg =
        mapUserManagementHttpError(
          status,
          'Error al cargar los usuarios. Intente nuevamente.',
        );
      setError(msg);
      console.error('Error loading users:', err);
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = useMemo(() => {
    if (!searchTerm.trim()) return users;
    const search = searchTerm.toLowerCase();
    return users.filter(
      (user) =>
        user.username?.toLowerCase().includes(search) ||
        user.email?.toLowerCase().includes(search) ||
        user.first_name?.toLowerCase().includes(search) ||
        user.last_name?.toLowerCase().includes(search) ||
        user.rol?.toLowerCase().includes(search)
    );
  }, [users, searchTerm]);

  const paginatedUsers = filteredUsers.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  const handleOpenDialog = (user?: User) => {
    if (user) {
      setEditingUser(user);
      setFormData({
        username: user.username || '',
        email: user.email || '',
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        telefono: user.telefono || '',
        rol: (user.rol || 'paciente').toLowerCase(),
        password: '',
        password_confirm: '',
        is_active: user.is_active ?? true,
        is_staff: user.is_staff ?? false,
      });
    } else {
      setEditingUser(null);
      setFormData({
        username: '',
        email: '',
        first_name: '',
        last_name: '',
        telefono: '',
        rol: 'paciente',
        password: '',
        password_confirm: '',
        is_active: true,
        is_staff: false,
      });
    }
    // Resetear estados de médico/paciente
    setMedicoSeleccionado(null);
    setPacienteSeleccionado(null);
    setMedicoInputValue('');
    setPacienteInputValue('');
    setCrearNuevoMedico(false);
    setCrearNuevoPaciente(false);
    setNuevoMedicoData({ matricula: '', especialidad_id: '', areas_interes_ia: '' });
    setNuevoPacienteData({
      dni: '',
      fecha_nacimiento: '',
      sexo: '',
      direccion: '',
      obra_social: '',
      numero_afiliado: '',
      observaciones: '',
      antecedentes_personales: '',
      antecedentes_familiares: '',
    });
    setError('');
    setSuccessMessage('');
    setShowDialog(true);
  };

  const handleCloseDialog = () => {
    setShowDialog(false);
    setEditingUser(null);
    setMedicoSeleccionado(null);
    setPacienteSeleccionado(null);
    setMedicoInputValue('');
    setPacienteInputValue('');
    setCrearNuevoMedico(false);
    setCrearNuevoPaciente(false);
    setError('');
    setSuccessMessage('');
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');
      setSuccessMessage('');

      // Validaciones
      if (!formData.username.trim()) {
        setError('El nombre de usuario es requerido');
        setSaving(false);
        return;
      }
      if (!formData.email.trim()) {
        setError('El email es requerido');
        setSaving(false);
        return;
      }
      if (!editingUser && !formData.password) {
        setError('La contraseña es requerida para nuevos usuarios');
        setSaving(false);
        return;
      }
      if (formData.password && formData.password !== formData.password_confirm) {
        setError('Las contraseñas no coinciden');
        setSaving(false);
        return;
      }

      const payload: Record<string, unknown> = {
        username: formData.username,
        email: formData.email,
        first_name: formData.first_name,
        last_name: formData.last_name,
        telefono: formData.telefono,
        rol: formData.rol,
        is_active: formData.is_active,
        is_staff: formData.is_staff,
      };

      // Solo incluir password si se está creando o cambiando
      if (!editingUser || formData.password) {
        payload.password = formData.password;
        payload.password_confirm = formData.password_confirm;
      }
      
      // Agregar datos de médico/paciente según el rol
      if (formData.rol === 'medico') {
        if (crearNuevoMedico) {
          // Crear nuevo médico
          payload.medico_data = {
            matricula: nuevoMedicoData.matricula,
            especialidad_id: nuevoMedicoData.especialidad_id ? parseInt(nuevoMedicoData.especialidad_id, 10) : null,
            areas_interes_ia: nuevoMedicoData.areas_interes_ia || null,
          };
        } else if (medicoSeleccionado) {
          // Asociar con médico existente
          payload.medico_id = medicoSeleccionado.id;
        }
      } else if (formData.rol === 'paciente') {
        if (crearNuevoPaciente) {
          // Crear nuevo paciente
          payload.paciente_data = {
            dni: nuevoPacienteData.dni,
            fecha_nacimiento: nuevoPacienteData.fecha_nacimiento || null,
            sexo: nuevoPacienteData.sexo || null,
            direccion: nuevoPacienteData.direccion || null,
            obra_social: nuevoPacienteData.obra_social || null,
            numero_afiliado: nuevoPacienteData.numero_afiliado || null,
            observaciones: nuevoPacienteData.observaciones || null,
            antecedentes_personales: nuevoPacienteData.antecedentes_personales || null,
            antecedentes_familiares: nuevoPacienteData.antecedentes_familiares || null,
          };
        } else if (pacienteSeleccionado) {
          // Asociar con paciente existente
          payload.paciente_id = pacienteSeleccionado.id;
        }
      }

      if (editingUser) {
        await apiService.updateUserManagement(editingUser.id, payload);
      } else {
        await apiService.createUserManagement(payload);
      }

      setSuccessMessage(editingUser ? 'Usuario actualizado correctamente' : 'Usuario creado correctamente');
      setTimeout(() => {
        handleCloseDialog();
        loadUsers();
      }, 1000);
    } catch (error: unknown) {
      console.error('Error saving user:', error);
      const status = getErrorStatus(error);
      const ax = error as { response?: { data?: unknown } };
      const detail =
        ax.response?.data &&
        typeof ax.response.data === 'object' &&
        'detail' in (ax.response.data as object) &&
        typeof (ax.response.data as { detail?: unknown }).detail === 'string'
          ? (ax.response.data as { detail: string }).detail
          : null;
      setError(
        mapUserManagementHttpError(
          status,
          detail || 'Error al guardar el usuario. Verifique los datos e intente nuevamente.',
        ),
      );
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (user: User) => {
    const isSelf = currentUser?.id != null && user.id === currentUser.id;
    if (user.is_active && isSelf) {
      setError('No podés desactivar tu propio usuario desde esta pantalla.');
      return;
    }

    const actionLabel = user.is_active ? 'desactivar' : 'activar';
    if (!window.confirm(`¿Querés ${actionLabel} este usuario?`)) {
      return;
    }

    try {
      setError('');
      setSuccessMessage('');
      if (user.is_active) {
        await apiService.deactivateUserManagement(user.id);
        setSuccessMessage('Usuario desactivado correctamente');
      } else {
        await apiService.activateUserManagement(user.id);
        setSuccessMessage('Usuario activado correctamente');
      }
      await loadUsers();
    } catch (err: unknown) {
      const status = getErrorStatus(err);
      setError(
        mapUserManagementHttpError(
          status,
          'No se pudo cambiar el estado del usuario. Intente nuevamente.',
        ),
      );
      console.error('Error toggling user active:', err);
    }
  };

  const getRolDisplay = (rol: string) => {
    const rolChoice = ROL_CHOICES.find((r) => r.value === rol?.toLowerCase());
    return rolChoice?.label || rol || 'Sin rol';
  };

  if (!isAdmin) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">No tiene permisos para acceder a esta sección.</Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4" component="h1" sx={{ fontWeight: 600 }}>
          Gestión de Usuarios
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={() => handleOpenDialog()}
        >
          Nuevo Usuario
        </Button>
      </Box>

      {error && !showDialog && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {successMessage && !showDialog && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccessMessage('')}>
          {successMessage}
        </Alert>
      )}

      <Paper sx={{ mb: 2 }}>
        <Box sx={{ p: 2 }}>
          <TextField
            fullWidth
            placeholder="Buscar usuarios..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search />
                </InputAdornment>
              ),
            }}
          />
        </Box>
      </Paper>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Usuario</TableCell>
                  <TableCell>Nombre</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Rol</TableCell>
                  <TableCell>Teléfono</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Staff</TableCell>
                  <TableCell align="right">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {paginatedUsers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} align="center">
                      No hay usuarios disponibles
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedUsers.map((user) => (
                    <TableRow key={user.id} hover>
                      <TableCell>{user.username}</TableCell>
                      <TableCell>
                        {user.first_name} {user.last_name}
                      </TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        <Chip
                          label={getRolDisplay(user.rol || '')}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>{user.telefono || '-'}</TableCell>
                      <TableCell>
                        <Chip
                          label={user.is_active ? 'Activo' : 'Inactivo'}
                          size="small"
                          color={user.is_active ? 'success' : 'default'}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={user.is_staff ? 'Sí' : 'No'}
                          size="small"
                          color={user.is_staff ? 'info' : 'default'}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          onClick={() => handleToggleActive(user)}
                          disabled={Boolean(user.is_active && currentUser?.id != null && user.id === currentUser.id)}
                          title={
                            user.is_active && currentUser?.id != null && user.id === currentUser.id
                              ? 'No podés desactivar tu propio usuario'
                              : user.is_active
                                ? 'Desactivar usuario'
                                : 'Activar usuario'
                          }
                        >
                          {user.is_active ? <LockOpen /> : <Lock />}
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={() => handleOpenDialog(user)}
                          title="Editar"
                        >
                          <Edit />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <TablePagination
            component="div"
            count={filteredUsers.length}
            page={page}
            onPageChange={(_, newPage) => setPage(newPage)}
            rowsPerPage={rowsPerPage}
            onRowsPerPageChange={(e) => {
              setRowsPerPage(parseInt(e.target.value, 10));
              setPage(0);
            }}
            rowsPerPageOptions={[5, 10, 25, 50]}
          />
        </>
      )}

      <Dialog open={showDialog} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingUser ? 'Editar Usuario' : 'Nuevo Usuario'}
        </DialogTitle>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}
          {successMessage && (
            <Alert severity="success" sx={{ mb: 2 }}>
              {successMessage}
            </Alert>
          )}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
            <TextField
              label="Nombre de Usuario"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              required
              disabled={!!editingUser}
            />
            <TextField
              label="Email"
              type="email"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="Nombre"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                fullWidth
              />
              <TextField
                label="Apellido"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                fullWidth
              />
            </Box>
            <TextField
              label="Teléfono"
              value={formData.telefono}
              onChange={(e) => setFormData({ ...formData, telefono: e.target.value })}
            />
            <TextField
              select
              label="Rol"
              value={formData.rol}
              onChange={(e) => {
                setFormData({ ...formData, rol: e.target.value });
                // Resetear selecciones cuando cambia el rol
                setMedicoSeleccionado(null);
                setPacienteSeleccionado(null);
                setCrearNuevoMedico(false);
                setCrearNuevoPaciente(false);
                setMedicoInputValue('');
                setPacienteInputValue('');
              }}
              required
            >
              {ROL_CHOICES.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            
            {/* Sección para asociar con médico */}
            {formData.rol === 'medico' && !editingUser && (
              <Box sx={{ border: '1px solid #e0e0e0', borderRadius: 1, p: 2, bgcolor: '#f5f5f5' }}>
                <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
                  Asociar con Médico
                </Typography>
                <Tabs
                  value={crearNuevoMedico ? 1 : 0}
                  onChange={(_, newValue) => {
                    setCrearNuevoMedico(newValue === 1);
                    setMedicoSeleccionado(null);
                    setMedicoInputValue('');
                  }}
                  sx={{ mb: 2 }}
                >
                  <Tab label="Buscar Médico Existente" />
                  <Tab label="Crear Nuevo Médico" />
                </Tabs>
                
                {!crearNuevoMedico ? (
                  <Box>
                    <Autocomplete
                      options={medicoOptions}
                      getOptionLabel={(option) => {
                        const nombre = option.apellido || option.nombre 
                          ? `${option.apellido || ''}, ${option.nombre || ''}`.trim()
                          : `Médico ${option.id}`;
                        const esp = option.especialidad?.nombre || '';
                        return `${nombre}${esp ? ` - ${esp}` : ''}`.trim();
                      }}
                      value={medicoSeleccionado}
                      inputValue={medicoInputValue}
                      onInputChange={(_, newValue) => setMedicoInputValue(newValue)}
                      onChange={(_, newValue) => {
                        setMedicoSeleccionado(newValue);
                        if (newValue) {
                          // Sincronizar campos del médico al usuario (solo si el usuario no tiene esos campos)
                          setFormData({
                            ...formData,
                            first_name: formData.first_name || newValue.nombre || '',
                            last_name: formData.last_name || newValue.apellido || '',
                            // Email y teléfono del médico vienen del user, pero por si acaso los sincronizamos si están disponibles
                            email: formData.email || newValue.email || '',
                            telefono: formData.telefono || newValue.telefono || '',
                          });
                        } else {
                          // Si se deselecciona, no limpiar los campos (el usuario puede haberlos editado)
                        }
                      }}
                      loading={searchingMedicos}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Buscar Médico"
                          placeholder="Escriba al menos 2 caracteres para buscar por nombre o apellido..."
                          helperText={medicoSeleccionado 
                            ? `Médico seleccionado: ${medicoSeleccionado.matricula || 'Sin matrícula'}`
                            : 'Busque un médico existente para asociarlo con este usuario'}
                        />
                      )}
                      filterOptions={(options) => options}
                      noOptionsText={
                        searchingMedicos 
                          ? "Buscando..." 
                          : medicoInputValue.length < 2 
                            ? "Escriba al menos 2 caracteres"
                            : "No se encontraron médicos"
                      }
                    />
                    {medicoSeleccionado && (
                      <Alert severity="info" sx={{ mt: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
                          Información del Médico Seleccionado:
                        </Typography>
                        <Box component="ul" sx={{ m: 0, pl: 2 }}>
                          <li>
                            <strong>Nombre:</strong> {medicoSeleccionado.nombre || 'N/A'} {medicoSeleccionado.apellido || ''}
                          </li>
                          <li>
                            <strong>Matrícula:</strong> {medicoSeleccionado.matricula || 'N/A'}
                          </li>
                          <li>
                            <strong>Especialidad:</strong> {medicoSeleccionado.especialidad?.nombre || 'Sin especialidad'}
                          </li>
                          {medicoSeleccionado.email && (
                            <li>
                              <strong>Email:</strong> {medicoSeleccionado.email}
                            </li>
                          )}
                          {medicoSeleccionado.telefono && (
                            <li>
                              <strong>Teléfono:</strong> {medicoSeleccionado.telefono}
                            </li>
                          )}
                        </Box>
                        <Typography variant="caption" sx={{ mt: 1, display: 'block', fontStyle: 'italic' }}>
                          Los campos Email y Teléfono se han copiado automáticamente al formulario del usuario si estaban vacíos.
                        </Typography>
                      </Alert>
                    )}
                  </Box>
                ) : (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <TextField
                      label="Matrícula *"
                      value={nuevoMedicoData.matricula}
                      onChange={(e) => setNuevoMedicoData({ ...nuevoMedicoData, matricula: e.target.value })}
                      required
                      helperText="Matrícula profesional del médico"
                    />
                    <TextField
                      select
                      label="Especialidad"
                      value={nuevoMedicoData.especialidad_id}
                      onChange={(e) => setNuevoMedicoData({ ...nuevoMedicoData, especialidad_id: e.target.value })}
                      fullWidth
                    >
                      <MenuItem value="">Sin especialidad</MenuItem>
                      {especialidades.map((esp) => (
                        <MenuItem key={esp.id} value={String(esp.id)}>
                          {esp.nombre}
                        </MenuItem>
                      ))}
                    </TextField>
                    <TextField
                      label="Áreas de Interés (IA)"
                      multiline
                      rows={2}
                      value={nuevoMedicoData.areas_interes_ia}
                      onChange={(e) => setNuevoMedicoData({ ...nuevoMedicoData, areas_interes_ia: e.target.value })}
                      helperText="Opcional: áreas de interés para inteligencia artificial"
                    />
                  </Box>
                )}
              </Box>
            )}
            
            {/* Sección para asociar con paciente */}
            {formData.rol === 'paciente' && !editingUser && (
              <Box sx={{ border: '1px solid #e0e0e0', borderRadius: 1, p: 2, bgcolor: '#f5f5f5' }}>
                <Typography variant="subtitle2" sx={{ mb: 2, fontWeight: 600 }}>
                  Asociar con Paciente
                </Typography>
                <Tabs
                  value={crearNuevoPaciente ? 1 : 0}
                  onChange={(_, newValue) => {
                    setCrearNuevoPaciente(newValue === 1);
                    setPacienteSeleccionado(null);
                    setPacienteInputValue('');
                  }}
                  sx={{ mb: 2 }}
                >
                  <Tab label="Buscar Paciente Existente" />
                  <Tab label="Crear Nuevo Paciente" />
                </Tabs>
                
                {!crearNuevoPaciente ? (
                  <Box>
                    <Autocomplete
                      options={pacienteOptions}
                      getOptionLabel={(option) => formatPacienteLabel(option)}
                      value={pacienteSeleccionado}
                      inputValue={pacienteInputValue}
                      onInputChange={(_, newValue) => setPacienteInputValue(newValue)}
                      onChange={(_, newValue) => {
                        setPacienteSeleccionado(newValue);
                        if (newValue) {
                          // Sincronizar campos del paciente al usuario (solo si el usuario no tiene esos campos)
                          setFormData({
                            ...formData,
                            first_name: formData.first_name || newValue.nombre || '',
                            last_name: formData.last_name || newValue.apellido || '',
                            email: formData.email || newValue.email || '',
                            telefono: formData.telefono || newValue.telefono || '',
                          });
                        } else {
                          // Si se deselecciona, no limpiar los campos (el usuario puede haberlos editado)
                        }
                      }}
                      renderOption={(props, option) => (
                        <li {...props} key={option.id}>
                          {formatPacienteLabel(option)}
                        </li>
                      )}
                      loading={searchingPacientes}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Buscar Paciente"
                          placeholder="Escriba al menos 2 caracteres para buscar por nombre, apellido o DNI..."
                          helperText={pacienteSeleccionado 
                            ? `Paciente seleccionado: DNI ${pacienteSeleccionado.dni || 'N/A'}`
                            : 'Busque un paciente existente para asociarlo con este usuario'}
                        />
                      )}
                      filterOptions={(options) => options}
                      noOptionsText={
                        searchingPacientes 
                          ? "Buscando..." 
                          : pacienteInputValue.length < 2 
                            ? "Escriba al menos 2 caracteres"
                            : "No se encontraron pacientes"
                      }
                    />
                    {pacienteSeleccionado && (
                      <Alert severity="info" sx={{ mt: 2 }}>
                        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
                          Información del Paciente Seleccionado:
                        </Typography>
                        <Box component="ul" sx={{ m: 0, pl: 2 }}>
                          <li>
                            <strong>Nombre:</strong> {pacienteSeleccionado.nombre || 'N/A'} {pacienteSeleccionado.apellido || ''}
                          </li>
                          <li>
                            <strong>DNI:</strong> {pacienteSeleccionado.dni || 'N/A'}
                          </li>
                          {pacienteSeleccionado.fecha_nacimiento && (
                            <li>
                              <strong>Fecha de Nacimiento:</strong> {new Date(pacienteSeleccionado.fecha_nacimiento).toLocaleDateString()}
                            </li>
                          )}
                          {pacienteSeleccionado.sexo && (
                            <li>
                              <strong>Sexo:</strong> {pacienteSeleccionado.sexo === 'M' ? 'Masculino' : pacienteSeleccionado.sexo === 'F' ? 'Femenino' : 'Otro'}
                            </li>
                          )}
                          {pacienteSeleccionado.email && (
                            <li>
                              <strong>Email:</strong> {pacienteSeleccionado.email}
                            </li>
                          )}
                          {pacienteSeleccionado.telefono && (
                            <li>
                              <strong>Teléfono:</strong> {pacienteSeleccionado.telefono}
                            </li>
                          )}
                          {pacienteSeleccionado.direccion && (
                            <li>
                              <strong>Dirección:</strong> {pacienteSeleccionado.direccion}
                            </li>
                          )}
                          {pacienteSeleccionado.obra_social && (
                            <li>
                              <strong>Obra Social:</strong> {pacienteSeleccionado.obra_social}
                            </li>
                          )}
                        </Box>
                        <Typography variant="caption" sx={{ mt: 1, display: 'block', fontStyle: 'italic' }}>
                          Los campos Nombre, Apellido, Email y Teléfono se han copiado automáticamente al formulario del usuario si estaban vacíos.
                        </Typography>
                      </Alert>
                    )}
                  </Box>
                ) : (
                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <TextField
                      label="DNI *"
                      value={nuevoPacienteData.dni}
                      onChange={(e) => setNuevoPacienteData({ ...nuevoPacienteData, dni: e.target.value })}
                      required
                      helperText="Documento Nacional de Identidad"
                    />
                    <Box sx={{ display: 'flex', gap: 2 }}>
                      <TextField
                        label="Fecha de Nacimiento"
                        type="date"
                        value={nuevoPacienteData.fecha_nacimiento}
                        onChange={(e) => setNuevoPacienteData({ ...nuevoPacienteData, fecha_nacimiento: e.target.value })}
                        InputLabelProps={{ shrink: true }}
                        fullWidth
                      />
                      <TextField
                        select
                        label="Sexo"
                        value={nuevoPacienteData.sexo}
                        onChange={(e) => setNuevoPacienteData({ ...nuevoPacienteData, sexo: e.target.value })}
                        sx={{ minWidth: 150 }}
                      >
                        <MenuItem value="">No especificado</MenuItem>
                        <MenuItem value="M">Masculino</MenuItem>
                        <MenuItem value="F">Femenino</MenuItem>
                        <MenuItem value="O">Otro</MenuItem>
                      </TextField>
                    </Box>
                    <TextField
                      label="Dirección"
                      multiline
                      rows={2}
                      value={nuevoPacienteData.direccion}
                      onChange={(e) => setNuevoPacienteData({ ...nuevoPacienteData, direccion: e.target.value })}
                    />
                    <Box sx={{ display: 'flex', gap: 2 }}>
                      <TextField
                        label="Obra Social"
                        value={nuevoPacienteData.obra_social}
                        onChange={(e) => setNuevoPacienteData({ ...nuevoPacienteData, obra_social: e.target.value })}
                        fullWidth
                      />
                      <TextField
                        label="Número de Afiliado"
                        value={nuevoPacienteData.numero_afiliado}
                        onChange={(e) => setNuevoPacienteData({ ...nuevoPacienteData, numero_afiliado: e.target.value })}
                        fullWidth
                      />
                    </Box>
                    <TextField
                      label="Antecedentes Personales"
                      multiline
                      rows={3}
                      value={nuevoPacienteData.antecedentes_personales}
                      onChange={(e) => setNuevoPacienteData({ ...nuevoPacienteData, antecedentes_personales: e.target.value })}
                    />
                    <TextField
                      label="Antecedentes Familiares"
                      multiline
                      rows={3}
                      value={nuevoPacienteData.antecedentes_familiares}
                      onChange={(e) => setNuevoPacienteData({ ...nuevoPacienteData, antecedentes_familiares: e.target.value })}
                    />
                    <TextField
                      label="Observaciones"
                      multiline
                      rows={2}
                      value={nuevoPacienteData.observaciones}
                      onChange={(e) => setNuevoPacienteData({ ...nuevoPacienteData, observaciones: e.target.value })}
                    />
                  </Box>
                )}
              </Box>
            )}
            
            <TextField
              label={editingUser ? 'Nueva Contraseña (dejar vacío para no cambiar)' : 'Contraseña'}
              type="password"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required={!editingUser}
            />
            <TextField
              label="Confirmar Contraseña"
              type="password"
              value={formData.password_confirm}
              onChange={(e) => setFormData({ ...formData, password_confirm: e.target.value })}
              required={!editingUser || !!formData.password}
            />
            <FormControlLabel
              control={
                <Switch
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                />
              }
              label="Usuario Activo"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={formData.is_staff}
                  onChange={(e) => setFormData({ ...formData, is_staff: e.target.checked })}
                />
              }
              label="Es Staff"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancelar</Button>
          <Button
            onClick={handleSave}
            variant="contained"
            disabled={saving}
          >
            {saving ? <CircularProgress size={20} /> : editingUser ? 'Actualizar' : 'Crear'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default GestionUsuarios;

