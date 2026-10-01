import React, { useMemo, useState } from 'react';
import { Image, Linking, Pressable, Text, View } from 'react-native';
import { useSession } from '../lib/session';
import { catalogue } from '../lib/catalogue';
import { Action, Body, Card, ErrorText, Page, Title, colors } from '../components/ui';
import type { Clinic } from '../lib/clinics';

const brandLogo = require('../../assets/plandigital-mark.jpg');

export default function Institution() {
  const { link } = useSession();
  const clinics = useMemo(() => catalogue(), []);
  const [selected, setSelected] = useState<Clinic | null>(clinics.length === 1 ? clinics[0] : null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const year = new Date().getFullYear();

  const submit = async () => {
    if (busy || !selected) return;
    setBusy(true);
    setError('');
    try {
      await link(selected.code);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo vincular la clínica.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page showClinic={false}>
      <View style={{ alignItems: 'center', gap: 10, paddingTop: 24, paddingBottom: 8 }}>
        <Image
          source={brandLogo}
          accessibilityLabel="Plan Digital"
          style={{ width: 140, height: 140 }}
          resizeMode="contain"
        />
        <Text style={{ fontWeight: '900', fontSize: 18, color: colors.primary, letterSpacing: 2 }}>
          SYNESIS movil
        </Text>
        <Text style={{ color: colors.muted, fontSize: 13 }}>Plan Digital</Text>
      </View>

      <Title>Clínica o institución</Title>
      <Body>Elegí tu institución para continuar con el acceso.</Body>

      <Card>
        {clinics.length === 0 && (
          <Body>No hay instituciones configuradas en esta versión de la app.</Body>
        )}
        {clinics.map((c) => {
          const active = selected?.code === c.code;
          return (
            <Pressable
              key={c.code}
              accessibilityRole="button"
              accessibilityState={{ selected: active }}
              disabled={busy}
              onPress={() => setSelected(c)}
              style={{
                borderWidth: 1.5,
                borderColor: active ? colors.primary : colors.border,
                backgroundColor: active ? '#e8f7f8' : '#fff',
                borderRadius: 14,
                padding: 14,
                gap: 4,
              }}
            >
              <Text style={{ fontWeight: '700', fontSize: 17, color: colors.ink }}>{c.name}</Text>
              <Text style={{ color: colors.muted, fontSize: 13 }}>Código {c.code}</Text>
            </Pressable>
          );
        })}
        <ErrorText text={error} />
        <Action
          title={busy ? 'Vinculando…' : 'Continuar'}
          disabled={busy || !selected}
          onPress={submit}
        />
      </Card>

      <View style={{ marginTop: 24, alignItems: 'center', gap: 6 }}>
        <Pressable
          accessibilityRole="link"
          onPress={() => {
            void Linking.openURL('https://plandigital.com.ar');
          }}
        >
          <Text style={{ color: colors.primary, fontWeight: '600', fontSize: 15 }}>
            plandigital.com.ar
          </Text>
        </Pressable>
        <Text style={{ color: colors.muted, fontSize: 13, textAlign: 'center' }}>
          © 2015–{year} Plan Digital
        </Text>
      </View>
    </Page>
  );
}
