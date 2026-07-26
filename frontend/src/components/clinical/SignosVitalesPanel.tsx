import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Divider,
  Stack,
  TextField,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from '@mui/material';
import toast from 'react-hot-toast';
import { apiService } from '../../services/api';
import type { SignosVitales } from '../../types';

interface SignosVitalesPanelProps {
  atencionId: number;
  canEdit: boolean;
  initialItems?: SignosVitales[];
  compact?: boolean;
  onSaved?: (item: SignosVitales) => void;
}

const emptyForm = {
  tension_arterial: '',
  frecuencia_cardiaca: '',
  frecuencia_respiratoria: '',
  temperatura: '',
  saturacion_oxigeno: '',
  peso: '',
  talla: '',
};

function formatSv(sv: SignosVitales): string {
  const parts: string[] = [];
  if (sv.tension_arterial) parts.push(`TA ${sv.tension_arterial}`);
  if (sv.frecuencia_cardiaca != null) parts.push(`FC ${sv.frecuencia_cardiaca}`);
  if (sv.frecuencia_respiratoria != null) parts.push(`FR ${sv.frecuencia_respiratoria}`);
  if (sv.temperatura != null) parts.push(`T ${sv.temperatura}°C`);
  if (sv.saturacion_oxigeno != null) parts.push(`SpO₂ ${sv.saturacion_oxigeno}%`);
  if (sv.peso != null) parts.push(`${sv.peso} kg`);
  return parts.join(' · ') || '—';
}

const SignosVitalesPanel: React.FC<SignosVitalesPanelProps> = ({
  atencionId,
  canEdit,
  initialItems,
  compact = false,
  onSaved,
}) => {
  const [items, setItems] = useState<SignosVitales[]>(initialItems || []);
  const [loading, setLoading] = useState(!initialItems);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiService.getSignosVitales({ atencion: atencionId });
      setItems(data);
    } catch {
      if (!initialItems) setItems([]);
    } finally {
      setLoading(false);
    }
  }, [atencionId, initialItems]);

  useEffect(() => {
    if (initialItems) {
      setItems(initialItems);
      setLoading(false);
      return;
    }
    load();
  }, [initialItems, load]);

  const handleChange =
    (field: keyof typeof emptyForm) => (e: React.ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: e.target.value }));
    };

  const handleSubmit = async (e?: React.MouseEvent | React.FormEvent) => {
    e?.preventDefault?.();
    e?.stopPropagation?.();
    if (!canEdit) return;
    setSaving(true);
    try {
      const payload: Record<string, unknown> = { atencion_id: atencionId };
      if (form.tension_arterial.trim()) payload.tension_arterial = form.tension_arterial.trim();
      if (form.frecuencia_cardiaca) payload.frecuencia_cardiaca = Number(form.frecuencia_cardiaca);
      if (form.frecuencia_respiratoria) {
        payload.frecuencia_respiratoria = Number(form.frecuencia_respiratoria);
      }
      if (form.temperatura) payload.temperatura = Number(form.temperatura);
      if (form.saturacion_oxigeno) payload.saturacion_oxigeno = Number(form.saturacion_oxigeno);
      if (form.peso) payload.peso = Number(form.peso);
      if (form.talla) payload.talla = Number(form.talla);
      if (form.peso && form.talla) {
        const talla = Number(form.talla);
        if (talla > 0) {
          payload.indice_masa_corporal = Number(
            (Number(form.peso) / (talla * talla)).toFixed(2),
          );
        }
      }
      const created = await apiService.createSignosVitales(payload);
      setForm(emptyForm);
      setItems((prev) => [created, ...prev]);
      toast.success('Signos vitales registrados');
      onSaved?.(created);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'No se pudieron guardar los signos vitales';
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" py={2}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant={compact ? 'subtitle2' : 'subtitle1'} fontWeight={600} sx={{ mb: 1 }}>
        Signos vitales
      </Typography>

      {canEdit && (
        <Box
          sx={{ mb: 2 }}
          onKeyDown={(e) => {
            // Evitar que Enter envíe el form padre (consulta / evolución).
            if (e.key === 'Enter') {
              e.preventDefault();
              e.stopPropagation();
              void handleSubmit(e);
            }
          }}
        >
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} useFlexGap flexWrap="wrap">
            <TextField
              label="TA"
              size="small"
              placeholder="120/80"
              value={form.tension_arterial}
              onChange={handleChange('tension_arterial')}
              sx={{ width: { sm: 110 } }}
            />
            <TextField
              label="FC"
              size="small"
              type="number"
              value={form.frecuencia_cardiaca}
              onChange={handleChange('frecuencia_cardiaca')}
              sx={{ width: { sm: 90 } }}
            />
            <TextField
              label="FR"
              size="small"
              type="number"
              value={form.frecuencia_respiratoria}
              onChange={handleChange('frecuencia_respiratoria')}
              sx={{ width: { sm: 90 } }}
            />
            <TextField
              label="T °C"
              size="small"
              type="number"
              inputProps={{ step: 0.1 }}
              value={form.temperatura}
              onChange={handleChange('temperatura')}
              sx={{ width: { sm: 90 } }}
            />
            <TextField
              label="SpO₂ %"
              size="small"
              type="number"
              inputProps={{ step: 0.1 }}
              value={form.saturacion_oxigeno}
              onChange={handleChange('saturacion_oxigeno')}
              sx={{ width: { sm: 100 } }}
            />
            <TextField
              label="Peso kg"
              size="small"
              type="number"
              inputProps={{ step: 0.01 }}
              value={form.peso}
              onChange={handleChange('peso')}
              sx={{ width: { sm: 100 } }}
            />
            <TextField
              label="Talla m"
              size="small"
              type="number"
              inputProps={{ step: 0.01 }}
              value={form.talla}
              onChange={handleChange('talla')}
              sx={{ width: { sm: 100 } }}
            />
            <Button
              type="button"
              variant="contained"
              disabled={saving}
              onClick={(e) => void handleSubmit(e)}
              sx={{ alignSelf: 'center' }}
            >
              {saving ? <CircularProgress size={18} color="inherit" /> : 'Registrar'}
            </Button>
          </Stack>
        </Box>
      )}

      {!canEdit && items.length === 0 && (
        <Alert severity="info" sx={{ mb: 1 }}>
          Sin signos vitales registrados en esta atención.
        </Alert>
      )}

      {items.length > 0 && (
        <>
          <Divider sx={{ mb: 1 }} />
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Fecha</TableCell>
                <TableCell>Valores</TableCell>
                <TableCell>Registró</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.slice(0, compact ? 3 : 10).map((sv) => (
                <TableRow key={sv.id}>
                  <TableCell>
                    {sv.fecha_registro
                      ? new Date(sv.fecha_registro).toLocaleString('es-AR')
                      : '—'}
                  </TableCell>
                  <TableCell>{formatSv(sv)}</TableCell>
                  <TableCell>
                    {sv.registrado_por_nombre || sv.rol_registrador || '—'}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </>
      )}
    </Box>
  );
};

export default SignosVitalesPanel;
export { formatSv };
