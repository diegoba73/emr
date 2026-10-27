import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  Stack,
  Typography,
} from '@mui/material';
import { Close } from '@mui/icons-material';
import { pacientesService } from '../services/pacientes';
import type { Paciente } from '../types';
import {
  createPaciente,
  getCandidatosDuplicadoPaciente,
  updatePaciente,
  type PacienteDuplicadoCandidato,
} from '../services/apiService';
import { getSafeApiErrorMessage } from '../utils/apiError';
import PacienteDemographicsForm, {
  emptyPacienteFormValues,
  type PacienteDemographicsFormValues,
} from './PacienteDemographicsForm';
import PacienteAfiliacionesEditor from './PacienteAfiliacionesEditor';

function pacienteToFormValues(p: Paciente): PacienteDemographicsFormValues {
  const fecha = p.fecha_nacimiento;
  return {
    nombre: p.nombre || '',
    apellido: p.apellido || '',
    dni: p.dni || '',
    fecha_nacimiento: fecha ? String(fecha).slice(0, 10) : '',
    sexo: (p.sexo as 'M' | 'F' | 'O') || '',
    telefono: p.telefono || '',
    email: p.email || '',
    direccion: p.direccion || '',
    obra_social: p.obra_social || '',
    numero_afiliado: p.numero_afiliado || '',
    estado_civil: p.estado_civil || '',
    familiar_nombre: p.familiar_nombre || '',
    familiar_telefono: p.familiar_telefono || '',
    antecedentes_personales: p.antecedentes_personales || '',
    antecedentes_familiares: p.antecedentes_familiares || '',
    observaciones: p.observaciones || '',
  };
}

function formToPayload(values: PacienteDemographicsFormValues): Record<string, string | null> {
  const upper = (s: string) => s.trim().toUpperCase();
  const payload: Record<string, string | null> = {
    nombre: upper(values.nombre),
    apellido: upper(values.apellido),
    dni: values.dni.trim(),
    telefono: values.telefono.trim(),
    email: values.email.trim(),
    direccion: upper(values.direccion),
    obra_social: upper(values.obra_social),
    numero_afiliado: upper(values.numero_afiliado),
    estado_civil: values.estado_civil.trim(),
    familiar_nombre: values.familiar_nombre.trim(),
    familiar_telefono: values.familiar_telefono.trim(),
    antecedentes_personales: values.antecedentes_personales.trim(),
    antecedentes_familiares: values.antecedentes_familiares.trim(),
    observaciones: values.observaciones.trim(),
  };
  payload.fecha_nacimiento = values.fecha_nacimiento || null;
  payload.sexo = values.sexo || '';
  return payload;
}

function labelCandidato(p: Paciente): string {
  const nombre = `${p.apellido || ''} ${p.nombre || ''}`.trim() || `Paciente #${p.id}`;
  const dni = p.dni ? `DNI ${p.dni}` : 'sin DNI';
  const fnac = p.fecha_nacimiento ? String(p.fecha_nacimiento).slice(0, 10) : 'sin fecha';
  return `${nombre} — ${dni} — ${fnac} (ID ${p.id})`;
}

export interface PacienteFormDialogProps {
  open: boolean;
  mode: 'create' | 'edit';
  paciente?: Paciente | null;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
  /** Si hay duplicado y el usuario elige la ficha existente. */
  onUseExisting?: (paciente: Paciente) => void;
}

