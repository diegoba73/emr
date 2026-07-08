import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { SolicitudExamenLims } from '../../types/lims';
import { downloadInformeLimsPdf, postEnviarInformeOrden } from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import { countResultadosConValor } from '../../utils/limsOrdenResultados';

export interface EnviarInformeOrdenDialogProps {
  open: boolean;
  orden: SolicitudExamenLims;
  onClose: () => void;
  onSuccess: (orden: SolicitudExamenLims) => void;
}

const EnviarInformeOrdenDialog: React.FC<EnviarInformeOrdenDialogProps> = ({
  open,
  orden,
  onClose,
  onSuccess,
}) => {
  const [email, setEmail] = useState(true);
  const [whatsapp, setWhatsapp] = useState(true);
  const [sending, setSending] = useState(false);

  const tieneEmail = Boolean((orden.paciente_email || '').trim());
  const tieneTel = Boolean((orden.paciente_telefono || '').trim());
  const esInformeParcial = orden.estado === 'INFORMADO_PARCIAL';
  const progreso = countResultadosConValor(orden);

  useEffect(() => {
    if (!open) return;
    setEmail(tieneEmail);
    setWhatsapp(tieneTel);
  }, [open, tieneEmail, tieneTel]);

  const handleEnviar = async () => {
    if (!email && !whatsapp) {
      toast.error('Seleccioná al menos un canal de envío.');
      return;
    }
    setSending(true);
    try {
      const res = await postEnviarInformeOrden(orden.id, { email, whatsapp });
      const envio = res.envio;

      if (envio?.email_enviado) {
        const adj = envio.email_adjunto_pdf !== false;
        const tipo = esInformeParcial ? 'Informe parcial' : 'Informe';
        toast.success(
          adj
            ? `${tipo} enviado por correo a ${envio.email_destino || 'paciente'} con PDF adjunto.`
            : `${tipo} enviado por correo a ${envio.email_destino || 'paciente'}.`
        );
      }

      if (envio?.whatsapp_enviado) {
        if (envio.whatsapp_pdf_adjunto) {
          toast.success(
            esInformeParcial
              ? 'WhatsApp enviado con el informe parcial en PDF.'
              : 'WhatsApp enviado con el informe PDF adjunto.'
          );
        } else {
          toast.success(
            esInformeParcial
              ? 'WhatsApp enviado con enlace de descarga del informe parcial.'
              : 'WhatsApp enviado con enlace de descarga del informe.'
          );
        }
      } else if (whatsapp && envio?.whatsapp_enlace) {
        try {
          await downloadInformeLimsPdf(orden.id);
        } catch {
          /* el operador puede descargar desde la orden */
        }
        window.open(envio.whatsapp_enlace, '_blank', 'noopener,noreferrer');
        toast.success(
          'Se descargó el PDF y se abrió WhatsApp: adjunte el archivo al chat si el envío automático no estaba disponible.',
          { duration: 6000 }
        );
      }

      (envio?.advertencias || []).forEach((w) => toast(w, { icon: 'ℹ️', duration: 5000 }));
      onSuccess(res);
      onClose();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsEnviarInforme));
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open={open} onClose={sending ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {esInformeParcial ? 'Enviar informe parcial al paciente' : 'Enviar informe al paciente'}
      </DialogTitle>
      <DialogContent>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Orden {orden.numero || orden.id} — {orden.paciente_nombre || 'Paciente'}
        </Typography>
        {esInformeParcial && (
          <Alert severity="info" sx={{ mb: 2 }}>
            <strong>Informe parcial.</strong> El PDF incluye {progreso.conValor} de {progreso.total}{' '}
            resultados cargados. Los exámenes pendientes figuran sin valor y el documento indica que el
            informe no está completo. Podés enviar un informe definitivo cuando finalice la orden.
          </Alert>
        )}
        {!tieneEmail && !tieneTel && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            El paciente no tiene email ni teléfono cargados. Actualice los datos en la ficha del
            paciente.
          </Alert>
        )}
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          <FormControlLabel
            control={
              <Checkbox
                checked={email}
                onChange={(e) => setEmail(e.target.checked)}
                disabled={!tieneEmail || sending}
              />
            }
            label={
              <span>
                Email con PDF adjunto{' '}
                {tieneEmail ? `(${orden.paciente_email})` : '(no registrado)'}
              </span>
            }
          />
          <FormControlLabel
            control={
              <Checkbox
                checked={whatsapp}
                onChange={(e) => setWhatsapp(e.target.checked)}
                disabled={!tieneTel || sending}
              />
            }
            label={
              <span>
                WhatsApp {tieneTel ? `(${orden.paciente_telefono})` : '(no registrado)'}
              </span>
            }
          />
        </Box>
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>
          {esInformeParcial ? (
            <>
              El correo adjunta el PDF parcial. WhatsApp envía el PDF vía Twilio si está configurado; si
              no, se abre el chat con un enlace de descarga y se descarga el PDF para que usted lo adjunte.
            </>
          ) : (
            <>
              El correo incluye el PDF adjunto. WhatsApp envía el PDF vía Twilio si está configurado; si
              no, se abre el chat con un enlace de descarga y se descarga el PDF para que usted lo adjunte.
            </>
          )}
        </Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={sending}>
          Cancelar
        </Button>
        <Button
          variant="contained"
          color="primary"
          onClick={handleEnviar}
          disabled={sending || (!email && !whatsapp)}
        >
          {sending ? 'Enviando…' : esInformeParcial ? 'Enviar informe parcial' : 'Enviar informe'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default EnviarInformeOrdenDialog;
