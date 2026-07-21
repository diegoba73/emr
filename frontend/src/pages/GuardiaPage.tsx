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
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useData } from '../contexts/DataContext';
import { AtencionFilters, useAtencionesQuery } from '../modules/atenciones/hooks';
import { Atencion } from '../types';
import GuardiaAtencionDialog, {
  GuardiaDialogMode,
} from '../modules/guardia/components/GuardiaAtencionDialog';
import { canOperateAtenciones } from '../utils/permissions';

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

  return (
    <Box sx={{ p: 3 }}>
      <Stack direction="row" alignItems="center" spacing={2} mb={3}>
        <LocalHospital color="error" sx={{ fontSize: 36 }} />
        <Box flex={1}>
          <Typography variant="h5" fontWeight={700}>
            Guardia cardiológica
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Atención rápida: paciente, motivo y pedido de análisis o estudio en un solo formulario. Si el
            cuadro lo requiere, derivá a internación; si no, guardá y finalizá.
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
                  <TableCell align="right">Acciones</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {atenciones.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography variant="body2" color="text.secondary" py={2}>
                        No hay atenciones de guardia registradas.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  atenciones.map((atencion: Atencion) => (
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
                        <Typography variant="body2" noWrap title={atencion.observaciones_generales ?? ''}>
                          {atencion.observaciones_generales || '—'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={atencion.estado_clinico || 'ABIERTA'}
                          size="small"
                          color={atencion.estado_clinico === 'FINALIZADA' ? 'success' : 'warning'}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Ver detalle">
                          <IconButton size="small" onClick={() => openDialog('view', atencion.id)}>
                            <Visibility fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        {canOperate && atencion.estado_clinico === 'ABIERTA' && (
                          <Tooltip title="Continuar atención">
                            <IconButton size="small" onClick={() => openDialog('edit', atencion.id)}>
                              <Edit fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {canOperate &&
                          atencion.estado_clinico === 'FINALIZADA' &&
                          !atencion.internacion_id && (
                            <Tooltip title="Derivar a internación">
                              <IconButton size="small" onClick={() => derivarInternacion(atencion)}>
                                <TransferWithinAStation fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                      </TableCell>
                    </TableRow>
                  ))
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
