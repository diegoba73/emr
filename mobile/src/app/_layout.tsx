import React, { useEffect, useRef, useState } from 'react';
import { Stack, router } from 'expo-router';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { SessionProvider, useSession } from '../lib/session';
import { notificationTurnoId } from '../lib/calendar';
import { colors, Loading } from '../components/ui';
import {
  attachNotificationListeners,
  handleLlamadoForeground,
  isLlamadoNotification,
  tryEnablePushSilent,
} from '../lib/notifications';
import { startLlamadoPolling } from '../lib/llamadoPoll';

function Navigation() {
  const { user, clinic, loading } = useSession();
  const [pending, setPending] = useState<{ id: string; code: string } | null>(null);
  const clearLastRef = useRef<(() => Promise<void>) | null>(null);

  useEffect(() => {
    let remove: () => void = () => {};
    let cancelled = false;
    void attachNotificationListeners({
      onResponse: (data, body) => {
        if (isLlamadoNotification(data)) {
          handleLlamadoForeground(data, body);
          return;
        }
        const id = notificationTurnoId(data);
        const code = data?.institucion;
        if (id && typeof code === 'string') setPending({ id, code });
      },
      onReceived: (data, body) => {
        handleLlamadoForeground(data, body);
      },
    }).then((api) => {
      if (cancelled) {
        api.remove();
        return;
      }
      const initial = api.getPendingTurno();
      if (initial) setPending(initial);
      clearLastRef.current = api.clearLastResponse;
      remove = api.remove;
    });
    return () => {
      cancelled = true;
      clearLastRef.current = null;
      remove();
    };
  }, []);

  useEffect(() => {
    if (user && !loading && pending) {
      if (pending.code === clinic?.code) {
        router.push({ pathname: '/turno/[id]', params: { id: pending.id } });
      }
      void (clearLastRef.current?.() ?? Promise.resolve()).then(() => setPending(null));
    }
  }, [user, clinic, loading, pending]);

  // Paciente: push Expo si hay development build; siempre polling LAN (vibra al Llamar).
  useEffect(() => {
    if (!user || user.rol !== 'paciente') return;
    void tryEnablePushSilent();
    return startLlamadoPolling({ enabled: true, intervalMs: 4000 });
  }, [user?.id, user?.rol]);

  if (loading) return <Loading />;
  return (
    <Stack
      key={clinic?.code || 'unlinked'}
      screenOptions={{
        headerStyle: { backgroundColor: '#fff' },
        headerTintColor: colors.ink,
        headerTitleStyle: { fontWeight: '700' },
        contentStyle: { backgroundColor: colors.bg },
      }}
    >
      <Stack.Protected guard={!clinic}>
        <Stack.Screen name="institucion" options={{ headerShown: false }} />
      </Stack.Protected>
      <Stack.Protected guard={Boolean(clinic) && !user}>
        <Stack.Screen name="login" options={{ headerShown: false }} />
      </Stack.Protected>
      <Stack.Protected guard={Boolean(user)}>
        <Stack.Screen name="index" options={{ title: 'SYNESIS movil' }} />
        <Stack.Screen name="reservar" options={{ title: 'Elegir horario' }} />
        <Stack.Screen name="turno/[id]" options={{ title: 'Detalle del turno' }} />
        <Stack.Screen name="informes/index" options={{ title: 'Informes' }} />
        <Stack.Screen name="informes/[id]" options={{ title: 'Informe' }} />
        <Stack.Screen name="lab/index" options={{ title: 'Laboratorio' }} />
        <Stack.Screen name="lab/nueva" options={{ title: 'Nuevo pedido' }} />
        <Stack.Screen name="ajustes" options={{ title: 'Mi cuenta' }} />
      </Stack.Protected>
    </Stack>
  );
}

export default function Root() {
  return (
    <SafeAreaProvider>
      <SessionProvider>
        <Navigation />
      </SessionProvider>
    </SafeAreaProvider>
  );
}