const PacienteFormDialog: React.FC<PacienteFormDialogProps> = ({
  open,
  mode,
  paciente,
  onClose,
  onSaved,
  onUseExisting,
}) => {
  const [values, setValues] = useState<PacienteDemographicsFormValues>(emptyPacienteFormValues());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [detailsReady, setDetailsReady] = useState(false);
  const [dupLoading, setDupLoading] = useState(false);
  const [candidatos, setCandidatos] = useState<PacienteDuplicadoCandidato[]>([]);
  const [bloqueaAlta, setBloqueaAlta] = useState(false);
  const [confirmDistinct, setConfirmDistinct] = useState(false);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setError('');
    setCandidatos([]);
    setBloqueaAlta(false);
    setConfirmDistinct(false);
    setDetailsReady(mode === 'create');
    setValues(emptyPacienteFormValues());
    setLoadingDetails(mode === 'edit');
    if (mode === 'edit' && paciente) {
      // El listado usa un serializer reducido: leer la ficha evita borrar datos omitidos.
      pacientesService.getById(paciente.id).then((full) => {
        if (cancelled) return;
        setValues(pacienteToFormValues(full));
        setDetailsReady(true);
      }).catch((e: unknown) => {
        if (!cancelled) setError(getSafeApiErrorMessage(e, 'No se pudo cargar la ficha completa. Cerrá y volvé a intentar.'));
      }).finally(() => { if (!cancelled) setLoadingDetails(false); });
    }
    return () => { cancelled = true; };
  }, [open, mode, paciente]);

  useEffect(() => {
    if (!open || mode !== 'create') return;

    const dni = values.dni.trim();
    const nombre = values.nombre.trim();
    const apellido = values.apellido.trim();
    const fecha_nacimiento = values.fecha_nacimiento.trim();
    const canCheckDni = dni.length >= 3;
    const canCheckIdentidad = Boolean(nombre && apellido && fecha_nacimiento);
    if (!canCheckDni && !canCheckIdentidad) {
      setCandidatos([]);
      setBloqueaAlta(false);
      setConfirmDistinct(false);
      setDupLoading(false);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      setDupLoading(true);
      void getCandidatosDuplicadoPaciente({
        ...(canCheckDni ? { dni } : {}),
        ...(canCheckIdentidad ? { nombre, apellido, fecha_nacimiento } : {}),
      })
        .then((res) => {
          if (cancelled) return;
          setCandidatos(res.resultados || []);
          setBloqueaAlta(Boolean(res.bloquea_alta));
          setConfirmDistinct(false);
        })
        .catch(() => {
          if (cancelled) return;
          // No bloquear el alta si falla el chequeo preventivo; el POST sigue validando DNI.
          setCandidatos([]);
          setBloqueaAlta(false);
        })
        .finally(() => {
          if (!cancelled) setDupLoading(false);
        });
    }, 400);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [
    open,
    mode,
    values.dni,
    values.nombre,
    values.apellido,
    values.fecha_nacimiento,
  ]);

  const handlePrincipalChange = useCallback((obra_social: string, numero_afiliado: string) => {
    setValues((prev) => ({ ...prev, obra_social, numero_afiliado }));
  }, []);

  const hasIdentidadOnly = useMemo(
    () => !bloqueaAlta && candidatos.some((c) => c.match === 'identidad'),
    [bloqueaAlta, candidatos],
  );

  const createBlocked = mode === 'create' && (bloqueaAlta || (hasIdentidadOnly && !confirmDistinct));

  const handleUseExisting = (p: Paciente) => {
    if (onUseExisting) {
      onUseExisting(p);
    }
    onClose();
  };

  const handleSave = async () => {
    if (!detailsReady || loadingDetails) return;
    setError('');
    if (mode === 'create' && !values.fecha_nacimiento) {
      setError('La fecha de nacimiento es obligatoria para crear el paciente');
      return;
    }
    if (!values.nombre.trim() || !values.apellido.trim() || !values.dni.trim()) {
      setError('Nombre, apellido y DNI son obligatorios');
      return;
    }
    if (createBlocked) {
      setError(
        bloqueaAlta
          ? 'Ya existe un paciente con este DNI. Usá la ficha existente.'
          : 'Hay posibles duplicados. Confirmá que es otra persona o usá la ficha existente.',
      );
      return;
    }
    setSaving(true);
    try {
      const payload = formToPayload(values);
      if (mode === 'create') {
        await createPaciente(payload as Partial<Paciente>);
      } else if (paciente) {
        await updatePaciente(paciente.id, payload as Partial<Paciente>);
      }
      await onSaved();
      onClose();
    } catch (e: unknown) {
      setError(getSafeApiErrorMessage(e, mode === 'create' ? 'Error al crear el paciente' : 'Error al guardar los cambios'));
    } finally {
      setSaving(false);
    }
  };

  const title = mode === 'create' ? 'Nuevo Paciente' : 'Editar Paciente';

  return (
    <Dialog open={open} onClose={saving ? undefined : onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6">{title}</Typography>
          <IconButton onClick={onClose} disabled={saving} sx={{ color: 'grey.500' }}>
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>
      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        {mode === 'create' && candidatos.length > 0 && (
          <Alert
            severity={bloqueaAlta ? 'error' : 'warning'}
            sx={{ mb: 2 }}
          >
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {bloqueaAlta
                ? 'Ya existe un paciente con este DNI. No se puede crear otra ficha.'
                : 'Posible duplicado: mismo nombre, apellido y fecha de nacimiento.'}
            </Typography>
            <Stack spacing={1}>
              {candidatos.map(({ match, paciente: p }) => (
                <Box
                  key={p.id}
                  sx={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 1,
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <Typography variant="body2">
                    {labelCandidato(p)}
                    {match === 'dni' ? ' · DNI coincidente' : ' · Identidad coincidente'}
                  </Typography>
                  <Button size="small" variant="outlined" onClick={() => handleUseExisting(p)} disabled={saving}>
                    Usar esta ficha
                  </Button>
                </Box>
              ))}
            </Stack>
            {hasIdentidadOnly && (
              <FormControlLabel
                sx={{ mt: 1 }}
                control={
                  <Checkbox
                    checked={confirmDistinct}
                    onChange={(e) => setConfirmDistinct(e.target.checked)}
                  />
                }
                label="Confirmo que es otra persona (no es un duplicado)"
              />
            )}
          </Alert>
        )}
        {mode === 'create' && dupLoading && (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            Buscando posibles duplicados…
          </Typography>
        )}
        {mode === 'edit' && paciente && (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            {paciente.nombre} {paciente.apellido} — ID {paciente.id}
          </Typography>
        )}
        {loadingDetails && <CircularProgress aria-label="Cargando ficha" size={24} />}
        {detailsReady && (
          <>
            <PacienteDemographicsForm
              values={values}
              onChange={(patch) => setValues((prev) => ({ ...prev, ...patch }))}
              requireBirthDate={mode === 'create'}
              hideObraSocial={mode === 'edit'}
            />
            {mode === 'edit' && paciente && (
              <PacienteAfiliacionesEditor
                pacienteId={paciente.id}
                obraSocialForm={values.obra_social}
                numeroAfiliadoForm={values.numero_afiliado}
                onPrincipalChange={handlePrincipalChange}
                disabled={saving}
              />
            )}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          Cancelar
        </Button>
        <Button
          variant="contained"
          disabled={saving || loadingDetails || !detailsReady || createBlocked || dupLoading}
          onClick={handleSave}
        >
          {saving ? 'Guardando…' : mode === 'create' ? 'Crear Paciente' : 'Guardar Cambios'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default PacienteFormDialog;
