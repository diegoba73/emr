import React from 'react';
import { Box, ToggleButton, ToggleButtonGroup, Typography } from '@mui/material';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import BiotechIcon from '@mui/icons-material/Biotech';

export type AgendaTipo = 'consulta' | 'estudio';

export interface AgendaTipoSelectorProps {
  value: AgendaTipo;
  onChange: (value: AgendaTipo) => void;
  showEstudio: boolean;
  disabled?: boolean;
}

const AgendaTipoSelector: React.FC<AgendaTipoSelectorProps> = ({
  value,
  onChange,
  showEstudio,
  disabled = false,
}) => {
  if (!showEstudio) return null;

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        ¿Qué tipo de turno querés agendar?
      </Typography>
      <ToggleButtonGroup
        exclusive
        fullWidth
        value={value}
        disabled={disabled}
        onChange={(_, next) => {
          if (next) onChange(next as AgendaTipo);
        }}
        sx={{
          '& .MuiToggleButton-root': {
            py: 1.25,
            px: 1.5,
            textAlign: 'left',
            justifyContent: 'flex-start',
            gap: 1,
          },
        }}
      >
        <ToggleButton value="consulta">
          <LocalHospitalIcon fontSize="small" color="primary" />
          <Box>
            <Typography variant="body2" fontWeight={700} display="block">
              Consulta médica
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Paciente + médico + consultorio
            </Typography>
          </Box>
        </ToggleButton>
        <ToggleButton value="estudio">
          <BiotechIcon fontSize="small" sx={{ color: '#0D9488' }} />
          <Box>
            <Typography variant="body2" fontWeight={700} display="block">
              Estudio complementario
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Estudio solicitado + sala (sin médico)
            </Typography>
          </Box>
        </ToggleButton>
      </ToggleButtonGroup>
    </Box>
  );
};

export default AgendaTipoSelector;
