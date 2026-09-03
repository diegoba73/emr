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
import { NotaEnfermeriaRow, formatFechaHc } from './hcInternacionUtils';

interface NotaEnfermeriaSectionProps {
  internacionId: number;
  canEdit: boolean;
  historialLimit?: number;
  onSaved?: () => void;
}

const emptyForm = { observaciones: '', curaciones: '', dispositivos: '' };

const NotaEnfermeriaSection: React.FC<NotaEnfermeriaSectionProps> = ({
  internacionId,
  canEdit,
  historialLimit,
  onSaved,
}) => {
  const [rows, setRows] = useState<NotaEnfermeriaRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listHcResource<NotaEnfermeriaRow>(
        internacionId,
        'notas-enfermeria',
      );
      setRows(data);
    } catch {
      setError('No se pudieron cargar las notas.');
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
      await createHcResource(internacionId, 'notas-enfermeria', form);
      setForm(emptyForm);
      await load();
      onSaved?.();
    } catch {
      setError('No se pudo guardar la nota.');
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
          Cargando notas…
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
                  row.observaciones,
                  row.curaciones && `Curaciones: ${row.curaciones}`,
                  row.dispositivos && `Dispositivos: ${row.dispositivos}`,
                ]
                  .filter(Boolean)
                  .join('\n')}
              </Typography>
            </Box>
          ))}
          {!visibleRows.length && (
            <Typography variant="body2" color="text.secondary">
              Sin notas de enfermería en este episodio.
            </Typography>
          )}
          {historialLimit != null && rows.length > historialLimit && (
            <Typography variant="caption" color="text.secondary">
              Mostrando las últimas {historialLimit} de {rows.length}.
            </Typography>
          )}
        </>
      )}
      {canEdit && (
        <Stack spacing={1}>
          <TextField
            label="Observaciones"
            value={form.observaciones}
            onChange={(e) => setForm({ ...form, observaciones: e.target.value })}
            multiline
            size="small"
          />
          <TextField
            label="Curaciones"
            value={form.curaciones}
            onChange={(e) => setForm({ ...form, curaciones: e.target.value })}
            multiline
            size="small"
          />
          <TextField
            label="Dispositivos (SV, acceso, O2, SNG…)"
            value={form.dispositivos}
            onChange={(e) => setForm({ ...form, dispositivos: e.target.value })}
            multiline
            size="small"
          />
          <Button variant="outlined" disabled={saving} onClick={() => void handleSave()}>
            Agregar nota de enfermería
          </Button>
        </Stack>
      )}
    </Stack>
  );
};

export default NotaEnfermeriaSection;
