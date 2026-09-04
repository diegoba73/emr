import React, { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { EstudioMicrobiologia, InformeMicrobiologia } from '../../../types/lims';
import {
  anularInformeMicrobiologia,
  createInformeMicrobiologia,
  downloadInformeMicroPdf,
  emitirInformeMicrobiologia,
  updateInformeMicrobiologia,
  validarInformeMicrobiologia,
} from '../../../services/limsApi';
import EnviarInformeMicroDialog from '../EnviarInformeMicroDialog';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../../utils/apiError';
import { InformeMicrobiologiaEstadoBadge } from './MicroBadges';
import { MotivoDialog, useMotivoDialog } from './MotivoDialog';
import { ordenPuedeValidarObraSocial } from '../../../utils/limsObraSocial';

export interface InformesMicrobiologiaPanelProps {
  estudio: EstudioMicrobiologia;
  informes: InformeMicrobiologia[];
  /** Solo bioquímico/admin: crear, editar, emitir, anular. */
  canOperate: boolean;
  canValidar: boolean;
  canDownloadPdf?: boolean;
  canEnviar?: boolean;
  onRefresh: () => void;
}

const ESTADOS_PDF_BIO = new Set(['EMITIDO', 'VALIDADO']);
const ESTADOS_PDF_PUBLICO = new Set(['VALIDADO']);

const InformesMicrobiologiaPanel: React.FC<InformesMicrobiologiaPanelProps> = ({
  estudio,
  informes,
  canOperate,
  canValidar,
  canDownloadPdf = false,
  canEnviar = false,
  onRefresh,
}) => {
  const [textoNuevo, setTextoNuevo] = useState('');
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [downloading, setDownloading] = useState(false);
  const [enviarOpen, setEnviarOpen] = useState(false);
  const { openMotivoDialog, dialogProps } = useMotivoDialog();

  useEffect(() => {
    const d: Record<number, string> = {};
    for (const inf of informes) {
      if (inf.estado === 'BORRADOR') d[inf.id] = inf.texto || '';
    }
    setDrafts(d);
  }, [informes]);

  const finalVigente = informes.find((i) => i.tipo === 'FINAL' && i.estado !== 'ANULADO');
  const estadosPdf = canOperate || canValidar ? ESTADOS_PDF_BIO : ESTADOS_PDF_PUBLICO;
  const finalEntregable =
    finalVigente && estadosPdf.has(finalVigente.estado) ? finalVigente : null;
  const faltaFinal = !finalVigente && estudio.estado !== 'CANCELADO';
  const lecturasolo = !canOperate && !canValidar;
  const osPermiteValidar = ordenPuedeValidarObraSocial(estudio);

  const crear = async (tipo: 'PRELIMINAR' | 'FINAL') => {
    try {
      await createInformeMicrobiologia({
        estudio_id: estudio.id,
        tipo,
        texto: textoNuevo,
      });
      toast.success(`Informe ${tipo} en borrador`);
      setTextoNuevo('');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarInforme));
    }
  };

  const guardarBorrador = async (inf: InformeMicrobiologia) => {
    if (inf.estado !== 'BORRADOR') return;
    try {
      await updateInformeMicrobiologia(inf.id, { texto: drafts[inf.id] ?? '' });
      toast.success('Borrador actualizado');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarInforme));
    }
  };

  const emitir = async (id: number) => {
    try {
      await emitirInformeMicrobiologia(id, {});
      toast.success('Informe emitido');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsEmitirInforme));
    }
  };

  const validar = async (id: number) => {
    if (!osPermiteValidar) {
      toast.error(
        'En órdenes ambulatorias la obra social tiene que estar Autorizada antes de validar.'
      );
      return;
    }
    try {
      await validarInformeMicrobiologia(id);
      toast.success('Informe final validado');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsValidarInforme));
    }
  };

  const anular = (id: number) => {
    openMotivoDialog({
      title: 'Anular informe',
      label: 'Motivo de anulación',
      confirmLabel: 'Anular informe',
      onConfirm: async (motivo) => {
        try {
          await anularInformeMicrobiologia(id, motivo);
          toast.success('Informe anulado');
          onRefresh();
        } catch (e) {
          const msg = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsAnularInforme);
          toast.error(msg);
          throw new Error(msg);
        }
      },
    });
  };

  const descargarPdf = async () => {
    setDownloading(true);
    try {
      await downloadInformeMicroPdf(estudio.id);
      toast.success('PDF descargado');
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsDescargarInforme));
    } finally {
      setDownloading(false);
    }
  };

  if (lecturasolo && informes.length === 0) {
    return (
      <Box>
        <Alert severity="info">
          El informe estará disponible para consulta y descarga cuando el bioquímico lo valide.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {!osPermiteValidar && estudio.estado !== 'VALIDADO' && estudio.estado !== 'INFORMADO' && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          En órdenes ambulatorias la obra social tiene que estar <strong>Autorizada</strong> para
          validar y emitir el informe.
        </Alert>
      )}
      {canOperate && faltaFinal && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No hay informe final vigente. Se requiere informe final validado para marcar el estudio
          como informado.
        </Alert>
      )}
      {lecturasolo && finalEntregable && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Informe final validado. Ya puede consultarlo o descargar el PDF.
        </Alert>
      )}
      {finalEntregable && (canDownloadPdf || canEnviar) && (
        <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
          {canDownloadPdf && (
            <Button variant="outlined" onClick={descargarPdf} disabled={downloading}>
              {downloading ? 'Descargando…' : 'Descargar PDF'}
            </Button>
          )}
          {canEnviar && (
            <Button variant="contained" onClick={() => setEnviarOpen(true)}>
              Enviar informe
            </Button>
          )}
        </Box>
      )}
      <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Tipo</TableCell>
              <TableCell>Estado</TableCell>
              <TableCell>Texto</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {informes.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5}>
                  <Typography color="text.secondary">Sin informes cargados.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              informes.map((inf) => (
                <TableRow key={inf.id}>
                  <TableCell>{inf.id}</TableCell>
                  <TableCell>{inf.tipo}</TableCell>
                  <TableCell>
                    <InformeMicrobiologiaEstadoBadge estado={inf.estado} tipo={inf.tipo} />
                  </TableCell>
                  <TableCell sx={{ maxWidth: 280 }}>
                    {inf.estado === 'BORRADOR' && canOperate ? (
                      <TextField
                        fullWidth
                        multiline
                        minRows={2}
                        size="small"
                        value={drafts[inf.id] ?? ''}
                        onChange={(e) =>
                          setDrafts((d) => ({ ...d, [inf.id]: e.target.value }))
                        }
                      />
                    ) : (
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {(inf.texto || '').slice(0, 200)}
                        {(inf.texto || '').length > 200 ? '…' : ''}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {canOperate && inf.estado === 'BORRADOR' && (
                      <>
                        <Button size="small" onClick={() => guardarBorrador(inf)}>
                          Guardar
                        </Button>
                        <Button size="small" variant="contained" onClick={() => emitir(inf.id)}>
                          Emitir
                        </Button>
                      </>
                    )}
                    {canOperate && inf.estado === 'EMITIDO' && (
                      <Button size="small" color="error" onClick={() => anular(inf.id)}>
                        Anular
                      </Button>
                    )}
                    {canValidar && inf.tipo === 'FINAL' && inf.estado === 'EMITIDO' && (
                      <Tooltip
                        title={
                          osPermiteValidar
                            ? ''
                            : 'La obra social tiene que estar Autorizada para validar el informe.'
                        }
                      >
                        <span>
                          <Button
                            size="small"
                            color="success"
                            disabled={!osPermiteValidar}
                            onClick={() => validar(inf.id)}
                          >
                            Validar
                          </Button>
                        </span>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {canOperate && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Nuevo informe (borrador)
          </Typography>
          <TextField
            fullWidth
            multiline
            minRows={4}
            label="Texto"
            value={textoNuevo}
            onChange={(e) => setTextoNuevo(e.target.value)}
            sx={{ mb: 1 }}
          />
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button variant="outlined" onClick={() => crear('PRELIMINAR')}>
              Preliminar
            </Button>
            <Button variant="contained" onClick={() => crear('FINAL')}>
              Final
            </Button>
          </Box>
        </Paper>
      )}
      <MotivoDialog {...dialogProps} />
      <EnviarInformeMicroDialog
        open={enviarOpen}
        estudio={estudio}
        onClose={() => setEnviarOpen(false)}
        onSuccess={onRefresh}
      />
    </Box>
  );
};

export default InformesMicrobiologiaPanel;
