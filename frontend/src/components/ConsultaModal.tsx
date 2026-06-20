import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  TextField,
  Button,
  Typography,
  IconButton,
  Alert,
  Card,
  CardContent,
  Divider,
} from '@mui/material';
import { Close } from '@mui/icons-material';
import { apiService } from '../services/api';
import { Turno, Consulta } from '../types';

interface ConsultaModalProps {
  open: boolean;
  onClose: () => void;
  turno: Turno | null;
  onSuccess?: () => void;
  consultaExistente?: Consulta | null;
}

interface ConsultaFormData {
  anamnesis: string;
  examen_fisico: string;
  diagnostico_presuntivo: string;
  plan_manejo: string;
  notas_medicas: string;
}

const ConsultaModal: React.FC<ConsultaModalProps> = ({
  open,
  onClose,
  turno,
  onSuccess,
  consultaExistente,
}) => {
  const [formData, setFormData] = useState<ConsultaFormData>({
    anamnesis: '',
    examen_fisico: '',
    diagnostico_presuntivo: '',
    plan_manejo: '',
    notas_medicas: '',
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isEditMode, setIsEditMode] = useState(false);

  // Cargar datos de consulta existente si existe
  useEffect(() => {
    if (open && consultaExistente) {
      setIsEditMode(true);
      setFormData({
        anamnesis: consultaExistente.anamnesis || '',
        examen_fisico: consultaExistente.examen_fisico || '',
        diagnostico_presuntivo: consultaExistente.diagnostico_presuntivo || '',
        plan_manejo: consultaExistente.plan_manejo || '',
        notas_medicas: consultaExistente.notas_medicas || '',
      });
    } else if (open && turno) {
      // Verificar si el turno ya tiene consulta
      const checkConsultaExistente = async () => {
        const consulta = await apiService.getConsultaInfo(turno.id);
        if (consulta) {
          setIsEditMode(true);
          setFormData({
            anamnesis: consulta.anamnesis || '',
            examen_fisico: consulta.examen_fisico || '',
            diagnostico_presuntivo: consulta.diagnostico_presuntivo || '',
            plan_manejo: consulta.plan_manejo || '',
            notas_medicas: consulta.notas_medicas || '',
          });
        } else {
          // No hay consulta existente, modo creación
          setIsEditMode(false);
          setFormData({
            anamnesis: '',
            examen_fisico: '',
            diagnostico_presuntivo: '',
            plan_manejo: '',
            notas_medicas: '',
          });
        }
      };
      checkConsultaExistente();
    }
  }, [open, turno, consultaExistente]);

  const handleClose = () => {
    setError(null);
    setFormData({
      anamnesis: '',
      examen_fisico: '',
      diagnostico_presuntivo: '',
      plan_manejo: '',
      notas_medicas: '',
    });
    setIsEditMode(false);
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!turno) return;

    setError(null);
    setLoading(true);

    try {
      if (isEditMode && consultaExistente) {
        // TODO: Implementar actualización de consulta cuando esté disponible
        console.log('Edición de consulta - pendiente de implementar');
        setError('La edición de consultas aún no está implementada');
      } else {
        // Crear nueva consulta
        await apiService.crearConsulta(turno.id, formData);
        
        if (onSuccess) {
          onSuccess();
        }
        handleClose();
      }
    } catch (error: any) {
      console.error('Error al guardar consulta:', error);
      setError(error.message || 'Error al guardar la consulta. Por favor, intenta nuevamente.');
    } finally {
      setLoading(false);
    }
  };

  if (!turno) return null;

  return (
    <Dialog 
      open={open} 
      onClose={handleClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
          boxShadow: 3,
        }
      }}
    >
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pb: 2 }}>
        <Typography variant="h6" component="div">
          {isEditMode ? '📋 Editar Consulta' : '📋 Nueva Consulta'}
        </Typography>
        <IconButton onClick={handleClose} size="small">
          <Close />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        {/* Información del Turno */}
        <Card sx={{ mb: 3, bgcolor: 'grey.50' }}>
          <CardContent>
            <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold', mb: 2 }}>
              📅 Información del Turno
            </Typography>
            <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 2 }}>
              <Box>
                <Typography variant="caption" color="text.secondary">👤 Paciente</Typography>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {turno.paciente?.nombre} {turno.paciente?.apellido}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">👨‍⚕️ Médico</Typography>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {turno.medico?.nombre} {turno.medico?.apellido}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">📅 Fecha</Typography>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {new Date(turno.fecha_hora_inicio).toLocaleDateString('es-ES', {
                    weekday: 'long',
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric'
                  })}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">🕐 Hora</Typography>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {new Date(turno.fecha_hora_inicio).toLocaleTimeString('es-ES', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </Typography>
              </Box>
              {turno.motivo_consulta && (
                <Box sx={{ gridColumn: '1 / -1' }}>
                  <Typography variant="caption" color="text.secondary">📝 Motivo</Typography>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {turno.motivo_consulta}
                  </Typography>
                </Box>
              )}
            </Box>
          </CardContent>
        </Card>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        <Box component="form" onSubmit={handleSubmit} id="consulta-form">
          <TextField
            fullWidth
            multiline
            rows={4}
            label="📝 Anamnesis (Interrogatorio)"
            value={formData.anamnesis}
            onChange={(e) => setFormData({...formData, anamnesis: e.target.value})}
            placeholder="Describa el interrogatorio realizado al paciente..."
            required
            sx={{ mb: 2 }}
            variant="outlined"
          />

          <TextField
            fullWidth
            multiline
            rows={4}
            label="🔍 Examen Físico"
            value={formData.examen_fisico}
            onChange={(e) => setFormData({...formData, examen_fisico: e.target.value})}
            placeholder="Describa los hallazgos del examen físico..."
            required
            sx={{ mb: 2 }}
            variant="outlined"
          />

          <TextField
            fullWidth
            multiline
            rows={3}
            label="🏥 Diagnóstico Presuntivo"
            value={formData.diagnostico_presuntivo}
            onChange={(e) => setFormData({...formData, diagnostico_presuntivo: e.target.value})}
            placeholder="Diagnóstico presuntivo o definitivo..."
            required
            sx={{ mb: 2 }}
            variant="outlined"
          />

          <TextField
            fullWidth
            multiline
            rows={4}
            label="💊 Plan de Manejo / Conducta"
            value={formData.plan_manejo}
            onChange={(e) => setFormData({...formData, plan_manejo: e.target.value})}
            placeholder="Tratamiento, medicamentos, estudios solicitados, etc..."
            required
            sx={{ mb: 2 }}
            variant="outlined"
          />

          <TextField
            fullWidth
            multiline
            rows={3}
            label="📋 Notas Médicas Adicionales"
            value={formData.notas_medicas}
            onChange={(e) => setFormData({...formData, notas_medicas: e.target.value})}
            placeholder="Observaciones adicionales..."
            sx={{ mb: 2 }}
            variant="outlined"
          />
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button onClick={handleClose} disabled={loading}>
          Cancelar
        </Button>
        <Button
          type="submit"
          form="consulta-form"
          variant="contained"
          disabled={loading}
          sx={{ minWidth: 150 }}
        >
          {loading ? 'Guardando...' : isEditMode ? 'Actualizar Consulta' : 'Guardar Consulta'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ConsultaModal;

