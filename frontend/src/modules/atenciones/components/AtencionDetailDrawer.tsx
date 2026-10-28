import React, { useMemo, useState, useEffect } from 'react';
import {
  Drawer,
  Box,
  IconButton,
  Typography,
  Divider,
  GridLegacy as Grid,
  Chip,
  Stack,
  Tabs,
  Tab,
  CircularProgress,
  Button,
} from '@mui/material';
import { Close, LocalHospital, AssignmentTurnedIn, TransferWithinAStation } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Atencion, User } from '../../../types';
import { useAtencionQuery } from '../hooks';
import ConsultaAmbulatoriaForm from './forms/ConsultaAmbulatoriaForm';
import EvolucionInternacionForm from './forms/EvolucionInternacionForm';
import AtencionPedidosSection from './AtencionPedidosSection';
import EstudioDiagnosticoForm from './forms/EstudioDiagnosticoForm';
import ProcedimientoForm from './forms/ProcedimientoForm';
import CirugiaForm from './forms/CirugiaForm';
import { useData } from '../../../contexts/DataContext';
import { canOperateAtenciones } from '../../../utils/permissions';
import { Z_CLINICAL_DRAWER } from '../../../utils/layerZIndex';

interface AtencionDetailDrawerProps {
  atencionId: number | null;
  open: boolean;
  onClose: () => void;
  currentUserRole?: string;
  currentUser?: User | null;
  canOperate?: boolean;
  onIntervencionSaved?: () => void | Promise<void>;
  forceEdit?: boolean;
  /** Pestaña inicial al abrir (guardia → pedidos clínicos). */
  initialTab?: 'pedidos' | 'detalle' | 'resumen';
}

