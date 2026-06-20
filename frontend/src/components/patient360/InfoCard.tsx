import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';

export interface InfoCardProps {
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
  dense?: boolean;
}

/**
 * Tarjeta compacta para métricas o listas cortas en Patient 360.
 */
const InfoCard: React.FC<InfoCardProps> = ({ title, children, action, dense }) => (
  <Card variant="outlined" sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
    <CardContent sx={{ py: dense ? 1.25 : 2, '&:last-child': { pb: dense ? 1.25 : 2 } }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="subtitle2" color="text.secondary" fontWeight={600}>
          {title}
        </Typography>
        {action}
      </Box>
      {children}
    </CardContent>
  </Card>
);

export default InfoCard;
