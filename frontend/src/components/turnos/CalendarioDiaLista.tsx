import React, { useMemo } from 'react';
import {
  Box,
  Button,
  ButtonGroup,
  Chip,
  Paper,
  Typography,
} from '@mui/material';
import { ChevronLeft, ChevronRight, Today } from '@mui/icons-material';
import type { Turno } from '../../types';
import {
  formatTurnoCalendarTitle,
  getTurnoAgendaKind,
  getTurnoKindMeta,
  TURNO_KIND_META,
  type TurnoAgendaKind,
} from '../../utils/turnoKind';
import { getTurnoEstadoColor } from '../../utils/turnoEstadoColors';
import { formatHoraDisplay } from '../../utils/dateFieldFormat';

function formatHora(d: Date): string {
  return formatHoraDisplay(d);
}

function sameLocalDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function addDays(d: Date, n: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}

const KIND_CHIP_COLOR: Record<
  TurnoAgendaKind,
  'primary' | 'info' | 'warning' | 'error' | 'default'
> = {
  consulta: 'primary',
  estudio: 'info',
  procedimiento: 'warning',
  cirugia: 'error',
};

export interface CalendarioDiaListaProps {
  date: Date;
  turnos: Turno[];
  onNavigate: (d: Date) => void;
  onChangeView: (view: 'month' | 'week' | 'day') => void;
  onSelectTurno: (t: Turno) => void;
  onNuevoTurno?: () => void;
  canCreate?: boolean;
}

/**
 * Vista Día del calendario como lista cronológica clara (paciente, médico, tipo).
 */
const CalendarioDiaLista: React.FC<CalendarioDiaListaProps> = ({
  date,
  turnos,
  onNavigate,
  onChangeView,
  onSelectTurno,
  onNuevoTurno,
  canCreate = false,
}) => {
  const delDia = useMemo(() => {
    return turnos
      .filter((t) => {
        if (!t.fecha_hora_inicio) return false;
        return sameLocalDay(new Date(t.fecha_hora_inicio), date);
      })
      .sort(
        (a, b) =>
          new Date(a.fecha_hora_inicio).getTime() - new Date(b.fecha_hora_inicio).getTime()
      );
  }, [turnos, date]);

  const resumenTipos = useMemo(() => {
    const counts: Partial<Record<TurnoAgendaKind, number>> = {};
    for (const t of delDia) {
      const k = getTurnoAgendaKind(t);
      counts[k] = (counts[k] || 0) + 1;
    }
    return counts;
  }, [delDia]);

  const tituloFecha = date.toLocaleDateString('es-AR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  return (
    <Box data-testid="calendario-dia-lista">
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          gap: 1,
          mb: 2,
        }}
      >
        <ButtonGroup size="small" variant="outlined">
          <Button onClick={() => onChangeView('month')}>Mes</Button>
          <Button onClick={() => onChangeView('week')}>Semana</Button>
          <Button variant="contained" onClick={() => onChangeView('day')}>
            Día
          </Button>
        </ButtonGroup>
        <ButtonGroup size="small" variant="outlined">
          <Button
            aria-label="Día anterior"
            onClick={() => onNavigate(addDays(date, -1))}
          >
            <ChevronLeft />
          </Button>
          <Button startIcon={<Today />} onClick={() => onNavigate(new Date())}>
            Hoy
          </Button>
          <Button aria-label="Día siguiente" onClick={() => onNavigate(addDays(date, 1))}>
            <ChevronRight />
          </Button>
        </ButtonGroup>
        <Typography variant="h6" sx={{ flex: 1, minWidth: 180, textTransform: 'capitalize' }}>
          {tituloFecha}
        </Typography>
        {canCreate && onNuevoTurno && (
          <Button variant="contained" size="small" onClick={onNuevoTurno}>
            Nuevo turno
          </Button>
        )}
      </Box>

      {Object.keys(resumenTipos).length > 0 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
          {(Object.keys(resumenTipos) as TurnoAgendaKind[]).map((k) => (
            <Chip
              key={k}
              size="small"
              color={KIND_CHIP_COLOR[k]}
              variant="outlined"
              label={`${TURNO_KIND_META[k].shortLabel}: ${resumenTipos[k]}`}
            />
          ))}
        </Box>
      )}

      {delDia.length === 0 ? (
        <Paper sx={{ p: 3 }}>
          <Typography color="text.secondary">No hay turnos este día.</Typography>
        </Paper>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {delDia.map((t) => {
            const kind = getTurnoAgendaKind(t);
            const meta = getTurnoKindMeta(t);
            const start = new Date(t.fecha_hora_inicio);
            const end = t.fecha_hora_fin ? new Date(t.fecha_hora_fin) : null;
            const paciente = t.paciente
              ? `${t.paciente.apellido || ''}, ${t.paciente.nombre || ''}`.replace(/^,\s*|,\s*$/g, '').trim()
              : 'Sin paciente';
            const medico = t.medico
              ? `Dr. ${(t.medico.apellido || t.medico.nombre || '').trim()}`
              : 'Sin médico';
            const prestacion =
              t.estudio_complementario?.tipo_estudio_nombre ||
              (t.estudio_complementario as { procedimiento_catalogo_nombre?: string } | undefined)
                ?.procedimiento_catalogo_nombre ||
              t.motivo_reserva ||
              '';
            const estadoColor = getTurnoEstadoColor(t.estado);

            return (
              <Paper
                key={t.id}
                elevation={0}
                onClick={() => onSelectTurno(t)}
                sx={{
                  p: 1.5,
                  cursor: 'pointer',
                  border: 1,
                  borderColor: 'divider',
                  borderLeft: 4,
                  borderLeftColor: estadoColor || 'primary.main',
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: 1.5,
                  alignItems: 'flex-start',
                  '&:hover': { bgcolor: 'action.hover' },
                }}
              >
                <Box sx={{ minWidth: 88 }}>
                  <Typography variant="h6" sx={{ fontWeight: 700, lineHeight: 1.1 }}>
                    {formatHora(start)}
                  </Typography>
                  {end && (
                    <Typography variant="caption" color="text.secondary">
                      → {formatHora(end)}
                    </Typography>
                  )}
                </Box>
                <Box sx={{ flex: 1, minWidth: 180 }}>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75, mb: 0.5 }}>
                    <Chip size="small" color={KIND_CHIP_COLOR[kind]} label={meta.shortLabel} />
                    <Chip size="small" variant="outlined" label={t.estado} />
                  </Box>
                  <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                    {paciente}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {medico}
                    {t.recurso?.nombre ? ` · ${t.recurso.nombre}` : ''}
                  </Typography>
                  {prestacion && (
                    <Typography variant="body2" sx={{ mt: 0.25 }}>
                      {prestacion}
                    </Typography>
                  )}
                </Box>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ display: { xs: 'none', md: 'block' }, maxWidth: 200 }}
                >
                  {formatTurnoCalendarTitle(t)}
                </Typography>
              </Paper>
            );
          })}
        </Box>
      )}
    </Box>
  );
};

export default CalendarioDiaLista;
