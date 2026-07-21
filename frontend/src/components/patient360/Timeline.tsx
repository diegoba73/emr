import React from 'react';
import { Box, Typography, Stack, Chip, useTheme, alpha, Paper } from '@mui/material';
import { LocalHospital, Science, Healing, Event, Assignment, Hotel, Emergency } from '@mui/icons-material';

export type TimelineItemType =
  | 'consulta'
  | 'guardia'
  | 'estudio'
  | 'procedimiento'
  | 'turno'
  | 'solicitud'
  | 'internacion_ingreso'
  | 'internacion_evolucion'
  | 'internacion_alta'
  | 'otro';

export interface TimelineItem {
  id: string;
  type: TimelineItemType;
  title: string;
  subtitle?: string;
  date: Date;
  critical?: boolean;
  onClick?: () => void;
  episodeGroupId?: string;
  episodeGroupTitle?: string;
  nested?: boolean;
}

const typeColor = (type: TimelineItemType, theme: { palette: any }) => {
  switch (type) {
    case 'consulta':
      return theme.palette.primary.main;
    case 'guardia':
      return theme.palette.error.main;
    case 'estudio':
      return theme.palette.info.main;
    case 'procedimiento':
      return theme.palette.warning.main;
    case 'turno':
      return theme.palette.secondary.main;
    case 'solicitud':
      return theme.palette.success.main;
    case 'internacion_ingreso':
    case 'internacion_evolucion':
    case 'internacion_alta':
      return theme.palette.warning.main;
    default:
      return theme.palette.text.secondary;
  }
};

const typeIcon = (type: TimelineItemType) => {
  switch (type) {
    case 'consulta':
      return <LocalHospital fontSize="small" />;
    case 'guardia':
      return <Emergency fontSize="small" />;
    case 'estudio':
      return <Science fontSize="small" />;
    case 'procedimiento':
      return <Healing fontSize="small" />;
    case 'turno':
      return <Event fontSize="small" />;
    case 'solicitud':
      return <Assignment fontSize="small" />;
    case 'internacion_ingreso':
    case 'internacion_evolucion':
    case 'internacion_alta':
      return <Hotel fontSize="small" />;
    default:
      return <Event fontSize="small" />;
  }
};

export interface TimelineProps {
  items: TimelineItem[];
  emptyLabel?: string;
}

/**
 * Línea de tiempo clínica: ítems ordenados por fecha (descendente en el listado).
 */
const Timeline: React.FC<TimelineProps> = ({ items, emptyLabel = 'Sin eventos clínicos en el período cargado' }) => {
  const theme = useTheme();
  const sorted = [...items].sort((a, b) => b.date.getTime() - a.date.getTime());

  if (sorted.length === 0) {
    return (
      <Box sx={{ py: 3, textAlign: 'center' }}>
        <Typography color="text.secondary" variant="body2">
          {emptyLabel}
        </Typography>
      </Box>
    );
  }

  return (
    <Stack spacing={1.25} sx={{ pl: 0.5 }}>
      {sorted.map((item) => {
        const c = typeColor(item.type, theme);
        const isInternacionEpisode = Boolean(item.episodeGroupId);
        return (
          <Box key={item.id}>
            {item.episodeGroupTitle && (
              <Typography
                variant="caption"
                fontWeight={700}
                color="warning.dark"
                sx={{ display: 'block', mb: 0.5, ml: item.nested ? 2 : 0 }}
              >
                {item.episodeGroupTitle}
              </Typography>
            )}
          <Paper
            variant="outlined"
            onClick={item.onClick}
            sx={{
              p: 1.5,
              display: 'flex',
              gap: 1.5,
              ml: item.nested ? 2 : 0,
              borderLeft: `4px solid ${c}`,
              cursor: item.onClick ? 'pointer' : 'default',
              transition: 'background 0.15s',
              bgcolor: item.critical
                ? alpha(theme.palette.error.main, 0.04)
                : isInternacionEpisode
                  ? alpha(theme.palette.warning.main, 0.04)
                  : 'background.paper',
              '&:hover': item.onClick
                ? { bgcolor: alpha(c, 0.06) }
                : undefined,
            }}
          >
            <Box
              sx={{
                width: 36,
                height: 36,
                borderRadius: 1,
                flexShrink: 0,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'common.white',
                bgcolor: c,
              }}
            >
              {typeIcon(item.type)}
            </Box>
            <Box sx={{ minWidth: 0, flex: 1 }}>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 0.75, mb: 0.25 }}>
                <Typography variant="subtitle2" fontWeight={700}>
                  {item.title}
                </Typography>
                <Chip
                  size="small"
                  label={item.type}
                  sx={{ textTransform: 'capitalize', height: 22, fontSize: '0.7rem' }}
                />
                {item.critical && <Chip size="small" color="error" label="Riesgo" sx={{ height: 22, fontSize: '0.7rem' }} />}
              </Box>
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
                {item.date.toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' })}
              </Typography>
              {item.subtitle && (
                <Typography variant="body2" color="text.secondary">
                  {item.subtitle}
                </Typography>
              )}
            </Box>
          </Paper>
          </Box>
        );
      })}
    </Stack>
  );
};

export default Timeline;
