import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  GridLegacy as Grid,
  CircularProgress,
  Alert,
  Paper,
  IconButton,
  Snackbar,
  Button,
} from '@mui/material';
import { Refresh as RefreshIcon, Settings as SettingsIcon } from '@mui/icons-material';
import { Cama } from '../types';
import { getCamas, moverPacienteCama } from '../services/apiService';
import { useData } from '../contexts/DataContext';
import BedCard from '../components/internacion/BedCard';
import ModalIngresarPaciente from '../components/internacion/ModalIngresarPaciente';
import ModalGestionarPaciente from '../components/internacion/ModalGestionarPaciente';
import ModalGestionarCama from '../components/internacion/ModalGestionarCama';
import ModalCrearCama from '../components/internacion/ModalCrearCama';

const InternacionDashboard: React.FC = () => {
  const { currentUser } = useData();
  const [camasUCO, setCamasUCO] = useState<Cama[]>([]);
  const [camasUCE, setCamasUCE] = useState<Cama[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedCama, setSelectedCama] = useState<Cama | null>(null);
  const [modalIngresarOpen, setModalIngresarOpen] = useState(false);
  const [modalGestionarOpen, setModalGestionarOpen] = useState(false);
  const [modalGestionarCamaOpen, setModalGestionarCamaOpen] = useState(false);
  const [modalCrearCamaOpen, setModalCrearCamaOpen] = useState(false);
  
  // Verificar si el usuario puede gestionar infraestructura
  const canManageInfra = ['admin', 'medico', 'enfermeria'].includes((currentUser?.rol || '').toLowerCase());
  
  // Estado para recordar qué cama se estaba editando (para restaurar scroll)
  const camaToScrollRef = useRef<number | null>(null);
  
  // Estados para drag and drop
  const [draggingCama, setDraggingCama] = useState<Cama | null>(null);
  const [dragOverCama, setDragOverCama] = useState<Cama | null>(null);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  const loadCamas = async (preserveScrollToCamaId?: number | null) => {
    setLoading(true);
    setError(null);
    try {
      const [camasUCOData, camasUCEData] = await Promise.all([
        getCamas('UCO'),
        getCamas('UCE'),
      ]);

      // Filter by sector name (backend should handle this, but filter client-side as fallback)
      const getSectorNombre = (cama: Cama): string => {
        if (typeof cama.sector === 'object') {
          return cama.sector.nombre;
        }
        return cama.sector_nombre || '';
      };
      const ucoCamas = camasUCOData.filter((c) => getSectorNombre(c) === 'UCO');
      const uceCamas = camasUCEData.filter((c) => getSectorNombre(c) === 'UCE');

      setCamasUCO(ucoCamas);
      setCamasUCE(uceCamas);
      
      // Si hay una cama a la que hacer scroll, guardarla para después
      if (preserveScrollToCamaId) {
        camaToScrollRef.current = preserveScrollToCamaId;
      }
    } catch (err: any) {
      setError('Error al cargar camas: ' + (err.message || 'Error desconocido'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCamas();
  }, []);

  // Efecto para hacer scroll a la cama después de que se carguen las camas
  useEffect(() => {
    if (!loading && camaToScrollRef.current) {
      // Esperar más tiempo para que el DOM se actualice completamente y el modal se cierre
      const timeoutId = setTimeout(() => {
        const camaElement = document.getElementById(`cama-${camaToScrollRef.current}`);
        if (camaElement) {
          // Usar scrollIntoView que es más confiable
          camaElement.scrollIntoView({
            behavior: 'smooth',
            block: 'center', // Centrar el elemento en la vista
          });
        } else {
          // Si no se encuentra el elemento, intentar con scrollTo como fallback
          // Esto puede pasar si el elemento aún no está en el DOM
          console.warn(`No se encontró el elemento cama-${camaToScrollRef.current}, intentando scroll manual`);
          // Intentar de nuevo después de un breve delay
          setTimeout(() => {
            const retryElement = document.getElementById(`cama-${camaToScrollRef.current}`);
            if (retryElement) {
              retryElement.scrollIntoView({
                behavior: 'smooth',
                block: 'center',
              });
            }
          }, 200);
        }
        // Limpiar la referencia después de hacer scroll
        camaToScrollRef.current = null;
      }, 300); // Aumentado a 300ms para dar tiempo a que el modal se cierre
      
      return () => clearTimeout(timeoutId);
    }
  }, [loading, camasUCO, camasUCE]);

  const handleCamaClick = (cama: Cama) => {
    setSelectedCama(cama);
    // Guardar el ID de la cama para restaurar scroll después
    camaToScrollRef.current = cama.id;
    if (cama.estado === 'DISPONIBLE') {
      setModalIngresarOpen(true);
    } else if (cama.estado === 'OCUPADA') {
      setModalGestionarOpen(true);
    } else if (cama.estado === 'LIMPIEZA' || cama.estado === 'MANTENIMIENTO') {
      setModalGestionarCamaOpen(true);
    }
  };

  const handleModalClose = () => {
    setModalIngresarOpen(false);
    setModalGestionarOpen(false);
    setModalGestionarCamaOpen(false);
    setSelectedCama(null);
  };

  const handleSuccess = () => {
    // Mantener el ID de la cama seleccionada para restaurar scroll
    const camaIdToScroll = selectedCama?.id || camaToScrollRef.current;
    loadCamas(camaIdToScroll);
  };

  const handleDragStart = (e: React.DragEvent, cama: Cama) => {
    if (cama.estado === 'OCUPADA' && cama.internacion_actual) {
      setDraggingCama(cama);
    }
  };

  const handleDragOver = (e: React.DragEvent, cama: Cama) => {
    if (draggingCama && draggingCama.id !== cama.id && 
        (cama.estado === 'DISPONIBLE' || cama.estado === 'OCUPADA')) {
      e.preventDefault();
      setDragOverCama(cama);
    }
  };

  const handleDragEnd = () => {
    setDraggingCama(null);
    setDragOverCama(null);
  };

  const handleDrop = async (e: React.DragEvent, camaDestino: Cama) => {
    e.preventDefault();
    
    if (!draggingCama || !draggingCama.internacion_actual) {
      setDragOverCama(null);
      return;
    }

    // No permitir mover a la misma cama
    if (draggingCama.id === camaDestino.id) {
      setDragOverCama(null);
      setDraggingCama(null);
      return;
    }

    // Solo permitir mover a camas disponibles u ocupadas
    if (camaDestino.estado !== 'DISPONIBLE' && camaDestino.estado !== 'OCUPADA') {
      setSnackbar({
        open: true,
        message: `No se puede mover a una cama en estado: ${camaDestino.estado}`,
        severity: 'error',
      });
      setDragOverCama(null);
      setDraggingCama(null);
      return;
    }

    const internacionId = draggingCama.internacion_actual.id_internacion;
    
    try {
      setLoading(true);
      const result = await moverPacienteCama(internacionId, camaDestino.id) as { message?: string; mensaje?: string };
      
      setSnackbar({
        open: true,
        message: result.message || result.mensaje || 'Paciente movido exitosamente',
        severity: 'success',
      });
      
      // Recargar camas para reflejar los cambios
      await loadCamas();
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || 
                      err.response?.data?.detail || 
                      'Error al mover paciente: ' + (err.message || 'Error desconocido');
      setSnackbar({
        open: true,
        message: errorMsg,
        severity: 'error',
      });
    } finally {
      setLoading(false);
      setDragOverCama(null);
      setDraggingCama(null);
    }
  };

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
        <Typography variant="h4" sx={{ fontWeight: 600 }}>
          Panel de Internación
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          {canManageInfra && (
            <Button
              variant="outlined"
              startIcon={<SettingsIcon />}
              onClick={() => setModalCrearCamaOpen(true)}
              sx={{ mr: 1 }}
            >
              Administrar Infraestructura
            </Button>
          )}
          <IconButton onClick={() => loadCamas()} color="primary">
            <RefreshIcon />
          </IconButton>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Sección UCO */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3, mb: 3 }}>
            <Typography variant="h5" sx={{ fontWeight: 600, mb: 2, color: 'primary.main' }}>
              Unidad Coronaria (UCO)
            </Typography>
            <Grid container spacing={2}>
              {camasUCO.length === 0 ? (
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">
                    No hay camas disponibles en UCO
                  </Typography>
                </Grid>
              ) : (
                camasUCO.map((cama) => (
                  <Grid item xs={12} sm={6} md={4} lg={3} key={cama.id}>
                    <Box id={`cama-${cama.id}`}>
                      <BedCard 
                        cama={cama} 
                        onClick={() => handleCamaClick(cama)}
                        onDragStart={handleDragStart}
                        onDragOver={handleDragOver}
                        onDrop={handleDrop}
                        onDragEnd={handleDragEnd}
                        isDragging={draggingCama?.id === cama.id}
                        isDragOver={dragOverCama?.id === cama.id}
                      />
                    </Box>
                  </Grid>
                ))
              )}
            </Grid>
          </Paper>
        </Grid>

        {/* Sección UCE */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h5" sx={{ fontWeight: 600, mb: 2, color: 'secondary.main' }}>
              Cuidados Especiales (UCE)
            </Typography>
            <Grid container spacing={2}>
              {camasUCE.length === 0 ? (
                <Grid item xs={12}>
                  <Typography variant="body2" color="text.secondary">
                    No hay camas disponibles en UCE
                  </Typography>
                </Grid>
              ) : (
                camasUCE.map((cama) => (
                  <Grid item xs={12} sm={6} md={4} lg={3} key={cama.id}>
                    <Box id={`cama-${cama.id}`}>
                      <BedCard 
                        cama={cama} 
                        onClick={() => handleCamaClick(cama)}
                        onDragStart={handleDragStart}
                        onDragOver={handleDragOver}
                        onDrop={handleDrop}
                        onDragEnd={handleDragEnd}
                        isDragging={draggingCama?.id === cama.id}
                        isDragOver={dragOverCama?.id === cama.id}
                      />
                    </Box>
                  </Grid>
                ))
              )}
            </Grid>
          </Paper>
        </Grid>
      </Grid>

      {/* Modales */}
      <ModalIngresarPaciente
        open={modalIngresarOpen}
        onClose={handleModalClose}
        cama={selectedCama}
        onSuccess={handleSuccess}
      />

      <ModalGestionarPaciente
        open={modalGestionarOpen}
        onClose={handleModalClose}
        cama={selectedCama}
        onSuccess={handleSuccess}
      />

      <ModalGestionarCama
        open={modalGestionarCamaOpen}
        onClose={handleModalClose}
        cama={selectedCama}
        onSuccess={handleSuccess}
      />
      
      <ModalCrearCama
        open={modalCrearCamaOpen}
        onClose={() => setModalCrearCamaOpen(false)}
        onSuccess={handleSuccess}
      />

      {/* Snackbar para notificaciones */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert 
          onClose={() => setSnackbar({ ...snackbar, open: false })} 
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default InternacionDashboard;

