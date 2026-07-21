import React, { useMemo, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  GridLegacy as Grid,
  TextField,
  MenuItem,
  Button,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  Stack,
} from '@mui/material';
import { FilterAlt, Refresh, Visibility, Edit } from '@mui/icons-material';
import { useData } from '../../contexts/DataContext';
import { AtencionFilters, useAtencionesQuery } from './hooks';
import { Atencion, Medico } from '../../types';
import AtencionDetailDrawer from './components/AtencionDetailDrawer';
import { canOperateAtenciones } from '../../utils/permissions';

const contextoAtencionOptions = [
  { value: '', label: 'Todos' },
  { value: 'AMBULATORIA', label: 'Ambulatoria' },
  { value: 'GUARDIA', label: 'Guardia' },
  { value: 'INTERNACION', label: 'Internación' },
];

const tipoIntervencionOptions = [
  { value: '', label: 'Todos' },
  { value: 'CONSULTA', label: 'Consulta' },
  { value: 'ESTUDIO', label: 'Estudio' },
  { value: 'PROCEDIMIENTO', label: 'Procedimiento' },
  { value: 'CIRUGIA', label: 'Cirugía' },
];

const getContextoLabel = (item: Atencion) =>
  item.contexto_atencion_display ||
  contextoAtencionOptions.find((opt) => opt.value === item.contexto_atencion)?.label ||
  'Ambulatoria';

const getContextoChipColor = (contexto?: string) => {
  switch (contexto) {
    case 'INTERNACION':
      return 'warning';
    case 'GUARDIA':
      return 'error';
    case 'AMBULATORIA':
      return 'info';
    default:
      return 'info';
  }
};

const estadoClinicoOptions = [
  { value: '', label: 'Todos' },
  { value: 'ABIERTA', label: 'Abierta' },
  { value: 'FINALIZADA', label: 'Finalizada' },
  { value: 'EN_REVISION', label: 'En revisión' },
];

const formatDateTime = (value?: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
};

const getEstadoColor = (estado?: string) => {
  switch (estado) {
    case 'FINALIZADA':
      return 'success';
    case 'EN_REVISION':
      return 'warning';
    default:
      return 'info';
  }
};

const getTipoChipColor = (tipo?: string) => {
  switch (tipo) {
    case 'CONSULTA':
      return 'primary';
    case 'ESTUDIO':
      return 'secondary';
    case 'PROCEDIMIENTO':
      return 'warning';
    case 'CIRUGIA':
      return 'error';
    default:
      return 'default';
  }
};

const mapMedicoOptions = (medicos: Medico[]) =>
  medicos
    .filter((medico) => medico && medico.id) // Filtrar médicos inválidos
    .map((medico) => ({
      value: medico.id,
      label: `Dr. ${medico.nombre || ''} ${medico.apellido || ''}`.trim() || `Médico ${medico.id}`,
    }))
    .sort((a, b) => a.label.localeCompare(b.label));

