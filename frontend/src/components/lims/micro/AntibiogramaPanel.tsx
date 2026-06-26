import React, { useState } from 'react';
import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
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
import type { AisladoMicrobiologico, Antibiograma, Antibiotico, ResultadoAntibiotico } from '../../../types/lims';
import {
  cancelarAntibiograma,
  completarAntibiograma,
  createAntibiograma,
  createResultadoAntibiotico,
} from '../../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../../utils/apiError';
import { AntibiogramaEstadoBadge, InterpretacionAntibioticoBadge } from './MicroBadges';
import { MotivoDialog, useMotivoDialog } from './MotivoDialog';

const INTERPRETACIONES = ['S', 'I', 'R', 'SDD', 'NO_APLICA'];

export interface AntibiogramaPanelProps {
  aislados: AisladoMicrobiologico[];
  antibiogramas: Antibiograma[];
  resultados: ResultadoAntibiotico[];
  antibioticos: Antibiotico[];
  canOperate: boolean;
  onRefresh: () => void;
}

const AntibiogramaPanel: React.FC<AntibiogramaPanelProps> = ({
  aislados,
  antibiogramas,
  resultados,
  antibioticos,
  canOperate,
  onRefresh,
}) => {
  const [aisladoId, setAisladoId] = useState<number | ''>('');
  const [abId, setAbId] = useState<number | ''>('');
  const [antibioticoId, setAntibioticoId] = useState<number | ''>('');
  const [interp, setInterp] = useState('S');
  const [mic, setMic] = useState('');
  const { openMotivoDialog, dialogProps } = useMotivoDialog();

  const aisladosElegibles = aislados.filter((a) => a.estado === 'IDENTIFICADO' && a.microorganismo);

  const crearAb = async () => {
    if (aisladoId === '') {
      toast.error('Seleccione aislado identificado');
      return;
    }
    try {
      await createAntibiograma({ aislado_id: Number(aisladoId) });
      toast.success('Antibiograma creado');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarAntibiograma));
    }
  };

  const agregarResultado = async () => {
    if (abId === '' || antibioticoId === '') {
      toast.error('Antibiograma y antibiótico requeridos');
      return;
    }
    const ab = antibiogramas.find((x) => x.id === Number(abId));
    if (ab && ['COMPLETO', 'CANCELADO'].includes(ab.estado)) {
      toast.error('Antibiograma cerrado');
      return;
    }
    try {
      await createResultadoAntibiotico({
        antibiograma_id: Number(abId),
        antibiotico_id: Number(antibioticoId),
        interpretacion: interp,
        mic,
      });
      toast.success('Resultado agregado');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarResultadoAntibiograma));
    }
  };

  const completar = async (id: number) => {
    try {
      await completarAntibiograma(id);
      toast.success('Antibiograma completado');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCompletarAntibiograma));
    }
  };

  const cancelar = (id: number) => {
    openMotivoDialog({
      title: 'Cancelar antibiograma',
      label: 'Motivo de cancelación',
      confirmLabel: 'Cancelar antibiograma',
      onConfirm: async (motivo) => {
        try {
          await cancelarAntibiograma(id, motivo);
          toast.success('Antibiograma cancelado');
          onRefresh();
        } catch (e) {
          const msg = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsCancelarAntibiograma);
          toast.error(msg);
          throw new Error(msg);
        }
      },
    });
  };

  return (
    <Box>
      <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Aislado</TableCell>
              <TableCell>Estado</TableCell>
              <TableCell>Método</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {antibiogramas.map((ab) => (
              <TableRow key={ab.id}>
                <TableCell>{ab.id}</TableCell>
                <TableCell>{ab.aislado}</TableCell>
                <TableCell>
                  <AntibiogramaEstadoBadge estado={ab.estado} />
                </TableCell>
                <TableCell>{ab.metodo || '—'}</TableCell>
                <TableCell>
                  {canOperate && ab.estado !== 'COMPLETO' && ab.estado !== 'CANCELADO' && (
                    <>
                      <Button size="small" onClick={() => completar(ab.id)}>
                        Completar
                      </Button>
                      <Button size="small" color="error" onClick={() => cancelar(ab.id)}>
                        Cancelar
                      </Button>
                    </>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="subtitle2" gutterBottom>
        Resultados
      </Typography>
      <TableContainer component={Paper} variant="outlined" sx={{ mb: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Antibiograma</TableCell>
              <TableCell>Antibiótico</TableCell>
              <TableCell>MIC</TableCell>
              <TableCell>Interp.</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {resultados.map((r) => (
              <TableRow key={r.id}>
                <TableCell>{r.antibiograma}</TableCell>
                <TableCell>{antibioticos.find((a) => a.id === r.antibiotico)?.codigo || r.antibiotico}</TableCell>
                <TableCell>{r.mic || '—'}</TableCell>
                <TableCell>
                  <InterpretacionAntibioticoBadge interpretacion={r.interpretacion} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {canOperate && (
        <>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Nuevo antibiograma
            </Typography>
            <FormControl size="small" sx={{ minWidth: 200, mr: 2 }}>
              <InputLabel>Aislado identificado</InputLabel>
              <Select
                label="Aislado identificado"
                value={aisladoId === '' ? '' : String(aisladoId)}
                onChange={(e) => setAisladoId(e.target.value === '' ? '' : Number(e.target.value))}
              >
                <MenuItem value="">—</MenuItem>
                {aisladosElegibles.map((a) => (
                  <MenuItem key={a.id} value={a.id}>
                    #{a.id}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button variant="contained" onClick={crearAb}>
              Crear antibiograma
            </Button>
          </Paper>
          <Paper sx={{ p: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Agregar resultado
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
              <FormControl size="small" sx={{ minWidth: 140 }}>
                <InputLabel>Antibiograma</InputLabel>
                <Select label="Antibiograma" value={abId === '' ? '' : String(abId)} onChange={(e) => setAbId(e.target.value === '' ? '' : Number(e.target.value))}>
                  <MenuItem value="">—</MenuItem>
                  {antibiogramas
                    .filter((a) => !['COMPLETO', 'CANCELADO'].includes(a.estado))
                    .map((a) => (
                      <MenuItem key={a.id} value={a.id}>
                        #{a.id}
                      </MenuItem>
                    ))}
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 160 }}>
                <InputLabel>Antibiótico</InputLabel>
                <Select
                  label="Antibiótico"
                  value={antibioticoId === '' ? '' : String(antibioticoId)}
                  onChange={(e) => setAntibioticoId(e.target.value === '' ? '' : Number(e.target.value))}
                >
                  <MenuItem value="">—</MenuItem>
                  {antibioticos.filter((a) => a.activo !== false).map((a) => (
                    <MenuItem key={a.id} value={a.id}>
                      {a.codigo}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <FormControl size="small" sx={{ minWidth: 120 }}>
                <InputLabel>Interp.</InputLabel>
                <Select label="Interp." value={interp} onChange={(e) => setInterp(e.target.value)}>
                  {INTERPRETACIONES.map((i) => (
                    <MenuItem key={i} value={i}>
                      {i}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField size="small" label="MIC" value={mic} onChange={(e) => setMic(e.target.value)} />
              <Button variant="contained" onClick={agregarResultado}>
                Agregar
              </Button>
            </Box>
          </Paper>
        </>
      )}
      <MotivoDialog {...dialogProps} />
    </Box>
  );
};

export default AntibiogramaPanel;
