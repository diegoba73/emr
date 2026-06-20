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
  Typography,
} from '@mui/material';
import toast from 'react-hot-toast';
import type { EstudioMicrobiologia, InformeMicrobiologia } from '../../../types/lims';
import {
  anularInformeMicrobiologia,
  createInformeMicrobiologia,
  emitirInformeMicrobiologia,
  formatDrfError,
  updateInformeMicrobiologia,
  validarInformeMicrobiologia,
} from '../../../services/limsApi';
import { InformeMicrobiologiaEstadoBadge } from './MicroBadges';
import { MotivoDialog, useMotivoDialog } from './MotivoDialog';

export interface InformesMicrobiologiaPanelProps {
  estudio: EstudioMicrobiologia;
  informes: InformeMicrobiologia[];
  canOperate: boolean;
  canValidar: boolean;
  onRefresh: () => void;
}

const InformesMicrobiologiaPanel: React.FC<InformesMicrobiologiaPanelProps> = ({
  estudio,
  informes,
  canOperate,
  canValidar,
  onRefresh,
}) => {
  const [textoNuevo, setTextoNuevo] = useState('');
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const { openMotivoDialog, dialogProps } = useMotivoDialog();

  useEffect(() => {
    const d: Record<number, string> = {};
    for (const inf of informes) {
      if (inf.estado === 'BORRADOR') d[inf.id] = inf.texto || '';
    }
    setDrafts(d);
  }, [informes]);

  const finalVigente = informes.find((i) => i.tipo === 'FINAL' && i.estado !== 'ANULADO');
  const faltaFinal = !finalVigente && estudio.estado !== 'CANCELADO';

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
      toast.error(formatDrfError(e));
    }
  };

  const guardarBorrador = async (inf: InformeMicrobiologia) => {
    if (inf.estado !== 'BORRADOR') return;
    try {
      await updateInformeMicrobiologia(inf.id, { texto: drafts[inf.id] ?? '' });
      toast.success('Borrador actualizado');
      onRefresh();
    } catch (e) {
      toast.error(formatDrfError(e));
    }
  };

  const emitir = async (id: number) => {
    try {
      await emitirInformeMicrobiologia(id, {});
      toast.success('Informe emitido');
      onRefresh();
    } catch (e) {
      toast.error(formatDrfError(e));
    }
  };

  const validar = async (id: number) => {
    try {
      await validarInformeMicrobiologia(id);
      toast.success('Informe final validado');
      onRefresh();
    } catch (e) {
      toast.error(formatDrfError(e));
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
          const msg = formatDrfError(e);
          toast.error(msg);
          throw new Error(msg);
        }
      },
    });
  };

  return (
    <Box>
      {faltaFinal && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          No hay informe final vigente. Se requiere informe final validado para marcar el estudio como informado.
        </Alert>
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
            {informes.map((inf) => (
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
                      onChange={(e) => setDrafts((d) => ({ ...d, [inf.id]: e.target.value }))}
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
                    <Button size="small" color="success" onClick={() => validar(inf.id)}>
                      Validar
                    </Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
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
    </Box>
  );
};

export default InformesMicrobiologiaPanel;
