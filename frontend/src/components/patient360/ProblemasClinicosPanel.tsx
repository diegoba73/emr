import React, { useCallback, useEffect, useState } from 'react';
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  IconButton,
  Stack,
  TextField,
  Typography,
  FormControlLabel,
  Checkbox,
} from '@mui/material';
import { Add, Star, StarBorder, CheckCircleOutline } from '@mui/icons-material';
import {
  createProblemaClinico,
  listProblemasClinicos,
  resolverProblemaClinico,
  updateProblemaClinico,
  type ProblemaClinico,
} from '../../services/pacienteProblemas';
import SectionCard from './SectionCard';

export interface ProblemasClinicosPanelProps {
  pacienteId: number;
  canEdit: boolean;
}

const ProblemasClinicosPanel: React.FC<ProblemasClinicosPanelProps> = ({
  pacienteId,
  canEdit,
}) => {
  const [items, setItems] = useState<ProblemaClinico[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [nuevo, setNuevo] = useState('');
  const [comoPrincipal, setComoPrincipal] = useState(true);
  const [editId, setEditId] = useState<number | null>(null);
  const [editTexto, setEditTexto] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listProblemasClinicos(pacienteId, { estado: 'ACTIVO' });
      setItems(data);
    } catch {
      setError('No se pudieron cargar los diagnósticos.');
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [pacienteId]);

  useEffect(() => {
    void load();
  }, [load]);

  const onCrear = async () => {
    const texto = nuevo.trim();
    if (!texto || saving) return;
    setSaving(true);
    setError('');
    try {
      await createProblemaClinico(pacienteId, {
        texto,
        es_principal: comoPrincipal || items.length === 0,
      });
      setNuevo('');
      setComoPrincipal(true);
      await load();
    } catch {
      setError('No se pudo agregar el diagnóstico.');
    } finally {
      setSaving(false);
    }
  };

  const onMarcarPrincipal = async (p: ProblemaClinico) => {
    if (!canEdit || p.es_principal || saving) return;
    setSaving(true);
    try {
      await updateProblemaClinico(pacienteId, p.id, { es_principal: true });
      await load();
    } catch {
      setError('No se pudo marcar como principal.');
    } finally {
      setSaving(false);
    }
  };

  const onResolver = async (p: ProblemaClinico) => {
    if (!canEdit || saving) return;
    if (!window.confirm(`¿Resolver «${p.display || p.texto}»?`)) return;
    setSaving(true);
    try {
      await resolverProblemaClinico(pacienteId, p.id);
      await load();
    } catch {
      setError('No se pudo resolver el problema.');
    } finally {
      setSaving(false);
    }
  };

  const onGuardarEdit = async () => {
    if (editId == null || saving) return;
    const texto = editTexto.trim();
    if (!texto) return;
    setSaving(true);
    try {
      await updateProblemaClinico(pacienteId, editId, { texto });
      setEditId(null);
      setEditTexto('');
      await load();
    } catch {
      setError('No se pudo guardar el cambio.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <SectionCard
      title="Diagnósticos / problemas activos"
      subtitle="El principal se congela en pedidos de laboratorio y presentaciones a OS"
      headerRight={loading ? <CircularProgress size={18} /> : null}
    >
      {error && (
        <Typography variant="caption" color="error" sx={{ mb: 1, display: 'block' }}>
          {error}
        </Typography>
      )}
      <Stack spacing={1} sx={{ mb: 1.5 }}>
        {items.length === 0 && !loading && (
          <Typography variant="body2" color="text.secondary">
            Sin diagnósticos activos. El médico puede cargarlos aquí.
          </Typography>
        )}
        {items.map((p) => (
          <Box
            key={p.id}
            sx={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 1,
              py: 0.5,
              borderBottom: '1px solid',
              borderColor: 'divider',
            }}
          >
            <IconButton
              size="small"
              disabled={!canEdit || p.es_principal || saving}
              onClick={() => void onMarcarPrincipal(p)}
              title={p.es_principal ? 'Principal' : 'Marcar como principal'}
              aria-label={p.es_principal ? 'Principal' : 'Marcar como principal'}
            >
              {p.es_principal ? <Star color="warning" fontSize="small" /> : <StarBorder fontSize="small" />}
            </IconButton>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              {editId === p.id ? (
                <Stack direction="row" spacing={1} alignItems="center">
                  <TextField
                    size="small"
                    fullWidth
                    value={editTexto}
                    onChange={(e) => setEditTexto(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') void onGuardarEdit();
                    }}
                  />
                  <Button size="small" onClick={() => void onGuardarEdit()} disabled={saving}>
                    OK
                  </Button>
                  <Button
                    size="small"
                    onClick={() => {
                      setEditId(null);
                      setEditTexto('');
                    }}
                  >
                    Cancelar
                  </Button>
                </Stack>
              ) : (
                <Typography
                  variant="body2"
                  sx={{ cursor: canEdit ? 'pointer' : 'default' }}
                  onClick={() => {
                    if (!canEdit) return;
                    setEditId(p.id);
                    setEditTexto(p.texto);
                  }}
                >
                  {p.display || p.texto}
                  {p.es_principal && (
                    <Chip size="small" label="Principal" sx={{ ml: 1 }} color="warning" variant="outlined" />
                  )}
                </Typography>
              )}
            </Box>
            {canEdit && (
              <IconButton
                size="small"
                onClick={() => void onResolver(p)}
                disabled={saving}
                title="Resolver"
                aria-label="Resolver"
              >
                <CheckCircleOutline fontSize="small" />
              </IconButton>
            )}
          </Box>
        ))}
      </Stack>
      {canEdit && (
        <Stack spacing={1}>
          <TextField
            size="small"
            label="Nuevo diagnóstico"
            placeholder="Ej. HTA + DBT2"
            value={nuevo}
            onChange={(e) => setNuevo(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') void onCrear();
            }}
            fullWidth
          />
          <Stack direction="row" alignItems="center" justifyContent="space-between">
            <FormControlLabel
              control={
                <Checkbox
                  size="small"
                  checked={comoPrincipal}
                  onChange={(e) => setComoPrincipal(e.target.checked)}
                />
              }
              label="Marcar como principal"
            />
            <Button
              size="small"
              variant="contained"
              startIcon={<Add />}
              onClick={() => void onCrear()}
              disabled={saving || !nuevo.trim()}
            >
              Agregar
            </Button>
          </Stack>
        </Stack>
      )}
    </SectionCard>
  );
};

export default ProblemasClinicosPanel;
