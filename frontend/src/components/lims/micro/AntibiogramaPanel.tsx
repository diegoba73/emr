import React, { useMemo, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
  deleteAntibiograma,
  deleteResultadoAntibiotico,
  updateAntibiograma,
  updateResultadoAntibiotico,
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
  /** Cultivo sin desarrollo: no corresponde antibiograma. */
  cultivoSinDesarrollo?: boolean;
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
  cultivoSinDesarrollo = false,
}) => {
  const [aisladoId, setAisladoId] = useState<number | ''>('');
  const [abId, setAbId] = useState<number | ''>('');
  const [antibioticoSel, setAntibioticoSel] = useState<Antibiotico | null>(null);
  const [interp, setInterp] = useState('S');
  const [mic, setMic] = useState('');
  const [halo, setHalo] = useState('');
  const [metodoRes, setMetodoRes] = useState('');
  const [estandar, setEstandar] = useState('');
  const { openMotivoDialog, dialogProps } = useMotivoDialog();
  const [editAb, setEditAb] = useState<Antibiograma | null>(null);
  const [editAbForm, setEditAbForm] = useState({ metodo: '', observaciones: '' });
  const [editRes, setEditRes] = useState<ResultadoAntibiotico | null>(null);
  const [editResForm, setEditResForm] = useState({
    interpretacion: 'S',
    mic: '',
    halo_mm: '',
    metodo: '',
    estandar_version: '',
    observaciones: '',
  });
  const [editSaving, setEditSaving] = useState(false);

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
        halo_mm: halo.trim() ? halo.trim() : null,
        metodo: metodoRes.trim() || undefined,
        estandar_version: estandar.trim() || undefined,
      });
      toast.success('Resultado agregado');
      setAntibioticoSel(null);
      setMic('');
      setHalo('');
      setMetodoRes('');
      setEstandar('');
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

  const eliminarAb = async (ab: Antibiograma) => {
    const nRes = resultados.filter((r) => r.antibiograma === ab.id).length;
    const msg =
      nRes > 0
        ? `¿Eliminar antibiograma #${ab.id}? También se eliminarán ${nRes} resultado(s). Esta acción no se puede deshacer.`
        : `¿Eliminar antibiograma #${ab.id}? Esta acción no se puede deshacer.`;
    if (!window.confirm(msg)) return;
    try {
      await deleteAntibiograma(ab.id);
      toast.success('Antibiograma eliminado');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsEliminarRegistroMicro));
    }
  };

  const eliminarResultado = async (r: ResultadoAntibiotico) => {
    if (
      !window.confirm(
        `¿Eliminar resultado #${r.id}? Esta acción no se puede deshacer.`
      )
    ) {
      return;
    }
    try {
      await deleteResultadoAntibiotico(r.id);
      toast.success('Resultado eliminado');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsEliminarRegistroMicro));
    }
  };

  const openEditarAb = (ab: Antibiograma) => {
    setEditAb(ab);
    setEditAbForm({ metodo: ab.metodo || '', observaciones: ab.observaciones || '' });
  };

  const guardarAb = async () => {
    if (!editAb) return;
    setEditSaving(true);
    try {
      await updateAntibiograma(editAb.id, {
        metodo: editAbForm.metodo,
        observaciones: editAbForm.observaciones,
      });
      toast.success('Antibiograma actualizado');
      setEditAb(null);
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarAntibiograma));
    } finally {
      setEditSaving(false);
    }
  };

  const openEditarRes = (r: ResultadoAntibiotico) => {
    setEditRes(r);
    setEditResForm({
      interpretacion: r.interpretacion || 'S',
      mic: r.mic || '',
      halo_mm: r.halo_mm != null && r.halo_mm !== '' ? String(r.halo_mm) : '',
      metodo: r.metodo || '',
      estandar_version: r.estandar_version || '',
      observaciones: r.observaciones || '',
    });
  };

  const guardarRes = async () => {
    if (!editRes) return;
    setEditSaving(true);
    try {
      await updateResultadoAntibiotico(editRes.id, {
        interpretacion: editResForm.interpretacion,
        mic: editResForm.mic,
        halo_mm: editResForm.halo_mm || null,
        metodo: editResForm.metodo,
        estandar_version: editResForm.estandar_version,
        observaciones: editResForm.observaciones,
      });
      toast.success('Resultado actualizado');
      setEditRes(null);
      onRefresh();
    } catch (e) {
      toast.error(
        getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarResultadoAntibiograma)
      );
    } finally {
      setEditSaving(false);
    }
  };

  return (
    <Box>
      {cultivoSinDesarrollo && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Cultivo <strong>sin desarrollo</strong>: no corresponde antibiograma. Emití el informe
          final en la pestaña <strong>Informes</strong>.
        </Alert>
      )}
      {canOperate && !cultivoSinDesarrollo && (
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
              <TextField size="small" label="MIC/CIM" value={mic} onChange={(e) => setMic(e.target.value)} />
              <TextField
                size="small"
                label="Halo (mm)"
                value={halo}
                onChange={(e) => setHalo(e.target.value)}
                sx={{ width: 110 }}
              />
              <TextField
                size="small"
                label="Método"
                value={metodoRes}
                onChange={(e) => setMetodoRes(e.target.value)}
                sx={{ minWidth: 140 }}
              />
              <TextField
                size="small"
                label="Estándar/versión"
                value={estandar}
                onChange={(e) => setEstandar(e.target.value)}
                placeholder="CLSI / EUCAST"
                sx={{ minWidth: 160 }}
              />
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
                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                    {canOperate && ab.estado !== 'COMPLETO' && ab.estado !== 'CANCELADO' && (
                      <>
                        <Button size="small" onClick={() => openEditarAb(ab)}>
                          Editar
                        </Button>
                        <Button size="small" onClick={() => completar(ab.id)}>
                          Completar
                        </Button>
                        <Button size="small" color="warning" onClick={() => cancelar(ab.id)}>
                          Cancelar
                        </Button>
                      </>
                    )}
                    {canOperate && (
                      <Button size="small" color="error" onClick={() => eliminarAb(ab)}>
                        Eliminar
                      </Button>
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
              <TableCell>Halo</TableCell>
              <TableCell>MIC</TableCell>
              <TableCell>Método</TableCell>
              <TableCell>Estándar</TableCell>
              <TableCell>Interp.</TableCell>
              {canOperate && <TableCell />}
            </TableRow>
          </TableHead>
          <TableBody>
            {resultados.length === 0 ? (
              <TableRow>
                <TableCell colSpan={canOperate ? 8 : 7}>
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
                    <TableCell>
                      {r.halo_mm != null && r.halo_mm !== ''
                        ? `${r.halo_mm}${r.unidad_halo ? ` ${r.unidad_halo}` : ''}`
                        : '—'}
                    </TableCell>
                    <TableCell>{r.mic || '—'}</TableCell>
                    <TableCell>{r.metodo || '—'}</TableCell>
                    <TableCell>{r.estandar_version || '—'}</TableCell>
                    <TableCell>
                      <InterpretacionAntibioticoBadge interpretacion={r.interpretacion} />
                    </TableCell>
                    {canOperate && (
                      <TableCell sx={{ whiteSpace: 'nowrap' }}>
                        <Button
                          size="small"
                          onClick={() => openEditarRes(r)}
                          disabled={
                            antibiogramas.find((a) => a.id === r.antibiograma)?.estado ===
                              'COMPLETO' ||
                            antibiogramas.find((a) => a.id === r.antibiograma)?.estado ===
                              'CANCELADO'
                          }
                        >
                          Editar
                        </Button>
                        <Button size="small" color="error" onClick={() => eliminarResultado(r)}>
                          Eliminar
                        </Button>
                      </TableCell>
                    )}
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={Boolean(editAb)} onClose={() => setEditAb(null)} fullWidth maxWidth="sm">
        <DialogTitle>Editar antibiograma #{editAb?.id}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField
              size="small"
              label="Método"
              value={editAbForm.metodo}
              onChange={(e) => setEditAbForm((f) => ({ ...f, metodo: e.target.value }))}
            />
            <TextField
              size="small"
              label="Observaciones"
              fullWidth
              multiline
              minRows={2}
              value={editAbForm.observaciones}
              onChange={(e) => setEditAbForm((f) => ({ ...f, observaciones: e.target.value }))}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditAb(null)}>Cancelar</Button>
          <Button variant="contained" onClick={guardarAb} disabled={editSaving}>
            Guardar
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(editRes)} onClose={() => setEditRes(null)} fullWidth maxWidth="sm">
        <DialogTitle>Editar resultado #{editRes?.id}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <FormControl size="small" fullWidth>
              <InputLabel>Interpretación</InputLabel>
              <Select
                label="Interpretación"
                value={editResForm.interpretacion}
                onChange={(e) =>
                  setEditResForm((f) => ({ ...f, interpretacion: e.target.value }))
                }
              >
                {INTERPRETACIONES.map((i) => (
                  <MenuItem key={i} value={i}>
                    {i}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <TextField
              size="small"
              label="MIC/CIM"
              value={editResForm.mic}
              onChange={(e) => setEditResForm((f) => ({ ...f, mic: e.target.value }))}
            />
            <TextField
              size="small"
              label="Halo (mm)"
              value={editResForm.halo_mm}
              onChange={(e) => setEditResForm((f) => ({ ...f, halo_mm: e.target.value }))}
            />
            <TextField
              size="small"
              label="Método"
              value={editResForm.metodo}
              onChange={(e) => setEditResForm((f) => ({ ...f, metodo: e.target.value }))}
            />
            <TextField
              size="small"
              label="Estándar/versión"
              value={editResForm.estandar_version}
              onChange={(e) =>
                setEditResForm((f) => ({ ...f, estandar_version: e.target.value }))
              }
            />
            <TextField
              size="small"
              label="Observaciones"
              fullWidth
              multiline
              minRows={2}
              value={editResForm.observaciones}
              onChange={(e) =>
                setEditResForm((f) => ({ ...f, observaciones: e.target.value }))
              }
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditRes(null)}>Cancelar</Button>
          <Button variant="contained" onClick={guardarRes} disabled={editSaving}>
            Guardar
          </Button>
        </DialogActions>
      </Dialog>

      <MotivoDialog {...dialogProps} />
    </Box>
  );
};

export default AntibiogramaPanel;
