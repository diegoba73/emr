import React from 'react';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Typography,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import BalanceHidricoSection from './BalanceHidricoSection';
import ControlesEnfermeriaSection from './ControlesEnfermeriaSection';
import NotaEnfermeriaSection from './NotaEnfermeriaSection';
import RegistroKinesiologiaSection from './RegistroKinesiologiaSection';

const accordionSx = {
  border: 1,
  borderColor: 'divider',
  borderRadius: 1,
  mb: 1.5,
  '&:before': { display: 'none' },
} as const;

interface RevistaHcDiarioAccordionsProps {
  internacionId: number;
  canWriteEnfermeria: boolean;
  canWriteKinesiologia: boolean;
  showEnfermeria: boolean;
  showKinesiologia: boolean;
}

const RevistaHcDiarioAccordions: React.FC<RevistaHcDiarioAccordionsProps> = ({
  internacionId,
  canWriteEnfermeria,
  canWriteKinesiologia,
  showEnfermeria,
  showKinesiologia,
}) => {
  if (!showEnfermeria && !showKinesiologia) {
    return null;
  }

  return (
    <Box sx={{ mb: 2 }}>
      {showEnfermeria && (
        <>
          <Accordion defaultExpanded disableGutters sx={accordionSx}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box>
                <Typography variant="subtitle2" fontWeight={700}>
                  Controles del turno
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Signos vitales y controles de enfermería por turno.
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <ControlesEnfermeriaSection
                internacionId={internacionId}
                canEdit={canWriteEnfermeria}
              />
            </AccordionDetails>
          </Accordion>

          <Accordion disableGutters sx={accordionSx}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box>
                <Typography variant="subtitle2" fontWeight={700}>
                  Balance hídrico
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Ingresos y egresos por turno.
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <BalanceHidricoSection
                internacionId={internacionId}
                canEdit={canWriteEnfermeria}
              />
            </AccordionDetails>
          </Accordion>

          <Accordion disableGutters sx={accordionSx}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box>
                <Typography variant="subtitle2" fontWeight={700}>
                  Nota de enfermería
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Observaciones, curaciones y dispositivos.
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <NotaEnfermeriaSection
                internacionId={internacionId}
                canEdit={canWriteEnfermeria}
              />
            </AccordionDetails>
          </Accordion>
        </>
      )}

      {showKinesiologia && (
        <Accordion defaultExpanded disableGutters sx={accordionSx}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box>
              <Typography variant="subtitle2" fontWeight={700}>
                Registro de kinesiología
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Sesión o intervención kinésica del día.
              </Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <RegistroKinesiologiaSection
              internacionId={internacionId}
              canEdit={canWriteKinesiologia}
            />
          </AccordionDetails>
        </Accordion>
      )}
    </Box>
  );
};

export default RevistaHcDiarioAccordions;