const AtencionesClinicasPage: React.FC = () => {
  const { medicos, currentUser } = useData();
  const [filters, setFilters] = useState<AtencionFilters>({
    tipo_intervencion: '',
    contexto_atencion: '',
    medico_id: undefined,
    estado_clinico: '',
    start_date: '',
    end_date: '',
    search: '',
  });
  const [formFilters, setFormFilters] = useState(filters);
  const [selectedAtencionId, setSelectedAtencionId] = useState<number | null>(null);
  const [isEditMode, setIsEditMode] = useState(false);

  const { data, isLoading, isFetching, refetch } = useAtencionesQuery(filters);

  const medicoOptions = useMemo(() => mapMedicoOptions(medicos), [medicos]);
  const atenciones = (data && 'results' in data ? data.results : []) as Atencion[];
  const canOperate = canOperateAtenciones(currentUser);

  const handleApplyFilters = () => {
    setFilters(formFilters);
  };

  const handleClearFilters = () => {
    const baseFilters: AtencionFilters = {
      tipo_intervencion: '',
      contexto_atencion: '',
      medico_id: undefined,
      estado_clinico: '',
      start_date: '',
      end_date: '',
      search: '',
    };
    setFormFilters(baseFilters);
    setFilters(baseFilters);
  };

  const handleOpenDetail = (id: number) => {
    setSelectedAtencionId(id);
    setIsEditMode(false);
  };

  const handleOpenEdit = (id: number) => {
    setSelectedAtencionId(id);
    setIsEditMode(true);
  };

  const handleCloseDetail = () => {
    setSelectedAtencionId(null);
    setIsEditMode(false);
  };

  return (
    <Box sx={{ p: { xs: 2, md: 3 }, mt: 8 }}>
      <Stack direction={{ xs: 'column', md: 'row' }} justifyContent="space-between" alignItems={{ xs: 'flex-start', md: 'center' }} spacing={2} mb={3}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Atenciones Clínicas
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Visualiza y gestiona los episodios clínicos registrados en el EMR.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1}>
          <Button
            variant="outlined"
            startIcon={<FilterAlt />}
            onClick={handleApplyFilters}
          >
            Aplicar filtros
          </Button>
          <Button
            variant="text"
            onClick={handleClearFilters}
          >
            Limpiar
          </Button>
          <Button
            variant="contained"
            startIcon={<Refresh />}
            onClick={() => refetch()}
            disabled={isFetching}
          >
            Actualizar
          </Button>
        </Stack>
      </Stack>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                select
                label="Contexto"
                value={formFilters.contexto_atencion ?? ''}
                onChange={(event) =>
                  setFormFilters((prev) => ({ ...prev, contexto_atencion: event.target.value || '' }))
                }
              >
                {contextoAtencionOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                select
                label="Tipo de intervención"
                value={formFilters.tipo_intervencion ?? ''}
                onChange={(event) =>
                  setFormFilters((prev) => ({ ...prev, tipo_intervencion: event.target.value || '' }))
                }
              >
                {tipoIntervencionOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                select
                label="Estado clínico"
                value={formFilters.estado_clinico ?? ''}
                onChange={(event) =>
                  setFormFilters((prev) => ({ ...prev, estado_clinico: event.target.value || '' }))
                }
              >
                {estadoClinicoOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                select
                label="Médico responsable"
                value={formFilters.medico_id ?? ''}
                onChange={(event) =>
                  setFormFilters((prev) => ({
                    ...prev,
                    medico_id: event.target.value ? Number(event.target.value) : undefined,
                  }))
                }
              >
                <MenuItem value="">Todos</MenuItem>
                {medicoOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Búsqueda rápida"
                placeholder="Paciente, médico, notas..."
                value={formFilters.search ?? ''}
                onChange={(event) =>
                  setFormFilters((prev) => ({ ...prev, search: event.target.value }))
                }
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Desde"
                type="date"
                InputLabelProps={{ shrink: true }}
                value={formFilters.start_date ?? ''}
                onChange={(event) =>
                  setFormFilters((prev) => ({ ...prev, start_date: event.target.value }))
                }
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                fullWidth
                label="Hasta"
                type="date"
                InputLabelProps={{ shrink: true }}
                value={formFilters.end_date ?? ''}
                onChange={(event) =>
                  setFormFilters((prev) => ({ ...prev, end_date: event.target.value }))
                }
              />
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardContent sx={{ position: 'relative', minHeight: 200 }}>
          {isLoading ? (
            <Box display="flex" alignItems="center" justifyContent="center" py={6}>
              <CircularProgress />
            </Box>
          ) : atenciones.length === 0 ? (
            <Box py={6} textAlign="center">
              <Typography variant="h6" color="text.secondary">
                No se encontraron atenciones con los filtros seleccionados.
              </Typography>
            </Box>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Fecha</TableCell>
                  <TableCell>Paciente</TableCell>
                  <TableCell>Médico</TableCell>
                  <TableCell>Tipo</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Recurso / Ubicación</TableCell>
                  <TableCell align="right">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {atenciones.map((item) => (
                  <TableRow key={item.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>
                        {formatDateTime(item.fecha_admision)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {item.fecha_cierre ? `Cierre: ${formatDateTime(item.fecha_cierre)}` : 'Sin cierre'}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      {item.paciente ? (
                        <>
                          <Typography variant="body2" fontWeight={600}>
                            {item.paciente.apellido || ''}, {item.paciente.nombre || ''}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            DNI {item.paciente.dni || 'N/A'}
                          </Typography>
                        </>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Paciente no disponible
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      {item.medico_principal ? (
                        <Typography variant="body2">
                          Dr. {item.medico_principal.apellido || ''}, {item.medico_principal.nombre || ''}
                        </Typography>
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          Médico no disponible
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                        <Chip
                          size="small"
                          label={getContextoLabel(item)}
                          color={getContextoChipColor(item.contexto_atencion)}
                        />
                        {item.tipo_intervencion && item.tipo_intervencion !== 'CONSULTA' && (
                          <Chip
                            size="small"
                            label={
                              tipoIntervencionOptions.find((opt) => opt.value === item.tipo_intervencion)?.label ??
                              item.tipo_intervencion
                            }
                            color={getTipoChipColor(item.tipo_intervencion)}
                            variant="outlined"
                          />
                        )}
                      </Stack>
                    </TableCell>
                    <TableCell>
                      <Chip
                        size="small"
                        label={estadoClinicoOptions.find((opt) => opt.value === item.estado_clinico)?.label ?? item.estado_clinico}
                        color={getEstadoColor(item.estado_clinico)}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">
                        {item.turno?.recurso?.nombre ?? '—'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {item.turno?.recurso?.ubicacion_display ?? ''}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Ver detalle">
                        <IconButton onClick={() => handleOpenDetail(item.id)}>
                          <Visibility />
                        </IconButton>
                      </Tooltip>
                      {canOperate && (
                        <Tooltip title="Editar">
                          <IconButton onClick={() => handleOpenEdit(item.id)} color="primary">
                            <Edit />
                          </IconButton>
                        </Tooltip>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
          {isFetching && !isLoading && (
            <Box
              position="absolute"
              top={0}
              left={0}
              right={0}
              display="flex"
              justifyContent="flex-end"
              p={1}
            >
              <CircularProgress size={24} />
            </Box>
          )}
        </CardContent>
      </Card>

      <AtencionDetailDrawer
        atencionId={selectedAtencionId}
        open={Boolean(selectedAtencionId)}
        onClose={handleCloseDetail}
        currentUser={currentUser}
        canOperate={canOperate}
        forceEdit={isEditMode}
      />
    </Box>
  );
};

export default AtencionesClinicasPage;

