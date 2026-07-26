import React, { useMemo, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
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
import {
  Add,
  Refresh,
  Visibility,
  Edit,
  LocalHospital,
  TransferWithinAStation,
  CheckCircleOutline,
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../contexts/DataContext';
import { AtencionFilters, useAtencionesQuery } from '../modules/atenciones/hooks';
import { Atencion } from '../types';
import GuardiaAtencionDialog, {
  GuardiaDialogMode,
} from '../modules/guardia/components/GuardiaAtencionDialog';
import { canOperateAtenciones } from '../utils/permissions';
import { apiService } from '../services/api';

const formatDateTime = (value?: string | null) => {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
};

const GuardiaPage: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [filters] = useState<AtencionFilters>({
    contexto_atencion: 'GUARDIA',
  });
  const { data, isLoading, isFetching, refetch } = useAtencionesQuery(filters);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<GuardiaDialogMode>('create');
  const [dialogAtencionId, setDialogAtencionId] = useState<number | null>(null);
  const [closingId, setClosingId] = useState<number | null>(null);

  const canOperate = canOperateAtenciones(currentUser);
  const atenciones = useMemo(() => data?.results ?? [], [data?.results]);

  const openDialog = (mode: GuardiaDialogMode, atencionId?: number) => {
    setDialogMode(mode);
    setDialogAtencionId(atencionId ?? null);
    setDialogOpen(true);
  };

  const derivarInternacion = (atencion: Atencion) => {
    const pacienteId =
      typeof atencion.paciente === 'object' ? atencion.paciente.id : atencion.paciente_id;
    navigate('/internacion', {
      state: {
        derivarDesdeAtencionId: atencion.id,
        pacienteId,
        motivoIngreso: atencion.observaciones_generales ?? '',
      },
    });
  };

  const cerrarAtencion = async (atencion: Atencion) => {
    if (
      !window.confirm(
        '¿Cerrar esta atención de guardia? Los pedidos de laboratorio y estudios siguen su curso.'
      )
    ) {
      return;
    }
    setClosingId(atencion.id);
    try {
      await apiService.closeAtencion(atencion.id);
      toast.success('Atención cerrada.');
      await refetch();
    } catch (err: unknown) {
      const ax = err as { response?: { data?: { error?: string; detail?: string } } };
      toast.error(
        ax.response?.data?.error ||
          ax.response?.data?.detail ||
          'No se pudo cerrar la atención.'
      );
    } finally {
      setClosingId(null);
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" alignItems="center" spacing={2} mb={3}>
        <LocalHospital color="error" sx={{ fontSize: 36 }} />
        <Box flex={1}>
          <Typography variant="h5" fontWeight={700}>
            Guardia cardiológica
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Guardá la atención abierta para seguir cargando pedidos. Derivar a internación no
            requiere cerrarla: los análisis y estudios pendientes se siguen marcando en esta lista.
          </Typography>
        </Box>
        {canOperate && (
          <Button
            variant="contained"
            color="error"
            startIcon={<Add />}
            onClick={() => openDialog('create')}
          >
            Nueva atención
          </Button>
        )}
        <IconButton onClick={() => refetch()} disabled={isFetching}>
          <Refresh />
        </IconButton>
      </Stack>

      <Card>
        <CardContent>
          {isLoading ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Fecha</TableCell>
                  <TableCell>Paciente</TableCell>
                  <TableCell>Médico</TableCell>
                  <TableCell>Motivo</TableCell>
                  <TableCell>Estado</TableCell>
                  <TableCell>Pedidos</TableCell>
                  <TableCell align="right">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {atenciones.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography variant="body2" color="text.secondary" py={2}>
                        No hay atenciones de guardia registradas.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  atenciones.map((atencion: Atencion) => {
                    const labPend = atencion.pedidos_lab_pendientes ?? 0;
                    const estPend = atencion.pedidos_estudios_pendientes ?? 0;
                    const sinPendientes = labPend === 0 && estPend === 0;
                    return (
                      <TableRow key={atencion.id} hover>
                        <TableCell>{formatDateTime(atencion.fecha_admision)}</TableCell>
                        <TableCell>
                          {atencion.paciente
                            ? `${atencion.paciente.apellido}, ${atencion.paciente.nombre}`
                            : '—'}
                        </TableCell>
                        <TableCell>
                          {atencion.medico_principal
                            ? `Dr. ${atencion.medico_principal.apellido}, ${atencion.medico_principal.nombre}`
                            : '—'}
                        </TableCell>
                        <TableCell sx={{ maxWidth: 220 }}>
                          <Typography
                            variant="body2"
                            noWrap
                            title={atencion.observaciones_generales ?? ''}
                          >
                            {atencion.observaciones_generales || '—'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                            <Chip
                              label={atencion.estado_clinico || 'ABIERTA'}
                              size="small"
                              color={
                                atencion.estado_clinico === 'FINALIZADA' ? 'success' : 'warning'
                              }
                            />
                            {atencion.derivada_a_internacion || atencion.internacion_id ? (
                              <Chip label="Derivada" size="small" variant="outlined" color="info" />
                            ) : null}
                          </Stack>
                        </TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                            {labPend > 0 && (
                              <Chip
                                size="small"
                                color="warning"
                                variant="outlined"
                                label={`Lab: ${labPend}`}
                              />
                            )}
                            {estPend > 0 && (
                              <Chip
                                size="small"
                                color="warning"
                                variant="outlined"
                                label={`Estudios: ${estPend}`}
                              />
                            )}
                            {sinPendientes && (
                              <Chip
                                size="small"
                                color="success"
                                variant="outlined"
                                label="Pedidos OK"
                              />
                            )}
                          </Stack>
                        </TableCell>
                        <TableCell align="right">
                          <Tooltip title="Ver detalle">
                            <IconButton size="small" onClick={() => openDialog('view', atencion.id)}>
                              <Visibility fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          {canOperate && atencion.estado_clinico === 'ABIERTA' && (
                            <Tooltip title="Continuar atención">
                              <IconButton
                                size="small"
                                onClick={() => openDialog('edit', atencion.id)}
                              >
                                <Edit fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                          {canOperate && atencion.estado_clinico === 'ABIERTA' && (
                            <Tooltip title="Cerrar atención">
                              <span>
                                <IconButton
                                  size="small"
                                  disabled={closingId === atencion.id}
                                  onClick={() => void cerrarAtencion(atencion)}
                                >
                                  {closingId === atencion.id ? (
                                    <CircularProgress size={16} />
                                  ) : (
                                    <CheckCircleOutline fontSize="small" />
                                  )}
                                </IconButton>
                              </span>
                            </Tooltip>
                          )}
                          {canOperate &&
                            !atencion.internacion_id &&
                            !atencion.derivada_a_internacion && (
                            <Tooltip title="Derivar a internación">
                              <IconButton size="small" onClick={() => derivarInternacion(atencion)}>
                                <TransferWithinAStation fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <GuardiaAtencionDialog
        open={dialogOpen}
        mode={dialogMode}
        atencionId={dialogAtencionId}
        onClose={() => setDialogOpen(false)}
        onSaved={() => {
          void refetch();
        }}
      />
    </Box>
  );
};

export default GuardiaPage;
