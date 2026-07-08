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
  LinearProgress,
  Tooltip,
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
    if (!loading.pacientes && pacientes.length === 0) {
      loadPacientes();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const formatDate = (dateString: string) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('es-ES');
  };

  const getSexoColor = (sexo: string | undefined) => {
    return sexo === 'M' ? 'primary' : 'secondary';
  };

  const canCreate = canCreatePaciente(currentUser);
  const canEdit = canUpdatePacienteDemographics(currentUser);

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
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" sx={{ fontWeight: 600, mb: 1 }}>
          Gestión de Pacientes
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Administra la información de todos los pacientes del sistema
        </Typography>
      </Box>

      <SearchAndFilters
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        searchPlaceholder="Buscar por nombre, apellido, DNI o email..."
        filters={{}}
        onRefresh={loadPacientes}
        onAdd={canCreate ? openCreate : undefined}
        addButtonText="Nuevo Paciente"
        totalItems={pacientes.length}
        filteredItems={filteredPacientes.length}
      />

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

      <PacienteFormDialog
        open={formOpen}
        mode={formMode}
        paciente={editingPaciente}
        onClose={() => setFormOpen(false)}
        onSaved={loadPacientes}
      />
    </Box>
  );
};

export default Pacientes;
