import React, { useMemo, useState } from 'react';
import {
  Autocomplete,
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
import type {
  AisladoMicrobiologico,
  Antibiograma,
  Antibiotico,
  Microorganismo,
  ResultadoAntibiotico,
} from '../../../types/lims';
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
  microorganismos?: Microorganismo[];
  canOperate: boolean;
  onRefresh: () => void;
}

function labelMicroorganismo(m: Microorganismo): string {
  const code = (m.codigo || '').trim();
  const name = (m.nombre || '').trim();
  if (code && name) return `${code} — ${name}`;
  return name || code || `Micro #${m.id}`;
}

function labelAntibiotico(a: Antibiotico): string {
  const code = (a.codigo || '').trim();
  const name = (a.nombre || '').trim();
  if (code && name) return `${code} — ${name}`;
  return name || code || `AB #${a.id}`;
}

function antibioticoMatchesQuery(a: Antibiotico, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const haystack = [a.codigo, a.nombre, a.familia]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return haystack.includes(q);
}

const AntibiogramaPanel: React.FC<AntibiogramaPanelProps> = ({
  aislados,
  antibiogramas,
  resultados,
  antibioticos,
  microorganismos = [],
  canOperate,
  onRefresh,
}) => {
  const [aisladoId, setAisladoId] = useState<number | ''>('');
  const [abId, setAbId] = useState<number | ''>('');
  const [antibioticoSel, setAntibioticoSel] = useState<Antibiotico | null>(null);
  const [interp, setInterp] = useState('S');
  const [mic, setMic] = useState('');
  const { openMotivoDialog, dialogProps } = useMotivoDialog();

  const microById = useMemo(() => {
    const map = new Map<number, Microorganismo>();
    for (const m of microorganismos) map.set(m.id, m);
    return map;
  }, [microorganismos]);

  const antibioticoById = useMemo(() => {
    const map = new Map<number, Antibiotico>();
    for (const a of antibioticos) map.set(a.id, a);
    return map;
  }, [antibioticos]);

  const aisladosElegibles = aislados.filter((a) => a.estado === 'IDENTIFICADO' && a.microorganismo);

  const labelAislado = (a: AisladoMicrobiologico): string => {
    const microId = a.microorganismo ?? null;
    const micro = microId != null ? microById.get(microId) : undefined;
    const microLabel = micro
      ? labelMicroorganismo(micro)
      : microId != null
        ? `Micro #${microId}`
        : 'Sin microorganismo';
    return `#${a.id} · ${microLabel}`;
  };

  const labelAisladoDeAb = (ab: Antibiograma): string => {
    const aislado = aislados.find((a) => a.id === ab.aislado);
    if (!aislado) return `#${ab.aislado}`;
    return labelAislado(aislado);
  };

  const antibioticosActivos = useMemo(
    () => antibioticos.filter((a) => a.activo !== false),
    [antibioticos],
  );

  const antibiogramasAbiertos = antibiogramas.filter(
    (a) => !['COMPLETO', 'CANCELADO'].includes(a.estado),
  );

  const crearAb = async () => {
    if (aisladoId === '') {
      toast.error('Seleccione aislado identificado');
      return;
    }
    try {
      await createAntibiograma({ aislado_id: Number(aisladoId) });
      toast.success('Antibiograma creado');
      setAisladoId('');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarAntibiograma));
    }
  };

  const agregarResultado = async () => {
    if (abId === '' || !antibioticoSel) {
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
        antibiotico_id: antibioticoSel.id,
        interpretacion: interp,
        mic,
      });
      toast.success('Resultado agregado');
      setAntibioticoSel(null);
      setMic('');
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
      {canOperate && (
        <>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Nuevo antibiograma
            </Typography>
            <FormControl size="small" sx={{ minWidth: 280, mr: 2 }}>
              <InputLabel>Aislado identificado</InputLabel>
              <Select
                label="Aislado identificado"
                value={aisladoId === '' ? '' : String(aisladoId)}
                onChange={(e) => setAisladoId(e.target.value === '' ? '' : Number(e.target.value))}
              >
                <MenuItem value="">—</MenuItem>
                {aisladosElegibles.map((a) => (
                  <MenuItem key={a.id} value={a.id}>
                    {labelAislado(a)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Button variant="contained" onClick={crearAb} disabled={aisladosElegibles.length === 0}>
              Crear antibiograma
            </Button>
          </Paper>

          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle2" gutterBottom>
              Agregar resultado
            </Typography>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'flex-start' }}>
              <FormControl size="small" sx={{ minWidth: 200 }}>
                <InputLabel>Antibiograma</InputLabel>
                <Select
                  label="Antibiograma"
                  value={abId === '' ? '' : String(abId)}
                  onChange={(e) => setAbId(e.target.value === '' ? '' : Number(e.target.value))}
                >
                  <MenuItem value="">—</MenuItem>
                  {antibiogramasAbiertos.map((a) => (
                    <MenuItem key={a.id} value={a.id}>
                      #{a.id} · {labelAisladoDeAb(a)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Autocomplete
                size="small"
                sx={{ minWidth: 280, flex: '1 1 240px' }}
                options={antibioticosActivos}
                value={antibioticoSel}
                onChange={(_e, value) => setAntibioticoSel(value)}
                getOptionLabel={(a) => labelAntibiotico(a)}
                isOptionEqualToValue={(x, y) => x.id === y.id}
                filterOptions={(options, state) =>
                  options.filter((a) => antibioticoMatchesQuery(a, state.inputValue))
                }
                noOptionsText="Sin coincidencias"
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Antibiótico *"
                    placeholder="Buscar por código o nombre"
                  />
                )}
              />

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
              <Button
                variant="contained"
                onClick={agregarResultado}
                disabled={antibiogramasAbiertos.length === 0}
              >
                Agregar
              </Button>
            </Box>
          </Paper>
        </>
      )}

      <Typography variant="subtitle1" gutterBottom>
        Antibiogramas
      </Typography>
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
            {antibiogramas.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5}>
                  <Typography color="text.secondary">Sin antibiogramas.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              antibiogramas.map((ab) => (
                <TableRow key={ab.id}>
                  <TableCell>{ab.id}</TableCell>
                  <TableCell>{labelAisladoDeAb(ab)}</TableCell>
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
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Typography variant="subtitle1" gutterBottom>
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
            {resultados.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4}>
                  <Typography color="text.secondary">Sin resultados.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              resultados.map((r) => {
                const ab = antibioticoById.get(r.antibiotico);
                return (
                  <TableRow key={r.id}>
                    <TableCell>{r.antibiograma}</TableCell>
                    <TableCell>{ab ? labelAntibiotico(ab) : r.antibiotico}</TableCell>
                    <TableCell>{r.mic || '—'}</TableCell>
                    <TableCell>
                      <InterpretacionAntibioticoBadge interpretacion={r.interpretacion} />
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <MotivoDialog {...dialogProps} />
    </Box>
  );
};

export default AntibiogramaPanel;
