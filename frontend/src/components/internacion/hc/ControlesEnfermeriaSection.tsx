import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { createHcResource, listHcResource } from '../../../services/internacion';
import {
  ControlEnfermeriaRow,
  TURNO_OPTIONS,
  Turno,
  formatFechaHc,
  toDecHc,
  toIntHc,
} from './hcInternacionUtils';

interface ControlesEnfermeriaSectionProps {
  internacionId: number;
  canEdit: boolean;
  historialLimit?: number;
  onSaved?: () => void;
}

const emptyForm = {
  turno: 'MANANA' as Turno,
  tension_arterial: '',
  frecuencia_cardiaca: '',
  frecuencia_respiratoria: '',
  temperatura: '',
  saturacion_oxigeno: '',
  dolor: '',
  glucemia: '',
  observaciones: '',
};

const ControlesEnfermeriaSection: React.FC<ControlesEnfermeriaSectionProps> = ({
  internacionId,
  canEdit,
  historialLimit,
  onSaved,
}) => {
  const [rows, setRows] = useState<ControlEnfermeriaRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listHcResource<ControlEnfermeriaRow>(
        internacionId,
        'controles-enfermeria',
      );
      setRows(data);
    } catch {
      setError('No se pudieron cargar los controles.');
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
      await createHcResource(internacionId, 'controles-enfermeria', {
        turno: form.turno,
        tension_arterial: form.tension_arterial,
        frecuencia_cardiaca: toIntHc(form.frecuencia_cardiaca),
        frecuencia_respiratoria: toIntHc(form.frecuencia_respiratoria),
        temperatura: toDecHc(form.temperatura),
        saturacion_oxigeno: toDecHc(form.saturacion_oxigeno),
        dolor: toIntHc(form.dolor),
        glucemia: toIntHc(form.glucemia),
        observaciones: form.observaciones,
      });
      setForm(emptyForm);
      await load();
      onSaved?.();
    } catch {
      setError('No se pudo registrar el control.');
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
          Cargando controles…
        </Typography>
      ) : (
        <>
          {visibleRows.map((row) => (
            <Box key={row.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1 }}>
              <Typography variant="caption" color="text.secondary">
                {formatFechaHc(row.fecha)} · {row.turno} · {row.registrado_por_nombre || '—'}
              </Typography>
              <Typography variant="body2">
                TA {row.tension_arterial || '—'} · FC {row.frecuencia_cardiaca ?? '—'} · FR{' '}
                {row.frecuencia_respiratoria ?? '—'} · T {row.temperatura ?? '—'} · SpO2{' '}
                {row.saturacion_oxigeno ?? '—'} · dolor {row.dolor ?? '—'} · glucemia{' '}
                {row.glucemia ?? '—'}
              </Typography>
              {row.observaciones && (
                <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                  {row.observaciones}
                </Typography>
              )}
            </Box>
          ))}
          {!visibleRows.length && (
            <Typography variant="body2" color="text.secondary">
              Sin controles registrados en este episodio.
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
          <TextField
            select
            label="Turno"
            value={form.turno}
            onChange={(e) => setForm({ ...form, turno: e.target.value as Turno })}
            size="small"
          >
            {TURNO_OPTIONS.map((opt) => (
              <MenuItem key={opt.value} value={opt.value}>
                {opt.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Tensión arterial"
            value={form.tension_arterial}
            onChange={(e) => setForm({ ...form, tension_arterial: e.target.value })}
            size="small"
          />
          <Stack direction="row" spacing={1}>
            <TextField
              label="FC"
              value={form.frecuencia_cardiaca}
              onChange={(e) => setForm({ ...form, frecuencia_cardiaca: e.target.value })}
              size="small"
              fullWidth
            />
            <TextField
              label="FR"
              value={form.frecuencia_respiratoria}
              onChange={(e) => setForm({ ...form, frecuencia_respiratoria: e.target.value })}
              size="small"
              fullWidth
            />
          </Stack>
          <Stack direction="row" spacing={1}>
            <TextField
              label="Temperatura"
              value={form.temperatura}
              onChange={(e) => setForm({ ...form, temperatura: e.target.value })}
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
          <Stack direction="row" spacing={1}>
            <TextField
              label="Dolor (0-10)"
              value={form.dolor}
              onChange={(e) => setForm({ ...form, dolor: e.target.value })}
              size="small"
              fullWidth
            />
            <TextField
              label="Glucemia"
              value={form.glucemia}
              onChange={(e) => setForm({ ...form, glucemia: e.target.value })}
              size="small"
              fullWidth
            />
          </Stack>
          <TextField
            label="Observaciones"
            value={form.observaciones}
            onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
            multiline
            size="small"
          />
          <Button variant="outlined" disabled={saving} onClick={() => void handleSave()}>
            Registrar control
          </Button>
        </Stack>
      )}
    </Stack>
  );
};

export default ControlesEnfermeriaSection;
