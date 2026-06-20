import React from 'react';
import {
  Paper,
  Typography,
  Box,
  Chip,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Hotel as BedIcon,
  Person as PersonIcon,
  LocalHospital as HospitalIcon,
  CleaningServices as CleaningIcon,
  Build as MaintenanceIcon,
  Shield as ShieldIcon,
} from '@mui/icons-material';
import { Cama } from '../../types';

interface BedCardProps {
  cama: Cama;
  onClick: () => void;
  onDragStart?: (e: React.DragEvent, cama: Cama) => void;
  onDragOver?: (e: React.DragEvent, cama: Cama) => void;
  onDrop?: (e: React.DragEvent, cama: Cama) => void;
  onDragEnd?: () => void;
  isDragging?: boolean;
  isDragOver?: boolean;
}

const BedCard: React.FC<BedCardProps> = ({ 
  cama, 
  onClick, 
  onDragStart, 
  onDragOver, 
  onDrop,
  onDragEnd,
  isDragging = false,
  isDragOver = false,
}) => {
  const getStatusStyles = () => {
    switch (cama.estado) {
      case 'DISPONIBLE':
        return {
          border: '2px solid #4caf50',
          backgroundColor: '#e8f5e9',
          color: '#2e7d32',
        };
      case 'OCUPADA':
        return {
          border: '2px solid #f44336',
          backgroundColor: '#ffffff',
          color: '#c62828',
        };
      case 'LIMPIEZA':
        return {
          border: '2px solid #ff9800',
          backgroundColor: '#fff3e0',
          color: '#e65100',
        };
      case 'MANTENIMIENTO':
        return {
          border: '2px solid #9e9e9e',
          backgroundColor: '#f5f5f5',
          color: '#616161',
        };
      default:
        return {
          border: '1px solid #e0e0e0',
          backgroundColor: '#ffffff',
          color: '#000000',
        };
    }
  };

  const getStatusIcon = () => {
    switch (cama.estado) {
      case 'DISPONIBLE':
        return <BedIcon sx={{ fontSize: 40, color: '#4caf50' }} />;
      case 'OCUPADA':
        return <PersonIcon sx={{ fontSize: 40, color: '#f44336' }} />;
      case 'LIMPIEZA':
        return <CleaningIcon sx={{ fontSize: 40, color: '#ff9800' }} />;
      case 'MANTENIMIENTO':
        return <MaintenanceIcon sx={{ fontSize: 40, color: '#9e9e9e' }} />;
      default:
        return <BedIcon sx={{ fontSize: 40 }} />;
    }
  };

  const styles = getStatusStyles();
  const internacion = cama.internacion_actual;

  const handleDragStart = (e: React.DragEvent) => {
    if (cama.estado === 'OCUPADA' && onDragStart) {
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', cama.id.toString());
      onDragStart(e, cama);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    if (onDragOver && (cama.estado === 'DISPONIBLE' || cama.estado === 'OCUPADA')) {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      onDragOver(e, cama);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    if (onDrop && (cama.estado === 'DISPONIBLE' || cama.estado === 'OCUPADA')) {
      e.preventDefault();
      onDrop(e, cama);
    }
  };

  const handleDragEndLocal = () => {
    if (onDragEnd) {
      onDragEnd();
    }
  };

  return (
    <Paper
      elevation={isDragging ? 8 : isDragOver ? 6 : 2}
      sx={{
        p: 2,
        height: '100%',
        cursor: cama.estado === 'OCUPADA' ? 'grab' : 'pointer',
        transition: 'all 0.3s ease',
        ...styles,
        opacity: isDragging ? 0.5 : 1,
        transform: isDragOver ? 'scale(1.05)' : isDragging ? 'scale(0.95)' : 'none',
        border: isDragOver ? '3px dashed #2196f3' : styles.border,
        '&:hover': {
          transform: isDragging || isDragOver ? 'none' : 'translateY(-4px)',
          boxShadow: 4,
        },
      }}
      onClick={onClick}
      draggable={cama.estado === 'OCUPADA'}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onDragEnd={handleDragEndLocal}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Header con nombre de cama */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {cama.nombre}
            </Typography>
            {cama.aislada && (
              <Tooltip title="Cama Aislada">
                <ShieldIcon sx={{ fontSize: 18, color: '#ff9800' }} />
              </Tooltip>
            )}
          </Box>
          {getStatusIcon()}
        </Box>

        {/* Estado */}
        <Chip
          label={cama.estado}
          size="small"
          sx={{
            mb: 1,
            backgroundColor: styles.backgroundColor,
            border: `1px solid ${styles.border.split(' ')[2]}`,
            fontWeight: 600,
          }}
        />

        {/* Información de internación si está ocupada */}
        {cama.estado === 'OCUPADA' && internacion && (
          <Box sx={{ mt: 1, flexGrow: 1 }}>
            <Typography
              variant="subtitle1"
              sx={{
                fontWeight: 700,
                mb: 0.5,
                color: '#c62828',
              }}
            >
              {internacion.nombre_paciente}
            </Typography>
            {internacion.nombre_medico && (
              <Typography variant="body2" sx={{ mb: 0.5, color: '#666' }}>
                <HospitalIcon sx={{ fontSize: 14, verticalAlign: 'middle', mr: 0.5 }} />
                {internacion.nombre_medico}
              </Typography>
            )}
            <Typography
              variant="body2"
              sx={{
                mb: 1,
                color: '#666',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
              }}
            >
              {internacion.diagnostico}
            </Typography>
            <Chip
              label={`${internacion.dias_internacion} días`}
              size="small"
              color="primary"
              sx={{ fontWeight: 600 }}
            />
          </Box>
        )}

        {/* Mensaje para camas disponibles */}
        {cama.estado === 'DISPONIBLE' && (
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Typography variant="body2" sx={{ color: '#4caf50', fontStyle: 'italic' }}>
              Cama disponible
            </Typography>
          </Box>
        )}

        {/* Mensaje para limpieza/mantenimiento */}
        {(cama.estado === 'LIMPIEZA' || cama.estado === 'MANTENIMIENTO') && (
          <Box sx={{ mt: 2, textAlign: 'center' }}>
            <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
              {cama.estado === 'LIMPIEZA' ? 'En limpieza' : 'En mantenimiento'}
            </Typography>
          </Box>
        )}
      </Box>
    </Paper>
  );
};

export default BedCard;

