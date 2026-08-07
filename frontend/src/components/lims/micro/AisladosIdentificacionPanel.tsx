import React, { useMemo, useState } from 'react';
import {
  Autocomplete,
  Box,
  Button,
  Checkbox,
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
} from '../../../types/lims';
import {
  createAisladoMicrobiologico,
  createIdentificacionMicroorganismo,
  descartarAisladoMicrobiologico,
} from '../../../services/limsApi';
import { CLINICAL_ACTION_ERRORS, getSafeClinicalActionMessage } from '../../../utils/apiError';
import { AisladoEstadoBadge } from './MicroBadges';
import { MotivoDialog, useMotivoDialog } from './MotivoDialog';

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
  const [metodo, setMetodo] = useState('');
  const [requiereAb, setRequiereAb] = useState(true);
  const [saving, setSaving] = useState(false);
  const { openMotivoDialog, dialogProps } = useMotivoDialog();

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
    if (!microId) return '—';
    const m = microById.get(microId);
    return m ? labelMicroorganismo(m) : String(microId);
  };

  const registrar = async () => {
    if (lecturaId === '') {
      toast.error('Seleccione lectura de origen');
      return;
    }
    if (!microSeleccionado) {
      toast.error('Seleccione el microorganismo identificado');
      return;
    }
    setSaving(true);
    try {
      const aislado = await createAisladoMicrobiologico({
        estudio_id: estudioId,
        lectura_id: Number(lecturaId),
        microorganismo_id: microSeleccionado.id,
        requiere_antibiograma: requiereAb,
      });
      await createIdentificacionMicroorganismo({
        aislado_id: aislado.id,
        microorganismo_id: microSeleccionado.id,
        metodo: metodo.trim() || undefined,
      });
      toast.success('Aislado e identificación registrados');
      setLecturaId('');
      setMicroSeleccionado(null);
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

  return (
    <Box>
      <Typography variant="subtitle1" gutterBottom>
        Aislados e identificación
      </Typography>

      {canOperate && (
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
              noOptionsText="Sin coincidencias"
              renderInput={(params) => (
                <TextField
                  {...params}
                  label="Microorganismo *"
                  placeholder="Buscar por código o nombre"
                />
              )}
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
                    <TableCell>
                      {canOperate && a.estado !== 'DESCARTADO' && (
                        <Button size="small" color="error" onClick={() => descartar(a.id)}>
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

      <MotivoDialog {...dialogProps} />
    </Box>
  );
};

export default AisladosIdentificacionPanel;
