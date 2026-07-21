import React, { useCallback, useEffect, useMemo, useState } from 'react';
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
  LinearProgress,
  Tooltip,
  Alert,
} from '@mui/material';
import {
  Phone,
  Email,
  Assignment,
  Edit,
} from '@mui/icons-material';
import { useData } from '../contexts/DataContext';
import { Paciente } from '../types';
import SearchAndFilters from '../components/SearchAndFilters';
import PacienteFormDialog from '../components/PacienteFormDialog';
import { canCreatePaciente, canUpdatePacienteDemographics } from '../utils/permissions';
import { apiService } from '../services/api';

const Pacientes: React.FC = () => {
  const { currentUser, loadPacientes } = useData();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  const [pacientes, setPacientes] = useState<Paciente[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [formOpen, setFormOpen] = useState(false);
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create');
  const [editingPaciente, setEditingPaciente] = useState<Paciente | null>(null);

  useEffect(() => {
    const q = searchParams.get('q');
    if (q !== null) {
      setSearchTerm(q);
    }
  }, [searchParams]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(searchTerm.trim());
      setPage(0);
    }, 350);
    return () => window.clearTimeout(timer);
  }, [searchTerm]);

  const fetchPacientes = useCallback(async () => {
    if (!currentUser) return;
    setLoading(true);
    setLoadError(null);
    try {
      const response = await apiService.getPacientes({
        page: page + 1,
        page_size: rowsPerPage,
        search: debouncedSearch || undefined,
      });
      setPacientes(response.results ?? []);
      setTotalCount(typeof response.count === 'number' ? response.count : (response.results?.length ?? 0));
    } catch (error: unknown) {
      setPacientes([]);
      setTotalCount(0);
      const err = error as { code?: string; message?: string; response?: { status?: number } };
      if (err?.code === 'ERR_NETWORK' || err?.message === 'Network Error') {
        setLoadError(
          'No se pudo conectar con el backend. Verificá que Docker esté activo: ./emrctl up'
        );
      } else {
        setLoadError('No se pudieron cargar los pacientes. Reintentá en unos segundos.');
      }
    } finally {
      setLoading(false);
    }
  }, [currentUser, page, rowsPerPage, debouncedSearch]);

  useEffect(() => {
    void fetchPacientes();
  }, [fetchPacientes]);

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const openPatient360 = (paciente: Paciente) => {
    navigate(`/paciente/${paciente.id}`);
  };

  const openCreate = () => {
    setFormMode('create');
    setEditingPaciente(null);
    setFormOpen(true);
  };

  const openEdit = (paciente: Paciente) => {
    setFormMode('edit');
    setEditingPaciente(paciente);
    setFormOpen(true);
  };

  const handleSaved = () => {
    void fetchPacientes();
    void loadPacientes();
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('es-ES');
  };

  const getSexoColor = (sexo: string | undefined) => {
    return sexo === 'M' ? 'primary' : 'secondary';
  };

  const canCreate = canCreatePaciente(currentUser);
  const canEdit = canUpdatePacienteDemographics(currentUser);

  const medicoHint = useMemo(
    () =>
      currentUser?.rol === 'MEDICO' &&
      totalCount <= 5 &&
      !debouncedSearch &&
      !loading &&
      !loadError,
    [currentUser?.rol, totalCount, debouncedSearch, loading, loadError]
  );

  if (!currentUser) {
    return (
      <Box sx={{ p: 3 }}>
        <LinearProgress />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Cargando sesión...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }} className="fade-in">
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
          Gestión de Pacientes
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {totalCount > 0
            ? `${totalCount.toLocaleString('es-AR')} pacientes en el sistema`
            : 'Administra la información de los pacientes del sistema'}
        </Typography>
      </Box>

      <SearchAndFilters
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        searchPlaceholder="Buscar por nombre, apellido o DNI..."
        filters={{}}
        onRefresh={() => void fetchPacientes()}
        onAdd={canCreate ? openCreate : undefined}
        addButtonText="Nuevo Paciente"
        totalItems={totalCount}
        filteredItems={pacientes.length}
      />

      {loadError && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          action={
            <Button color="inherit" size="small" onClick={() => void fetchPacientes()}>
              Reintentar
            </Button>
          }
        >
          {loadError}
        </Alert>
      )}

      {medicoHint && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Como médico solo ves pacientes con los que tengas turnos o consultas registradas.
          Usá la búsqueda arriba para encontrar un paciente por DNI o apellido dentro de tu alcance.
        </Alert>
      )}

      {loading && <LinearProgress sx={{ mb: 1 }} />}

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
              {!loading && pacientes.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                    <Typography variant="body1" color="text.secondary">
                      {debouncedSearch
                        ? 'No se encontraron pacientes con ese criterio'
                        : loadError
                          ? 'Sin datos — backend no disponible'
                          : 'No hay pacientes registrados'}
                    </Typography>
                  </TableCell>
                </TableRow>
              ) : (
                pacientes.map((paciente) => (
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
                      <Box sx={{ display: 'flex', gap: 0.5 }}>
                        {canEdit && (
                          <Tooltip title="Editar datos del paciente">
                            <IconButton
                              size="small"
                              onClick={() => openEdit(paciente)}
                              color="default"
                            >
                              <Edit fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
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
                              },
                            }}
                          >
                            <Assignment />
                          </IconButton>
                        </Tooltip>
                      </Box>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={totalCount}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          labelRowsPerPage="Filas por página:"
          labelDisplayedRows={({ from, to, count }) => `${from}-${to} de ${count !== -1 ? count : `más de ${to}`}`}
        />
      </Paper>

      <PacienteFormDialog
        open={formOpen}
        mode={formMode}
        paciente={editingPaciente}
        onClose={() => setFormOpen(false)}
        onSaved={handleSaved}
      />
    </Box>
  );
};

export default Pacientes;
