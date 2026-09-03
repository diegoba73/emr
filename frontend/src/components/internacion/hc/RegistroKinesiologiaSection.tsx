import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { createHcResource, listHcResource } from '../../../services/internacion';
import {
  RegistroKinesiologiaRow,
  formatFechaHc,
  toDecHc,
  toIntHc,
} from './hcInternacionUtils';

interface RegistroKinesiologiaSectionProps {
  internacionId: number;
  canEdit: boolean;
  historialLimit?: number;
  onSaved?: () => void;
}

const emptyForm = {
  frecuencia_respiratoria: '',
  saturacion_oxigeno: '',
  oxigenoterapia: '',
  secreciones: '',
  tecnica: '',
  movilizacion: '',
  evolucion: '',
  plan: '',
};

const RegistroKinesiologiaSection: React.FC<RegistroKinesiologiaSectionProps> = ({
  internacionId,
  canEdit,
  historialLimit,
  onSaved,
}) => {
  const [rows, setRows] = useState<RegistroKinesiologiaRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listHcResource<RegistroKinesiologiaRow>(
        internacionId,
        'kinesiologia',
      );
      setRows(data);
    } catch {
      setError('No se pudo cargar kinesiología.');
    } finally {
      setLoading(false);
    }
  }, [internacionId]);

  useEffect(() => {
    void load();
  }, [load]);

  const visibleRows =
    historialLimit != null ? rows.slice(0, historialLimit) : rows;

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await createHcResource(internacionId, 'kinesiologia', {
        frecuencia_respiratoria: toIntHc(form.frecuencia_respiratoria),
        saturacion_oxigeno: toDecHc(form.saturacion_oxigeno),
        oxigenoterapia: form.oxigenoterapia,
        secreciones: form.secreciones,
        tecnica: form.tecnica,
        movilizacion: form.movilizacion,
        evolucion: form.evolucion,
        plan: form.plan,
      });
      setForm(emptyForm);
      await load();
      onSaved?.();
    } catch {
      setError('No se pudo registrar kinesiología.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Stack spacing={1.5}>
      {error && (
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {loading ? (
        <Typography variant="body2" color="text.secondary">
          Cargando registros…
        </Typography>
      ) : (
        <>
          {visibleRows.map((row) => (
            <Box key={row.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1 }}>
              <Typography variant="caption" color="text.secondary">
                {formatFechaHc(row.fecha)} · {row.registrado_por_nombre || '—'}
              </Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                {[
                  row.frecuencia_respiratoria != null && `FR ${row.frecuencia_respiratoria}`,
                  row.saturacion_oxigeno != null && `SpO2 ${row.saturacion_oxigeno}`,
                  row.oxigenoterapia && `O2 ${row.oxigenoterapia}`,
                  row.secreciones && `Secreciones: ${row.secreciones}`,
                  row.tecnica,
                  row.movilizacion && `Movilización: ${row.movilizacion}`,
                  row.evolucion,
                  row.plan && `Plan: ${row.plan}`,
                ]
                  .filter(Boolean)
                  .join('\n')}
              </Typography>
            </Box>
          ))}
          {!visibleRows.length && (
            <Typography variant="body2" color="text.secondary">
              Sin registros de kinesiología en este episodio.
            </Typography>
          )}
          {historialLimit != null && rows.length > historialLimit && (
            <Typography variant="caption" color="text.secondary">
              Mostrando los últimos {historialLimit} de {rows.length}.
            </Typography>
          )}
        </>
      )}
      {canEdit && (
        <Stack spacing={1}>
          <Stack direction="row" spacing={1}>
            <TextField
              label="FR"
              value={form.frecuencia_respiratoria}
              onChange={(e) => setForm({ ...form, frecuencia_respiratoria: e.target.value })}
              size="small"
              fullWidth
            />
            <TextField
              label="SpO2"
              value={form.saturacion_oxigeno}
              onChange={(e) => setForm({ ...form, saturacion_oxigeno: e.target.value })}
              size="small"
              fullWidth
            />
          </Stack>
          <TextField
            label="Oxigenoterapia"
            value={form.oxigenoterapia}
            onChange={(e) => setForm({ ...form, oxigenoterapia: e.target.value })}
            size="small"
          />
          <TextField
            label="Secreciones"
            value={form.secreciones}
            onChange={(e) => setForm({ ...form, secreciones: e.target.value })}
            size="small"
          />
          <TextField
            label="Técnica"
            value={form.tecnica}
            onChange={(e) => setForm({ ...form, tecnica: e.target.value })}
            multiline
            size="small"
          />
          <TextField
            label="Movilización"
            value={form.movilizacion}
            onChange={(e) => setForm({ ...form, movilizacion: e.target.value })}
            size="small"
          />
          <TextField
            label="Evolución"
            value={form.evolucion}
            onChange={(e) => setForm({ ...form, evolucion: e.target.value })}
            multiline
            size="small"
          />
          <TextField
            label="Plan"
            value={form.plan}
            onChange={(e) => setForm({ ...form, plan: e.target.value })}
            multiline
            size="small"
          />
          <Button variant="outlined" disabled={saving} onClick={() => void handleSave()}>
            Registrar kinesiología
          </Button>
        </Stack>
      )}
    </Stack>
  );
};

export default RegistroKinesiologiaSection;
