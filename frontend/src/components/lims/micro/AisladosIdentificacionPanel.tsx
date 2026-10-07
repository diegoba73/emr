import React, { useMemo, useState } from 'react';
import {
  Autocomplete,
  Alert,
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
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
  IdentificacionMicroorganismo,
  LecturaCultivo,
  Microorganismo,
  SignificanciaAislado,
} from '../../../types/lims';
import {
  createAisladoMicrobiologico,
  createIdentificacionMicroorganismo,
  deleteAisladoMicrobiologico,
  deleteIdentificacionMicroorganismo,
  descartarAisladoMicrobiologico,
  updateAisladoMicrobiologico,
  updateIdentificacionMicroorganismo,
} from '../../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../../utils/apiError';
import { todasLecturasSinDesarrollo } from '../../../utils/limsMicroCultivoNegativo';
import { AisladoEstadoBadge } from './MicroBadges';
import { MotivoDialog, useMotivoDialog } from './MotivoDialog';

const SIGNIFICANCIAS: SignificanciaAislado[] = [
  'NO_DEFINIDA',
  'CONTAMINANTE',
  'FLORA_HABITUAL',
  'SIGNIFICATIVO',
  'CRITICO',
];

export interface AisladosIdentificacionPanelProps {
  estudioId: number;
  lecturas: LecturaCultivo[];
  aislados: AisladoMicrobiologico[];
  identificaciones: IdentificacionMicroorganismo[];
  microorganismos: Microorganismo[];
  canOperate: boolean;
  onRefresh: () => void;
}

function labelMicroorganismo(m: Microorganismo): string {
  const code = (m.codigo || '').trim();
  const name = (m.nombre || '').trim();
  if (code && name) return `${code} — ${name}`;
  return name || code || `Micro #${m.id}`;
}

function microMatchesQuery(m: Microorganismo, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const haystack = [m.codigo, m.nombre, m.genero, m.especie, m.grupo]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return haystack.includes(q);
}

