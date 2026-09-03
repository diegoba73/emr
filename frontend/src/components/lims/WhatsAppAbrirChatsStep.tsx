import React from 'react';
import { Alert, Button, Typography } from '@mui/material';

export type WhatsAppChatEnlace = {
  rol: string;
  telefono: string;
  enlace: string;
};

function etiquetaRol(rol: string): string {
  return rol === 'medico' ? 'médico solicitante' : 'paciente';
}

export interface WhatsAppAbrirChatsStepProps {
  enlaces: WhatsAppChatEnlace[];
  pdfDescargado: boolean;
}

/**
 * Paso posterior al envío: WhatsApp no sale solo (sin API de pago).
 * El clic del operador es gesto de usuario, así el navegador no bloquea el chat.
 */
const WhatsAppAbrirChatsStep: React.FC<WhatsAppAbrirChatsStepProps> = ({
  enlaces,
  pdfDescargado,
}) => {
  return (
    <>
      <Alert severity="info" sx={{ mb: 2 }}>
        WhatsApp no se envía solo. Abrí el chat y pulsá <strong>Enviar</strong>.
        {pdfDescargado
          ? ' El PDF ya se descargó: adjuntarlo es lo que funciona en esta PC (localhost no es un link tocable).'
          : ''}
      </Alert>
      {enlaces.map((item) => (
        <Button
          key={`${item.rol}-${item.telefono}`}
          variant="contained"
          color="success"
          fullWidth
          sx={{ mb: 1 }}
          onClick={() => window.open(item.enlace, '_blank', 'noopener,noreferrer')}
        >
          Abrir WhatsApp del {etiquetaRol(item.rol)} ({item.telefono})
        </Button>
      ))}
      <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
        Si WhatsApp Web no está iniciado, iniciá sesión y volvé a pulsar el botón.
      </Typography>
    </>
  );
};

export default WhatsAppAbrirChatsStep;
