import React, { useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Collapse,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Typography,
} from '@mui/material';
import { Campaign as CampaignIcon, Close as CloseIcon } from '@mui/icons-material';
import {
  AnnouncementAudience,
  getActiveAnnouncements,
} from '../data/announcements';

export interface AnnouncementsBannerProps {
  /** Quién ve el home: staff (dashboard) o paciente (portal). */
  audience?: AnnouncementAudience;
  /** Título del bloque. */
  heading?: string;
}

/**
 * Banner de noticias en la pantalla de inicio (después del login).
 * Soporta varios ítems; se puede ocultar en la sesión actual.
 */
const AnnouncementsBanner: React.FC<AnnouncementsBannerProps> = ({
  audience = 'all',
  heading = 'Novedades',
}) => {
  const items = useMemo(() => getActiveAnnouncements(audience) || [], [audience]);
  const [dismissed, setDismissed] = useState(false);

  if (!items.length || dismissed) {
    return null;
  }

  return (
    <Collapse in={!dismissed}>
      <Alert
        severity="info"
        icon={<CampaignIcon fontSize="inherit" />}
        data-testid="announcements-banner"
        sx={{ mb: 3, alignItems: 'flex-start' }}
        action={
          <IconButton
            aria-label="Ocultar novedades"
            color="inherit"
            size="small"
            onClick={() => setDismissed(true)}
          >
            <CloseIcon fontSize="inherit" />
          </IconButton>
        }
      >
        <Typography variant="subtitle1" fontWeight={700} component="h2" gutterBottom>
          {heading}
        </Typography>
        <List dense disablePadding sx={{ width: '100%' }}>
          {items.map((item, index) => (
            <ListItem
              key={item.id}
              alignItems="flex-start"
              disableGutters
              sx={{
                py: 0.75,
                borderTop: index === 0 ? 0 : 1,
                borderColor: 'divider',
              }}
            >
              <ListItemText
                primary={
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, alignItems: 'baseline' }}>
                    <Typography variant="body1" fontWeight={600} component="span">
                      {item.title}
                    </Typography>
                    {item.date ? (
                      <Typography variant="caption" color="text.secondary" component="span">
                        {item.date}
                      </Typography>
                    ) : null}
                  </Box>
                }
                secondary={
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
                    {item.body}
                  </Typography>
                }
              />
            </ListItem>
          ))}
        </List>
      </Alert>
    </Collapse>
  );
};

export default AnnouncementsBanner;
