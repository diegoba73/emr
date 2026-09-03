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
import type { EnviarInformeOrdenResponse, SolicitudExamenLims } from '../../types/lims';
import { downloadInformeLimsPdf, postEnviarInformeOrden } from '../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../utils/apiError';
import WhatsAppAbrirChatsStep, { type WhatsAppChatEnlace } from './WhatsAppAbrirChatsStep';

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
  const [emailPaciente, setEmailPaciente] = useState(true);
  const [whatsappPaciente, setWhatsappPaciente] = useState(true);
  const [emailMedico, setEmailMedico] = useState(false);
  const [whatsappMedico, setWhatsappMedico] = useState(false);
  const [sending, setSending] = useState(false);
  const [pasoWhatsapp, setPasoWhatsapp] = useState<{
    enlaces: WhatsAppChatEnlace[];
    pdfDescargado: boolean;
    resultado: EnviarInformeOrdenResponse;
  } | null>(null);

  const tieneEmailPac = Boolean((orden.paciente_email || '').trim());
  const tieneTelPac = Boolean((orden.paciente_telefono || '').trim());
  const tieneMedicoInterno = Boolean(orden.medico_interno);
  const tieneEmailMed = Boolean((orden.medico_email || '').trim());
  const tieneTelMed = Boolean((orden.medico_telefono || '').trim());
  const medicoLabel =
    orden.medico_interno_nombre || orden.medico_display || 'Médico solicitante';

  const ordenValidada = orden.estado === 'FINALIZADO';

  useEffect(() => {
    if (!open) return;
    setEmailPaciente(tieneEmailPac);
    setWhatsappPaciente(tieneTelPac);
    setEmailMedico(tieneMedicoInterno && tieneEmailMed);
    setWhatsappMedico(false);
    setPasoWhatsapp(null);
  }, [open, tieneEmailPac, tieneTelPac, tieneMedicoInterno, tieneEmailMed]);

  const algunoSeleccionado =
    emailPaciente || whatsappPaciente || emailMedico || whatsappMedico;

  const cerrarTrasExito = (resultado: SolicitudExamenLims) => {
    onSuccess(resultado);
    onClose();
  };

  const handleEnviar = async () => {
    if (!ordenValidada) {
      toast.error('Solo se puede enviar el informe después de la validación del bioquímico.');
      return;
    }
    if (!algunoSeleccionado) {
      toast.error('Seleccioná al menos un canal de envío.');
      return;
    }
    setSending(true);
    try {
      const res = await postEnviarInformeOrden(orden.id, {
        email: emailPaciente,
        whatsapp: whatsappPaciente,
        email_medico: emailMedico,
        whatsapp_medico: whatsappMedico,
      });
      const envio = res.envio;

      if (envio?.email_enviado) {
        const adj = envio.email_adjunto_pdf !== false;
        toast.success(
          adj
            ? `Informe enviado por correo a ${envio.email_destino || 'destinatarios'} con PDF adjunto.`
            : `Informe enviado por correo a ${envio.email_destino || 'destinatarios'}.`
        );
      }

      if (envio?.whatsapp_enviado) {
        toast.success(
          envio.whatsapp_pdf_adjunto
            ? 'WhatsApp enviado con el informe PDF adjunto.'
            : 'WhatsApp enviado con enlace de descarga del informe.'
        );
      }

      const enlacesFallback = (envio?.whatsapp_enlaces || []).filter(
        (e): e is WhatsAppChatEnlace => Boolean(e?.enlace)
      );
      if (enlacesFallback.length === 0 && envio?.whatsapp_enlace) {
        enlacesFallback.push({
          rol: 'paciente',
          telefono: envio.whatsapp_telefono || '',
          enlace: envio.whatsapp_enlace,
        });
      }
      const pidioWhatsapp = whatsappPaciente || whatsappMedico;
      const necesitaPasoManual =
        pidioWhatsapp && !envio?.whatsapp_enviado && enlacesFallback.length > 0;

      (envio?.advertencias || []).forEach((w) => toast(w, { icon: 'ℹ️', duration: 5000 }));

      if (necesitaPasoManual) {
        let pdfDescargado = false;
        try {
          await downloadInformeLimsPdf(orden.id);
          pdfDescargado = true;
        } catch {
          /* el operador puede descargar desde la orden */
        }
        setPasoWhatsapp({ enlaces: enlacesFallback, pdfDescargado, resultado: res });
        return;
      }

      cerrarTrasExito(res);
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsEnviarInforme));
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={sending ? undefined : () => (pasoWhatsapp ? cerrarTrasExito(pasoWhatsapp.resultado) : onClose())}
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>{pasoWhatsapp ? 'Abrir WhatsApp' : 'Enviar informe'}</DialogTitle>
      <DialogContent>
        {pasoWhatsapp ? (
          <WhatsAppAbrirChatsStep
            enlaces={pasoWhatsapp.enlaces}
            pdfDescargado={pasoWhatsapp.pdfDescargado}
          />
        ) : (
          <>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Orden {orden.numero || orden.id} — {orden.paciente_nombre || 'Paciente'}
              {medicoLabel ? ` · ${medicoLabel}` : ''}
            </Typography>
            {!ordenValidada && (
              <Alert severity="error" sx={{ mb: 2 }}>
                La orden aún no está validada. Solo se puede enviar el informe después de{' '}
                <strong>Validar y liberar</strong>.
              </Alert>
            )}
            {!tieneEmailPac && !tieneTelPac && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                El paciente no tiene email ni teléfono cargados.
              </Alert>
            )}
            {tieneMedicoInterno && !tieneEmailMed && !tieneTelMed && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                El médico solicitante no tiene email ni teléfono en su usuario del sistema.
              </Alert>
            )}
            {!tieneMedicoInterno && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Esta orden no tiene médico interno vinculado
                {orden.medico_externo_nombre
                  ? ` (solicitante externo: ${orden.medico_externo_nombre})`
                  : ''}
                ; solo se puede enviar al paciente.
              </Alert>
            )}

            <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
              Paciente
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5, mb: 2 }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={emailPaciente}
                    onChange={(e) => setEmailPaciente(e.target.checked)}
                    disabled={!tieneEmailPac || sending}
                  />
                }
                label={
                  <span>
                    Email con PDF adjunto{' '}
                    {tieneEmailPac ? `(${orden.paciente_email})` : '(no registrado)'}
                  </span>
                }
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={whatsappPaciente}
                    onChange={(e) => setWhatsappPaciente(e.target.checked)}
                    disabled={!tieneTelPac || sending}
                  />
                }
                label={
                  <span>
                    WhatsApp (después se abre el chat){' '}
                    {tieneTelPac ? `(${orden.paciente_telefono})` : '(no registrado)'}
                  </span>
                }
              />
            </Box>

            <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
              Médico solicitante
            </Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={emailMedico}
                    onChange={(e) => setEmailMedico(e.target.checked)}
                    disabled={!tieneMedicoInterno || !tieneEmailMed || sending}
                  />
                }
                label={
                  <span>
                    Email con PDF adjunto{' '}
                    {!tieneMedicoInterno
                      ? '(sin médico interno)'
                      : tieneEmailMed
                        ? `(${orden.medico_email})`
                        : '(no registrado)'}
                  </span>
                }
              />
              <FormControlLabel
                control={
                  <Checkbox
                    checked={whatsappMedico}
                    onChange={(e) => setWhatsappMedico(e.target.checked)}
                    disabled={!tieneMedicoInterno || !tieneTelMed || sending}
                  />
                }
                label={
                  <span>
                    WhatsApp (después se abre el chat){' '}
                    {!tieneMedicoInterno
                      ? '(sin médico interno)'
                      : tieneTelMed
                        ? `(${orden.medico_telefono})`
                        : '(no registrado)'}
                  </span>
                }
              />
            </Box>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 2 }}>
          El correo se envía solo. WhatsApp no: después te pedimos que abras el chat y pulses
          Enviar. En esta PC (localhost) el mensaje no lleva link — adjuntá el PDF descargado.
          En el servidor público sí se incluye el enlace.
            </Typography>
          </>
        )}
      </DialogContent>
      <DialogActions>
        {pasoWhatsapp ? (
          <Button variant="contained" onClick={() => cerrarTrasExito(pasoWhatsapp.resultado)}>
            Listo
          </Button>
        ) : (
          <>
            <Button onClick={onClose} disabled={sending}>
              Cancelar
            </Button>
            <Button
              variant="contained"
              color="primary"
              onClick={handleEnviar}
              disabled={sending || !algunoSeleccionado || !ordenValidada}
            >
              {sending ? 'Enviando…' : 'Enviar informe'}
            </Button>
          </>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default EnviarInformeOrdenDialog;