const AisladosIdentificacionPanel: React.FC<AisladosIdentificacionPanelProps> = ({
  estudioId,
  lecturas,
  aislados,
  identificaciones,
  microorganismos,
  canOperate,
  onRefresh,
}) => {
  const [lecturaId, setLecturaId] = useState<number | ''>('');
  const [microSeleccionado, setMicroSeleccionado] = useState<Microorganismo | null>(null);
  const [hallazgoLibre, setHallazgoLibre] = useState('');
  const [metodo, setMetodo] = useState('');
  const [requiereAb, setRequiereAb] = useState(true);
  const [saving, setSaving] = useState(false);
  const { openMotivoDialog, dialogProps } = useMotivoDialog();

  const [editAislado, setEditAislado] = useState<AisladoMicrobiologico | null>(null);
  const [editAisladoForm, setEditAisladoForm] = useState({
    descripcion: '',
    cantidad: '',
    significancia: 'NO_DEFINIDA' as SignificanciaAislado | string,
    requiere_antibiograma: false,
    observaciones: '',
  });
  const [editIdent, setEditIdent] = useState<IdentificacionMicroorganismo | null>(null);
  const [editIdentMicro, setEditIdentMicro] = useState<Microorganismo | null>(null);
  const [editIdentForm, setEditIdentForm] = useState({ metodo: '', resultado: '', observaciones: '' });
  const [editSaving, setEditSaving] = useState(false);

  const microsActivos = useMemo(
    () => microorganismos.filter((m) => m.activo !== false),
    [microorganismos],
  );

  const microById = useMemo(() => {
    const map = new Map<number, Microorganismo>();
    for (const m of microorganismos) map.set(m.id, m);
    return map;
  }, [microorganismos]);

  const identPorAislado = useMemo(() => {
    const map = new Map<number, IdentificacionMicroorganismo>();
    const ordered = [...identificaciones].sort((a, b) => {
      const ta = a.fecha || a.created_at || '';
      const tb = b.fecha || b.created_at || '';
      return tb.localeCompare(ta);
    });
    for (const i of ordered) {
      if (!map.has(i.aislado)) map.set(i.aislado, i);
    }
    return map;
  }, [identificaciones]);

  const nombreMicroDeAislado = (a: AisladoMicrobiologico): string => {
    const ident = identPorAislado.get(a.id);
    const microId = ident?.microorganismo ?? a.microorganismo ?? null;
    if (microId) {
      const m = microById.get(microId);
      return m ? labelMicroorganismo(m) : String(microId);
    }
    const libre = (a.descripcion || '').trim();
    return libre ? `Libre: ${libre}` : '—';
  };

  const registrar = async () => {
    if (lecturaId === '') {
      toast.error('Seleccione lectura de origen');
      return;
    }
    const libre = hallazgoLibre.trim();
    if (!microSeleccionado && !libre) {
      toast.error('Seleccione microorganismo del catálogo o escriba un hallazgo libre');
      return;
    }
    setSaving(true);
    try {
      if (microSeleccionado) {
        const aislado = await createAisladoMicrobiologico({
          estudio_id: estudioId,
          lectura_id: Number(lecturaId),
          microorganismo_id: microSeleccionado.id,
          descripcion: libre || undefined,
          requiere_antibiograma: requiereAb,
        });
        await createIdentificacionMicroorganismo({
          aislado_id: aislado.id,
          microorganismo_id: microSeleccionado.id,
          metodo: metodo.trim() || undefined,
        });
        toast.success('Aislado e identificación registrados');
      } else {
        await createAisladoMicrobiologico({
          estudio_id: estudioId,
          lectura_id: Number(lecturaId),
          descripcion: libre,
          requiere_antibiograma: false,
        });
        toast.success('Aislado con hallazgo libre (sin identificación formal)');
      }
      setLecturaId('');
      setMicroSeleccionado(null);
      setHallazgoLibre('');
      setMetodo('');
      setRequiereAb(true);
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarAislado));
    } finally {
      setSaving(false);
    }
  };

  const descartar = (id: number) => {
    openMotivoDialog({
      title: 'Descartar aislado',
      label: 'Motivo de descarte (obligatorio)',
      confirmLabel: 'Descartar',
      onConfirm: async (motivo) => {
        try {
          await descartarAisladoMicrobiologico(id, motivo);
          toast.success('Aislado descartado');
          onRefresh();
        } catch (e) {
          const msg = getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsDescartarAislado);
          toast.error(msg);
          throw new Error(msg);
        }
      },
    });
  };

  const eliminarAislado = async (a: AisladoMicrobiologico) => {
    if (
      !window.confirm(
        `¿Eliminar aislado #${a.id}? También se eliminarán identificaciones, antibiogramas y resultados asociados. Esta acción no se puede deshacer.`
      )
    ) {
      return;
    }
    try {
      await deleteAisladoMicrobiologico(a.id);
      toast.success('Aislado eliminado');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsEliminarRegistroMicro));
    }
  };

  const eliminarIdentificacion = async (ident: IdentificacionMicroorganismo) => {
    if (
      !window.confirm(
        `¿Eliminar identificación #${ident.id}? Esta acción no se puede deshacer.`
      )
    ) {
      return;
    }
    try {
      await deleteIdentificacionMicroorganismo(ident.id);
      toast.success('Identificación eliminada');
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsEliminarRegistroMicro));
    }
  };

  const openEditarAislado = (a: AisladoMicrobiologico) => {
    setEditAislado(a);
    setEditAisladoForm({
      descripcion: a.descripcion || '',
      cantidad: a.cantidad || '',
      significancia: a.significancia || 'NO_DEFINIDA',
      requiere_antibiograma: Boolean(a.requiere_antibiograma),
      observaciones: a.observaciones || '',
    });
  };

  const guardarAislado = async () => {
    if (!editAislado) return;
    setEditSaving(true);
    try {
      await updateAisladoMicrobiologico(editAislado.id, {
        descripcion: editAisladoForm.descripcion,
        cantidad: editAisladoForm.cantidad,
        significancia: editAisladoForm.significancia,
        requiere_antibiograma: editAisladoForm.requiere_antibiograma,
        observaciones: editAisladoForm.observaciones,
      });
      toast.success('Aislado actualizado');
      setEditAislado(null);
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsGuardarAislado));
    } finally {
      setEditSaving(false);
    }
  };

  const openEditarIdent = (ident: IdentificacionMicroorganismo) => {
    setEditIdent(ident);
    setEditIdentMicro(microById.get(ident.microorganismo) || null);
    setEditIdentForm({
      metodo: ident.metodo || '',
      resultado: ident.resultado || '',
      observaciones: ident.observaciones || '',
    });
  };

  const guardarIdent = async () => {
    if (!editIdent) return;
    if (!editIdentMicro) {
      toast.error('Seleccione microorganismo');
      return;
    }
    setEditSaving(true);
    try {
      await updateIdentificacionMicroorganismo(editIdent.id, {
        microorganismo_id: editIdentMicro.id,
        metodo: editIdentForm.metodo,
        resultado: editIdentForm.resultado,
        observaciones: editIdentForm.observaciones,
      });
      toast.success('Identificación actualizada');
      setEditIdent(null);
      onRefresh();
    } catch (e) {
      toast.error(getSafeClinicalActionMessage(e, CLINICAL_ACTION_ERRORS.limsActualizarIdentificacion));
    } finally {
      setEditSaving(false);
    }
  };

  return (
    <Box>
      <Typography variant="subtitle1" gutterBottom>
        Aislados e identificación
      </Typography>

      {canOperate && todasLecturasSinDesarrollo(lecturas) && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Todas las lecturas son <strong>sin desarrollo</strong>: no hace falta aislar ni hacer
          antibiograma. Pasá a la pestaña <strong>Informes</strong> para emitir el informe final
          («No se obtuvo desarrollo bacteriano»).
        </Alert>
      )}

      {canOperate && !todasLecturasSinDesarrollo(lecturas) && (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Nuevo aislado e identificación
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2, alignItems: 'flex-start' }}>
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel>Lectura</InputLabel>
              <Select
                label="Lectura"
                value={lecturaId === '' ? '' : String(lecturaId)}
                onChange={(e) => setLecturaId(e.target.value === '' ? '' : Number(e.target.value))}
              >
                <MenuItem value="">—</MenuItem>
                {lecturas.map((l) => (
                  <MenuItem key={l.id} value={l.id}>
                    #{l.id} · {l.crecimiento || '—'}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Autocomplete
              size="small"
              sx={{ minWidth: 280, flex: '1 1 240px' }}
              options={microsActivos}
              value={microSeleccionado}
              onChange={(_e, value) => setMicroSeleccionado(value)}
              getOptionLabel={(m) => labelMicroorganismo(m)}
              isOptionEqualToValue={(a, b) => a.id === b.id}
              filterOptions={(options, state) =>
                options.filter((m) => microMatchesQuery(m, state.inputValue))
              }
              noOptionsText="Sin coincidencias — use hallazgo libre"
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Microorganismo (catálogo)"
                  placeholder="Buscar por código o nombre"
                />
              )}
            />
            <TextField
              size="small"
              label="Hallazgo libre"
              placeholder="Si el catálogo no cubre el hallazgo"
              value={hallazgoLibre}
              onChange={(e) => setHallazgoLibre(e.target.value)}
              sx={{ minWidth: 220, flex: '1 1 200px' }}
            />

            <TextField
              size="small"
              label="Método (opc.)"
              value={metodo}
              onChange={(e) => setMetodo(e.target.value)}
              sx={{ minWidth: 140 }}
            />

            <FormControlLabel
              control={
                <Checkbox
                  checked={requiereAb}
                  onChange={(e) => setRequiereAb(e.target.checked)}
                />
              }
              label="Requiere AB"
            />

            <Button
              variant="contained"
              onClick={registrar}
              disabled={saving || lecturas.length === 0}
            >
              Registrar
            </Button>
          </Box>
          {lecturas.length === 0 && (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              Primero registrá al menos una lectura de cultivo.
            </Typography>
          )}
        </Paper>
      )}

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Lectura</TableCell>
              <TableCell>Estado</TableCell>
              <TableCell>Microorganismo</TableCell>
              <TableCell>Método</TableCell>
              <TableCell>Significancia</TableCell>
              <TableCell>AB</TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {aislados.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8}>
                  <Typography color="text.secondary">Sin aislados.</Typography>
                </TableCell>
              </TableRow>
            ) : (
              aislados.map((a) => {
                const ident = identPorAislado.get(a.id);
                return (
                  <TableRow key={a.id}>
                    <TableCell>{a.id}</TableCell>
                    <TableCell>{a.lectura_origen}</TableCell>
                    <TableCell>
                      <AisladoEstadoBadge estado={a.estado} />
                    </TableCell>
                    <TableCell>{nombreMicroDeAislado(a)}</TableCell>
                    <TableCell>{ident?.metodo || '—'}</TableCell>
                    <TableCell>{a.significancia}</TableCell>
                    <TableCell>{a.requiere_antibiograma ? 'Sí' : 'No'}</TableCell>
                    <TableCell sx={{ whiteSpace: 'nowrap' }}>
                      {canOperate && a.estado !== 'DESCARTADO' && (
                        <Button size="small" onClick={() => openEditarAislado(a)}>
                          Editar
                        </Button>
                      )}
                      {canOperate && ident && a.estado !== 'DESCARTADO' && (
                        <Button size="small" onClick={() => openEditarIdent(ident)}>
                          Editar ID
                        </Button>
                      )}
                      {canOperate && ident && (
                        <Button size="small" color="error" onClick={() => eliminarIdentificacion(ident)}>
                          Eliminar ID
                        </Button>
                      )}
                      {canOperate && (
                        <Button size="small" color="error" onClick={() => eliminarAislado(a)}>
                          Eliminar
                        </Button>
                      )}
                      {canOperate && a.estado !== 'DESCARTADO' && (
                        <Button size="small" color="warning" onClick={() => descartar(a.id)}>
                          Descartar
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog open={Boolean(editAislado)} onClose={() => setEditAislado(null)} fullWidth maxWidth="sm">
        <DialogTitle>Editar aislado #{editAislado?.id}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <TextField
              size="small"
              label="Descripción / hallazgo"
              fullWidth
              multiline
              minRows={2}
              value={editAisladoForm.descripcion}
              onChange={(e) => setEditAisladoForm((f) => ({ ...f, descripcion: e.target.value }))}
            />
            <TextField
              size="small"
              label="Cantidad"
              value={editAisladoForm.cantidad}
              onChange={(e) => setEditAisladoForm((f) => ({ ...f, cantidad: e.target.value }))}
            />
            <FormControl size="small" fullWidth>
              <InputLabel>Significancia</InputLabel>
              <Select
                label="Significancia"
                value={editAisladoForm.significancia}
                onChange={(e) =>
                  setEditAisladoForm((f) => ({ ...f, significancia: e.target.value }))
                }
              >
                {SIGNIFICANCIAS.map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControlLabel
              control={
                <Checkbox
                  checked={editAisladoForm.requiere_antibiograma}
                  onChange={(e) =>
                    setEditAisladoForm((f) => ({ ...f, requiere_antibiograma: e.target.checked }))
                  }
                />
              }
              label="Requiere antibiograma"
            />
            <TextField
              size="small"
              label="Observaciones"
              fullWidth
              multiline
              minRows={2}
              value={editAisladoForm.observaciones}
              onChange={(e) => setEditAisladoForm((f) => ({ ...f, observaciones: e.target.value }))}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditAislado(null)}>Cancelar</Button>
          <Button variant="contained" onClick={guardarAislado} disabled={editSaving}>
            Guardar
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(editIdent)} onClose={() => setEditIdent(null)} fullWidth maxWidth="sm">
        <DialogTitle>Editar identificación #{editIdent?.id}</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
            <Autocomplete
              size="small"
              options={microsActivos}
              value={editIdentMicro}
              onChange={(_e, value) => setEditIdentMicro(value)}
              getOptionLabel={(m) => labelMicroorganismo(m)}
              isOptionEqualToValue={(a, b) => a.id === b.id}
              filterOptions={(options, state) =>
                options.filter((m) => microMatchesQuery(m, state.inputValue))
              }
              renderInput={(params) => (
                <TextField {...params} label="Microorganismo *" />
              )}
            />
            <TextField
              size="small"
              label="Método"
              value={editIdentForm.metodo}
              onChange={(e) => setEditIdentForm((f) => ({ ...f, metodo: e.target.value }))}
            />
            <TextField
              size="small"
              label="Resultado"
              fullWidth
              multiline
              minRows={2}
              value={editIdentForm.resultado}
              onChange={(e) => setEditIdentForm((f) => ({ ...f, resultado: e.target.value }))}
            />
            <TextField
              size="small"
              label="Observaciones"
              fullWidth
              multiline
              minRows={2}
              value={editIdentForm.observaciones}
              onChange={(e) => setEditIdentForm((f) => ({ ...f, observaciones: e.target.value }))}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditIdent(null)}>Cancelar</Button>
          <Button variant="contained" onClick={guardarIdent} disabled={editSaving}>
            Guardar
          </Button>
        </DialogActions>
      </Dialog>

      <MotivoDialog {...dialogProps} />
    </Box>
  );
};

export default AisladosIdentificacionPanel;
