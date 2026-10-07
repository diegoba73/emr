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
} from '@mui/material';
import { DeleteOutline, Star, StarBorder } from '@mui/icons-material';
import type { PacienteAfiliacion } from '../types';
import {
  createPacienteAfiliacion,
  deletePacienteAfiliacion,
  listPacienteAfiliaciones,
  updatePacienteAfiliacion,
} from '../services/pacienteAfiliaciones';
import { getSafeApiErrorMessage } from '../utils/apiError';

type Props = {
  pacienteId: number;
  /** Campos legacy del form (espejo de la principal); se sincronizan al cambiar. */
  obraSocialForm: string;
  numeroAfiliadoForm: string;
  onPrincipalChange: (obra_social: string, numero_afiliado: string) => void;
  disabled?: boolean;
};

const PacienteAfiliacionesEditor: React.FC<Props> = ({
  pacienteId,
  obraSocialForm,
  numeroAfiliadoForm,
  onPrincipalChange,
  disabled = false,
}) => {
  const [items, setItems] = useState<PacienteAfiliacion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [nuevaOs, setNuevaOs] = useState('');
  const [nuevaAfil, setNuevaAfil] = useState('');
  const [saving, setSaving] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listPacienteAfiliaciones(pacienteId);
      setItems(data);
      const principal = data.find((a) => a.es_principal) || data[0];
      if (principal) {
        onPrincipalChange(principal.obra_social || '', principal.numero_afiliado || '');
      } else {
        onPrincipalChange('', '');
      }
    } catch (e) {
      setError(getSafeApiErrorMessage(e, 'No se pudieron cargar las afiliaciones.'));
    } finally {
      setLoading(false);
    }
  }, [pacienteId, onPrincipalChange]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const handleAdd = async () => {
    const os = nuevaOs.trim();
    if (!os) {
      setError('Indicá la obra social.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      await createPacienteAfiliacion(pacienteId, {
        obra_social: os,
        numero_afiliado: nuevaAfil.trim(),
        es_principal: items.length === 0,
      });
      setNuevaOs('');
      setNuevaAfil('');
      await reload();
    } catch (e) {
      setError(getSafeApiErrorMessage(e, 'No se pudo agregar la afiliación.'));
    } finally {
      setSaving(false);
    }
  };

  const handlePrincipal = async (afil: PacienteAfiliacion) => {
    setSaving(true);
    setError('');
    try {
      await updatePacienteAfiliacion(pacienteId, afil.id, { es_principal: true });
      await reload();
    } catch (e) {
      setError(getSafeApiErrorMessage(e, 'No se pudo marcar como principal.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (afil: PacienteAfiliacion) => {
    setSaving(true);
    setError('');
    try {
      await deletePacienteAfiliacion(pacienteId, afil.id);
      await reload();
    } catch (e) {
      setError(getSafeApiErrorMessage(e, 'No se pudo quitar la afiliación.'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Box sx={{ width: '100%', mt: 1 }}>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Obras sociales
      </Typography>
      {loading ? (
        <CircularProgress size={22} />
      ) : (
        <Stack spacing={1}>
          {items.map((a) => (
            <Stack
              key={a.id}
              direction="row"
              spacing={1}
              alignItems="center"
              sx={{
                border: '1px solid',
                borderColor: 'divider',
                borderRadius: 1,
                px: 1,
                py: 0.75,
              }}
            >
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="body2" noWrap>
                  <strong>{a.obra_social}</strong>
                  {a.numero_afiliado ? ` · ${a.numero_afiliado}` : ''}
                </Typography>
              </Box>
              {a.es_principal ? (
                <Chip size="small" label="Principal" color="primary" />
              ) : (
                <IconButton
                  size="small"
                  title="Marcar principal"
                  disabled={disabled || saving}
                  onClick={() => void handlePrincipal(a)}
                >
                  <StarBorder fontSize="small" />
                </IconButton>
              )}
              {a.es_principal && <Star fontSize="small" color="primary" />}
              <IconButton
                size="small"
                title="Quitar"
                disabled={disabled || saving}
                onClick={() => void handleDelete(a)}
              >
                <DeleteOutline fontSize="small" />
              </IconButton>
            </Stack>
          ))}
          {items.length === 0 && (
            <Typography variant="caption" color="text.secondary">
              Sin afiliaciones. Podés cargar la principal abajo o agregar varias.
              {obraSocialForm.trim()
                ? ` (Formulario: ${obraSocialForm}${
                    numeroAfiliadoForm.trim() ? ` · ${numeroAfiliadoForm}` : ''
                  })`
                : ''}
            </Typography>
          )}
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems="flex-start">
            <TextField
              size="small"
              label="Nueva obra social"
              value={nuevaOs}
              onChange={(e) => setNuevaOs(e.target.value)}
              disabled={disabled || saving}
              sx={{ flex: 2, minWidth: 160 }}
            />
            <TextField
              size="small"
              label="N° afiliado"
              value={nuevaAfil}
              onChange={(e) => setNuevaAfil(e.target.value)}
              disabled={disabled || saving}
              sx={{ flex: 1, minWidth: 120 }}
            />
            <Button
              variant="outlined"
              size="small"
              onClick={() => void handleAdd()}
              disabled={disabled || saving || !nuevaOs.trim()}
              sx={{ whiteSpace: 'nowrap' }}
            >
              Agregar
            </Button>
          </Stack>
          {error && (
            <Typography variant="caption" color="error">
              {error}
            </Typography>
          )}
        </Stack>
      )}
    </Box>
  );
};

export default PacienteAfiliacionesEditor;
