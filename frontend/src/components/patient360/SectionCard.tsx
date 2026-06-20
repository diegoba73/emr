import React from 'react';
import { Paper, Typography, Box, alpha, useTheme } from '@mui/material';

export interface SectionCardProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  /** Énfasis visual para estados críticos */
  emphasis?: 'default' | 'alert' | 'success';
  /** Acción en cabecera (p. ej. enlace) */
  headerRight?: React.ReactNode;
}

const SectionCard: React.FC<SectionCardProps> = ({ title, subtitle, children, emphasis = 'default', headerRight }) => {
  const theme = useTheme();
  const border =
    emphasis === 'alert'
      ? `1px solid ${alpha(theme.palette.error.main, 0.45)}`
      : emphasis === 'success'
        ? `1px solid ${alpha(theme.palette.success.main, 0.45)}`
        : `1px solid ${alpha(theme.palette.divider, 1)}`;
  const bg =
    emphasis === 'alert'
      ? alpha(theme.palette.error.main, 0.04)
      : emphasis === 'success'
        ? alpha(theme.palette.success.main, 0.04)
        : theme.palette.background.paper;

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        borderRadius: 2,
        border,
        bgcolor: bg,
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 1, mb: subtitle ? 0.5 : 1.5 }}>
        <Box>
          <Typography variant="subtitle1" fontWeight={700}>
            {title}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Box>
        {headerRight}
      </Box>
      <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto' }}>{children}</Box>
    </Paper>
  );
};

export default SectionCard;
