import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  ButtonGroup,
  Chip,
  CircularProgress,
  IconButton,
  Typography,
} from '@mui/material';
import { ChevronLeft, ChevronRight } from '@mui/icons-material';
import {
  getDiasDisponibles,
  getSlotsMedico,
  type DiaDisponible,
  type SlotMedico,
  type TipoAgenda,
} from '../../services/agendaMedica';
import { getSafeClinicalActionMessage } from '../../utils/apiError';

const fechaLocal = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

function inicioMes(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function finMes(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0);
}

function mismoMes(a: Date, b: Date): boolean {
  return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth();
}

export interface SlotPickerStaffProps {
  medicoId: number | null;
  tipo: TipoAgenda;
  value: SlotMedico | null;
  onChange: (slot: SlotMedico | null) => void;
  disabled?: boolean;
  /** Meses hacia adelante permitidos desde el mes actual (default 12). */
  maxMesesAdelante?: number;
}

/**
 * Selector visual: mes → días libres → horas.
 * Pensado para secretaría cuando los turnos libres están varios meses adelante.
 */
const SlotPickerStaff: React.FC<SlotPickerStaffProps> = ({
  medicoId,
  tipo,
  value,
  onChange,
  disabled = false,
  maxMesesAdelante = 12,
}) => {
  const hoy = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  const [mesVista, setMesVista] = useState(() => inicioMes(new Date()));
  const [diasLibres, setDiasLibres] = useState<DiaDisponible[]>([]);
  const [fechaElegida, setFechaElegida] = useState('');
  const [slots, setSlots] = useState<SlotMedico[]>([]);
  const [loadingDias, setLoadingDias] = useState(false);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [error, setError] = useState('');

  const mesMin = useMemo(() => inicioMes(hoy), [hoy]);
  const mesMax = useMemo(
    () => new Date(hoy.getFullYear(), hoy.getMonth() + maxMesesAdelante, 1),
    [hoy, maxMesesAdelante]
  );

  const puedeMesAnterior = mesVista > mesMin;
  const puedeMesSiguiente = mesVista < mesMax;

  const rangoMes = useMemo(() => {
    const desdeDate = inicioMes(mesVista);
    const hastaDate = finMes(mesVista);
    const desde = fechaLocal(desdeDate < hoy ? hoy : desdeDate);
    const hasta = fechaLocal(hastaDate);
    return { desde, hasta };
  }, [mesVista, hoy]);

  const labelMes = mesVista.toLocaleDateString('es-AR', {
    month: 'long',
    year: 'numeric',
  });

  // Al cambiar médico/tipo, volver al mes actual
  useEffect(() => {
    setMesVista(inicioMes(new Date()));
    setFechaElegida('');
    setSlots([]);
    setDiasLibres([]);
    onChange(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [medicoId, tipo]);

  useEffect(() => {
    setDiasLibres([]);
    setFechaElegida('');
    setSlots([]);
    onChange(null);
    if (!medicoId) return;
    if (rangoMes.desde > rangoMes.hasta) {
      setDiasLibres([]);
      return;
    }
    let active = true;
    setLoadingDias(true);
    setError('');
    getDiasDisponibles(medicoId, rangoMes.desde, rangoMes.hasta, tipo)
      .then((dias) => {
        if (!active) return;
        setDiasLibres(dias);
        if (dias.length === 1) setFechaElegida(dias[0].fecha);
      })
      .catch((e) => {
        if (active) {
          setError(getSafeClinicalActionMessage(e, 'No se pudo consultar los días disponibles.'));
        }
      })
      .finally(() => {
        if (active) setLoadingDias(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [medicoId, tipo, rangoMes.desde, rangoMes.hasta]);

  useEffect(() => {
    setSlots([]);
    onChange(null);
    if (!medicoId || !fechaElegida) return;
    let active = true;
    setLoadingSlots(true);
    getSlotsMedico(medicoId, fechaElegida, tipo)
      .then((s) => {
        if (active) setSlots(s);
      })
      .catch((e) => {
        if (active) {
          setError(getSafeClinicalActionMessage(e, 'No se pudo consultar la disponibilidad.'));
        }
      })
      .finally(() => {
        if (active) setLoadingSlots(false);
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [medicoId, fechaElegida, tipo]);

  const irMes = (delta: number) => {
    if (disabled) return;
    setMesVista((prev) => {
      const next = new Date(prev.getFullYear(), prev.getMonth() + delta, 1);
      if (next < mesMin) return mesMin;
      if (next > mesMax) return mesMax;
      return next;
    });
  };

  if (!medicoId) {
    return (
      <Alert severity="info">Seleccioná el profesional para ver los horarios libres.</Alert>
    );
  }

  return (
    <Box data-testid="slot-picker-staff">
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        Elegí mes, día y hora
      </Typography>

      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 1,
          mb: 1.5,
          flexWrap: 'wrap',
        }}
      >
        <ButtonGroup size="small" variant="outlined" disabled={disabled}>
          <IconButton
            aria-label="Mes anterior"
            size="small"
            disabled={disabled || !puedeMesAnterior}
            onClick={() => irMes(-1)}
          >
            <ChevronLeft />
          </IconButton>
          <Button
            disabled={disabled || mismoMes(mesVista, mesMin)}
            onClick={() => setMesVista(mesMin)}
            sx={{ textTransform: 'none', minWidth: 64 }}
          >
            Hoy
          </Button>
          <IconButton
            aria-label="Mes siguiente"
            size="small"
            disabled={disabled || !puedeMesSiguiente}
            onClick={() => irMes(1)}
          >
            <ChevronRight />
          </IconButton>
        </ButtonGroup>
        <Typography
          variant="subtitle1"
          sx={{ fontWeight: 700, textTransform: 'capitalize', flex: 1, textAlign: { xs: 'left', sm: 'right' } }}
        >
          {labelMes}
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 1 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {loadingDias && <CircularProgress size={22} sx={{ mb: 1 }} />}
      {!loadingDias && !diasLibres.length && (
        <Alert severity="warning" sx={{ mb: 1 }}>
          No hay horarios libres de {tipo === 'ESTUDIO' ? 'estudio' : 'consulta'} en{' '}
          <strong style={{ textTransform: 'capitalize' }}>{labelMes}</strong>. Probá el mes
          siguiente o revisá Horarios de atención.
        </Alert>
      )}
      <Box
        sx={{
          display: 'flex',
          gap: 1,
          overflowX: 'auto',
          pb: 1,
          mb: 1.5,
          WebkitOverflowScrolling: 'touch',
        }}
      >
        {diasLibres.map((d) => {
          const selected = fechaElegida === d.fecha;
          const label = new Date(`${d.fecha}T12:00:00`).toLocaleDateString('es-AR', {
            weekday: 'short',
            day: 'numeric',
          });
          return (
            <Chip
              key={d.fecha}
              label={`${label} · ${d.cantidad_slots}`}
              color={selected ? 'primary' : 'default'}
              variant={selected ? 'filled' : 'outlined'}
              disabled={disabled}
              onClick={() => {
                setFechaElegida(d.fecha);
                onChange(null);
              }}
              sx={{ flexShrink: 0 }}
            />
          );
        })}
      </Box>
      {fechaElegida && (
        <>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Horarios del{' '}
            {new Date(`${fechaElegida}T12:00:00`).toLocaleDateString('es-AR', {
              weekday: 'long',
              day: 'numeric',
              month: 'long',
            })}
          </Typography>
          {loadingSlots && <CircularProgress size={22} />}
          {!loadingSlots && !slots.length && (
            <Alert severity="info">No quedan horarios libres ese día.</Alert>
          )}
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {slots.map((slot) => {
              const hora = new Date(slot.inicio).toLocaleTimeString('es-AR', {
                hour: '2-digit',
                minute: '2-digit',
              });
              const selected = value?.inicio === slot.inicio;
              return (
                <Button
                  key={slot.inicio}
                  variant={selected ? 'contained' : 'outlined'}
                  color={selected ? 'success' : 'primary'}
                  disabled={disabled}
                  onClick={() => onChange(slot)}
                  sx={{ minWidth: 80, py: 1.25, fontSize: '1rem' }}
                >
                  {hora}
                </Button>
              );
            })}
          </Box>
          {value?.recurso_nombre && (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              {tipo === 'ESTUDIO' ? 'Sala' : 'Consultorio'}: {value.recurso_nombre}
            </Typography>
          )}
        </>
      )}
    </Box>
  );
};

export default SlotPickerStaff;