const AtencionDetailDrawer: React.FC<AtencionDetailDrawerProps> = ({
  atencionId,
  open,
  onClose,
  currentUserRole: _currentUserRole,
  currentUser: currentUserProp,
  canOperate: canOperateProp,
  onIntervencionSaved,
  forceEdit = false,
  initialTab = 'resumen',
}) => {
  const { currentUser: currentUserFromContext } = useData();
  const effectiveUser = currentUserProp ?? currentUserFromContext ?? null;

  const queryResult = useAtencionQuery(atencionId ?? undefined);
  const { data, isLoading, error } = queryResult;
  const isError = queryResult.isError ?? (error !== undefined && error !== null);
  
  // ELIMINADO: Refetch automático - React Query maneja el cache automáticamente
  // El backend ahora siempre devuelve IDs explícitos y relaciones completas
  // No necesitamos refetches defensivos que causan loops infinitos
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [tabValue, setTabValue] = useState(0);
  
  // Escuchar cambios en la atención para invalidar turnos cuando se guarda un registro
  const prevRegistroIds = React.useRef<{
    consulta?: number;
    procedimiento?: number;
    quirurgico?: number;
  }>({});
  
  useEffect(() => {
    if (!data) return;
    
    const currentIds = {
      consulta: data.consulta_ambulatoria?.id,
      procedimiento: data.registro_procedimiento?.id,
      quirurgico: data.registro_quirurgico?.id,
    };
    
    // Solo ejecutar si hay un cambio en los IDs de los registros
    const hasChanged = 
      prevRegistroIds.current.consulta !== currentIds.consulta ||
      prevRegistroIds.current.procedimiento !== currentIds.procedimiento ||
      prevRegistroIds.current.quirurgico !== currentIds.quirurgico;
    
    if (hasChanged && (currentIds.consulta || currentIds.procedimiento || currentIds.quirurgico)) {
      // Si la atención tiene un registro, invalidar turnos para que se recarguen
      queryClient.invalidateQueries({ queryKey: ['turnos'] });
      // También llamar al callback si está disponible para recargar turnos en DataContext
      if (onIntervencionSaved) {
        onIntervencionSaved();
      }
      // Actualizar la referencia
      prevRegistroIds.current = currentIds;
    }
  }, [data?.consulta_ambulatoria?.id, data?.registro_procedimiento?.id, data?.registro_quirurgico?.id, queryClient, onIntervencionSaved, data]);

  const canEdit = useMemo(() => {
    if (canOperateProp !== undefined) {
      return canOperateProp;
    }
    return canOperateAtenciones(effectiveUser);
  }, [canOperateProp, effectiveUser]);

  const atencionAbierta = data?.estado_clinico === 'ABIERTA' && !data?.fecha_cierre;
  const canEditClinical = canEdit && Boolean(atencionAbierta);

  const isInternacion = useMemo(
    () => data?.contexto_atencion === 'INTERNACION' || Boolean(data?.evolucion_internacion),
    [data?.contexto_atencion, data?.evolucion_internacion],
  );

  const isGuardia = useMemo(
    () => data?.contexto_atencion === 'GUARDIA',
    [data?.contexto_atencion],
  );

  // Solo internación usa solapas del drawer (evolución + pedidos).
  // CONSULTA: el formulario trae Detalle clínico | Pedidos y resultados.
  const showDrawerTabs = isInternacion;

  useEffect(() => {
    if (!open) return;
    // Internación: 0 = evolución, 1 = pedidos
    if (showDrawerTabs && initialTab === 'pedidos') {
      setTabValue(1);
      return;
    }
    setTabValue(0);
  }, [atencionId, open, initialTab, showDrawerTabs]);

  const showTabPanel = (index: number) => ({
    display: tabValue === index ? 'block' : 'none',
  });

  // Callback para cerrar el drawer después de guardar exitosamente
  const handleSaveSuccess = async () => {
    // Esperar un momento para que el usuario vea el toast de éxito
    setTimeout(async () => {
      // Llamar al callback para refrescar turnos antes de cerrar
      if (onIntervencionSaved) {
        await onIntervencionSaved();
      }
      onClose();
    }, 1500);
  };

  const renderDetalle = (atencion: Atencion) => {
    if (atencion.contexto_atencion === 'INTERNACION' || atencion.evolucion_internacion) {
      return (
        <EvolucionInternacionForm
          key={`evolucion-${atencion.id}-${forceEdit ? 'edit' : 'view'}`}
          atencionId={atencion.id}
          canEdit={canEditClinical}
          onSaveSuccess={handleSaveSuccess}
        />
      );
    }
    switch (atencion.tipo_intervencion) {
      case 'CONSULTA':
        return (
          <ConsultaAmbulatoriaForm
            key={`consulta-${atencion.id}-${forceEdit ? 'edit' : 'view'}`}
            atencionId={atencion.id}
            canEdit={canEditClinical}
            forceEdit={forceEdit}
            initialTab={initialTab === 'pedidos' ? 'pedidos' : 'detalle'}
            onSaveSuccess={handleSaveSuccess}
          />
        );
      case 'ESTUDIO':
        return (
          <EstudioDiagnosticoForm
            atencionId={atencion.id}
            registro={atencion.registro_procedimiento || undefined}
            canEdit={canEditClinical}
            onSaveSuccess={handleSaveSuccess}
          />
        );
      case 'PROCEDIMIENTO':
        return (
          <ProcedimientoForm
            atencionId={atencion.id}
            registro={atencion.registro_procedimiento || undefined}
            canEdit={canEditClinical}
            onSaveSuccess={handleSaveSuccess}
          />
        );
      case 'CIRUGIA':
        const registroQuirurgico = atencion.registro_quirurgico || undefined;
        return (
          <CirugiaForm
            key={`cirugia-${atencion.id}-${atencion.registro_quirurgico?.id || 'new'}`}
            atencionId={atencion.id}
            registro={registroQuirurgico}
            canEdit={canEditClinical}
            onSaveSuccess={handleSaveSuccess}
          />
        );
      default:
        return (
          <Typography variant="body2" color="text.secondary">
            No hay un formulario específico para este tipo de intervención.
          </Typography>
        );
    }
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      PaperProps={{
        sx: { 
          width: { xs: '100%', md: 640 },
          zIndex: Z_CLINICAL_DRAWER,
        },
      }}
      ModalProps={{
        style: { zIndex: Z_CLINICAL_DRAWER },
        disableEnforceFocus: true,
      }}
    >
      <Box display="flex" alignItems="center" justifyContent="space-between" px={2} py={1}>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <LocalHospital color="primary" />
          <Typography variant="h6" fontWeight={700}>
            {isInternacion ? 'Atención de internación' : 'Detalle de la Atención'}
          </Typography>
        </Stack>
        <IconButton onClick={onClose}>
          <Close />
        </IconButton>
      </Box>
      <Divider />

      {isLoading ? (
        <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" py={6}>
          <CircularProgress />
          <Typography variant="body2" color="text.secondary" mt={2}>
            Cargando atención...
          </Typography>
        </Box>
      ) : isError || !data ? (
        <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" py={6} px={2}>
          <Typography variant="h6" color="error" gutterBottom>
            {isError ? 'Error al cargar la atención' : 'Atención no encontrada'}
          </Typography>
          <Typography variant="body2" color="text.secondary" textAlign="center" mb={2}>
            {error?.message || 'No se pudo cargar la información de la atención. Por favor, intenta nuevamente.'}
          </Typography>
          <Button variant="outlined" onClick={onClose}>
            Cerrar
          </Button>
        </Box>
      ) : (data as any).error ? (
        <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" py={6} px={2}>
          <Typography variant="h6" color="error" gutterBottom>
            Error en los datos
          </Typography>
          <Typography variant="body2" color="text.secondary" textAlign="center" mb={2}>
            {(data as any).error || 'Error al cargar los datos de la atención'}
          </Typography>
          <Button variant="outlined" onClick={onClose}>
            Cerrar
          </Button>
        </Box>
      ) : (!data.paciente || (typeof data.paciente === 'object' && !data.paciente.id && !data.paciente.nombre)) && 
          (!data.medico_principal || (typeof data.medico_principal === 'object' && !data.medico_principal.id && !data.medico_principal.nombre)) ? (
        <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" py={6} px={2}>
          <Typography variant="h6" color="error" gutterBottom>
            Datos incompletos
          </Typography>
          <Typography variant="body2" color="text.secondary" textAlign="center" mb={2}>
            La atención no tiene todos los datos necesarios. Por favor, verifica que el turno tenga paciente y médico asignados.
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
            ID Atención: {data.id}
            {data.paciente 
              ? ` | Paciente: ${typeof data.paciente === 'object' ? (data.paciente.id || 'Sin ID') : data.paciente}` 
              : ' | Paciente: No disponible'}
            {data.medico_principal 
              ? ` | Médico: ${typeof data.medico_principal === 'object' ? (data.medico_principal.id || 'Sin ID') : data.medico_principal}` 
              : ' | Médico: No disponible'}
          </Typography>
          <Button variant="outlined" onClick={onClose} sx={{ mt: 2 }}>
            Cerrar
          </Button>
        </Box>
      ) : (
        <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
          <Stack direction="row" spacing={1} mb={2} alignItems="center" flexWrap="wrap" useFlexGap>
            <Chip
              label={data.contexto_atencion_display || data.contexto_atencion || 'Ambulatoria'}
              color={
                data.contexto_atencion === 'INTERNACION'
                  ? 'warning'
                  : data.contexto_atencion === 'GUARDIA'
                    ? 'error'
                    : 'info'
              }
              size="small"
            />
            {data.tipo_intervencion && data.tipo_intervencion !== 'CONSULTA' && (
              <Chip
                label={
                  data.tipo_intervencion === 'ESTUDIO'
                    ? 'Estudio'
                    : data.tipo_intervencion === 'PROCEDIMIENTO'
                      ? 'Procedimiento'
                      : data.tipo_intervencion === 'CIRUGIA'
                        ? 'Cirugía'
                        : data.tipo_intervencion
                }
                color="primary"
                size="small"
                variant="outlined"
              />
            )}
            <Chip
              label={data.estado_clinico || 'N/A'}
              color={data.estado_clinico === 'FINALIZADA' ? 'success' : data.estado_clinico === 'EN_REVISION' ? 'warning' : 'info'}
              size="small"
              variant="outlined"
            />
            {!!data.fecha_cierre && (
              <Chip
                icon={<AssignmentTurnedIn fontSize="small" />}
                label="Cerrada"
                size="small"
                color="success"
                variant="outlined"
              />
            )}
            {isGuardia && data.paciente?.id && (
              <Button
                size="small"
                variant="outlined"
                color="warning"
                startIcon={<TransferWithinAStation />}
                onClick={() => {
                  navigate('/internacion', {
                    state: {
                      derivarDesdeAtencionId: data.id,
                      pacienteId: data.paciente.id,
                      motivoIngreso:
                        data.consulta_ambulatoria?.diagnostico_presuntivo ||
                        data.observaciones_generales ||
                        '',
                    },
                  });
                }}
                sx={{ ml: 'auto' }}
              >
                Derivar a internación
              </Button>
            )}
          </Stack>

          <Grid container spacing={1} mb={2}>
            <Grid item xs={12}>
              <Typography variant="subtitle2" color="text.secondary">
                Paciente
              </Typography>
              <Typography variant="body1" fontWeight={600}>
                {(() => {
                  // Validar que paciente exista y tenga datos
                  if (!data.paciente) return 'Paciente no disponible';
                  // Si es un objeto con datos
                  if (typeof data.paciente === 'object') {
                    const apellido = data.paciente.apellido || '';
                    const nombre = data.paciente.nombre || '';
                    const dni = data.paciente.dni || 'N/A';
                    const nombreCompleto = `${apellido}, ${nombre}`.trim();
                    return nombreCompleto ? `${nombreCompleto} — DNI ${dni}` : `Paciente ID: ${data.paciente.id || 'N/A'}`;
                  }
                  // Si es solo un ID
                  return `Paciente ID: ${data.paciente}`;
                })()}
              </Typography>
            </Grid>
            <Grid item xs={12}>
              <Typography variant="subtitle2" color="text.secondary">
                Médico/a principal
              </Typography>
              <Typography variant="body1">
                {(() => {
                  // Validar que medico_principal exista y tenga datos
                  if (!data.medico_principal) return 'Médico no disponible';
                  // Si es un objeto con datos
                  if (typeof data.medico_principal === 'object') {
                    const apellido = data.medico_principal.apellido || '';
                    const nombre = data.medico_principal.nombre || '';
                    const nombreCompleto = `${apellido}, ${nombre}`.trim();
                    return nombreCompleto ? `Dr. ${nombreCompleto}` : `Médico ID: ${data.medico_principal.id || 'N/A'}`;
                  }
                  // Si es solo un ID
                  return `Médico ID: ${data.medico_principal}`;
                })()}
              </Typography>
            </Grid>
            <Grid item xs={12}>
              <Typography variant="subtitle2" color="text.secondary">
                Fechas
              </Typography>
              <Typography variant="body2">
                Ingreso: {new Date(data.fecha_admision).toLocaleString()}
              </Typography>
              <Typography variant="body2">
                Cierre: {data.fecha_cierre ? new Date(data.fecha_cierre).toLocaleString() : '—'}
              </Typography>
            </Grid>
            {data.observaciones_generales && (
              <Grid item xs={12}>
                <Typography variant="subtitle2" color="text.secondary">
                  Observaciones generales
                </Typography>
                <Typography variant="body2">{data.observaciones_generales}</Typography>
              </Grid>
            )}
          </Grid>

          {showDrawerTabs ? (
            <>
              <Tabs
                value={tabValue}
                onChange={(_event, newValue) => setTabValue(newValue)}
                variant="scrollable"
                scrollButtons="auto"
                sx={{ mb: 2 }}
              >
                <Tab label="Detalle clínico" />
                <Tab label="Pedidos y resultados" />
              </Tabs>
              <Box sx={{ flexGrow: 1, overflowY: 'auto', pr: 1 }}>
                <Box sx={showTabPanel(0)}>{renderDetalle(data)}</Box>
                <Box sx={showTabPanel(1)}>
                  {data.id && (
                    <AtencionPedidosSection
                      atencionId={data.id}
                      canEdit={canEditClinical}
                      variant="full"
                      pacienteId={data.paciente?.id}
                    />
                  )}
                </Box>
              </Box>
            </>
          ) : (
            <Box sx={{ flexGrow: 1, overflowY: 'auto', pr: 1 }}>
              {renderDetalle(data)}
            </Box>
          )}
        </Box>
      )}
    </Drawer>
  );
};

export default AtencionDetailDrawer;

