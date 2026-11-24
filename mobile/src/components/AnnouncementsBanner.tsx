import React, { useMemo, useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import {
  AnnouncementAudience,
  getActiveAnnouncements,
} from '../lib/announcements';
import { Body, Card, colors, Title } from './ui';

export interface AnnouncementsBannerProps {
  audience?: AnnouncementAudience;
  heading?: string;
}

/**
 * Banner de novedades en el inicio móvil (espejo del web).
 * Se puede ocultar durante la sesión actual.
 */
export default function AnnouncementsBanner({
  audience = 'all',
  heading = 'Novedades',
}: AnnouncementsBannerProps) {
  const items = useMemo(() => getActiveAnnouncements(audience) || [], [audience]);
  const [dismissed, setDismissed] = useState(false);

  if (!items.length || dismissed) {
    return null;
  }

  return (
    <Card>
      <View
        style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}
        accessibilityLabel="Novedades"
      >
        <Title>{heading}</Title>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Ocultar novedades"
          onPress={() => setDismissed(true)}
          hitSlop={8}
          style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1, padding: 4 })}
        >
          <Text style={{ color: colors.muted, fontSize: 18, fontWeight: '700' }}>×</Text>
        </Pressable>
      </View>
      {items.map((item, index) => (
        <View
          key={item.id}
          style={{
            gap: 4,
            paddingTop: index === 0 ? 0 : 10,
            borderTopWidth: index === 0 ? 0 : 1,
            borderTopColor: colors.border,
          }}
        >
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8, alignItems: 'baseline' }}>
            <Text style={{ color: colors.ink, fontWeight: '700', fontSize: 16 }}>{item.title}</Text>
            {item.date ? (
              <Text style={{ color: colors.muted, fontSize: 12 }}>{item.date}</Text>
            ) : null}
          </View>
          <Body>{item.body}</Body>
        </View>
      ))}
    </Card>
  );
}
