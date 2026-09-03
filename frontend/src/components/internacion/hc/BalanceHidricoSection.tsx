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
  BalanceHidricoRow,
  TURNO_OPTIONS,
  Turno,
  formatFechaHc,
  toIntHc,
} from './hcInternacionUtils';

interface BalanceHidricoSectionProps {
  internacionId: number;
  canEdit: boolean;
  historialLimit?: number;
  onSaved?: () => void;
}

const emptyForm = {
  turno: 'MANANA' as Turno,
  ingresos_vo_ml: '',
  ingresos_ev_ml: '',
  diuresis_ml: '',
  otros_egresos_ml: '',
  observaciones: '',
};

const BalanceHidricoSection: React.FC<BalanceHidricoSectionProps> = ({
  internacionId,
  canEdit,
  historialLimit,
  onSaved,
}) => {
  const [rows, setRows] = useState<BalanceHidricoRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listHcResource<BalanceHidricoRow>(
        internacionId,
        'balances-hidricos',
      );
      setRows(data);
    } catch {
      setError('No se pudo cargar el balance hídrico.');
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
      await createHcResource(internacionId, 'balances-hidricos', {
        turno: form.turno,
        ingresos_vo_ml: toIntHc(form.ingresos_vo_ml),
        ingresos_ev_ml: toIntHc(form.ingresos_ev_ml),
        diuresis_ml: toIntHc(form.diuresis_ml),
        otros_egresos_ml: toIntHc(form.otros_egresos_ml),
        observaciones: form.observaciones,
      });
      setForm(emptyForm);
      await load();
      onSaved?.();
    } catch {
      setError('No se pudo registrar el balance.');
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
          Cargando balances…
        </Typography>
      ) : (
        <>
          {visibleRows.map((row) => (
            <Box key={row.id} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1 }}>
              <Typography variant="caption" color="text.secondary">
                {formatFechaHc(row.fecha)} · {row.turno}
              </Typography>
              <Typography variant="body2">
                VO {row.ingresos_vo_ml ?? '—'} / EV {row.ingresos_ev_ml ?? '—'} · diuresis{' '}
                {row.diuresis_ml ?? '—'} · otros egresos {row.otros_egresos_ml ?? '—'}
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
              Sin balances registrados en este episodio.
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
          <Stack direction="row" spacing={1}>
            <TextField
              label="Ingresos VO (ml)"
              value={form.ingresos_vo_ml}
              onChange={(e) => setForm({ ...form, ingresos_vo_ml: e.target.value })}
              size="small"
              fullWidth
            />
            <TextField
              label="Ingresos EV (ml)"
              value={form.ingresos_ev_ml}
              onChange={(e) => setForm({ ...form, ingresos_ev_ml: e.target.value })}
              size="small"
              fullWidth
            />
          </Stack>
          <Stack direction="row" spacing={1}>
            <TextField
              label="Diuresis (ml)"
              value={form.diuresis_ml}
              onChange={(e) => setForm({ ...form, diuresis_ml: e.target.value })}
              size="small"
              fullWidth
            />
            <TextField
              label="Otros egresos (ml)"
              value={form.otros_egresos_ml}
              onChange={(e) => setForm({ ...form, otros_egresos_ml: e.target.value })}
              size="small"
              fullWidth
            />
          </Stack>
          <TextField
            label="Observaciones"
            value={form.observaciones}
            onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
            size="small"
          />
          <Button variant="outlined" disabled={saving} onClick={() => void handleSave()}>
            Registrar balance
          </Button>
        </Stack>
      )}
    </Stack>
  );
};

export default BalanceHidricoSection;
