import React, { useEffect, useState } from 'react';
import { Stack, router } from 'expo-router';
import * as Notifications from 'expo-notifications';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { SessionProvider, useSession } from '../lib/session';
import { notificationTurnoId } from '../lib/calendar';
import { colors, Loading } from '../components/ui';
import '../lib/notifications';
function Navigation() {
  const { user, clinic, loading } = useSession();
  const [pending, setPending] = useState<{id:string;code:string} | null>(null);
  useEffect(() => {
    const read = (response: Notifications.NotificationResponse) => {
      const id = notificationTurnoId(response.notification.request.content.data);
      const code = response.notification.request.content.data?.institucion;
      if (id && typeof code === 'string') setPending({id,code});
    };
    const initial = Notifications.getLastNotificationResponse();
    if (initial) read(initial);
    const listener = Notifications.addNotificationResponseReceivedListener(read);
    return () => listener.remove();
  }, []);
  useEffect(() => {
    if (user && !loading && pending) {
      if (pending.code === clinic?.code) router.push({ pathname: '/turno/[id]', params: { id: pending.id } });
      void Notifications.clearLastNotificationResponseAsync().then(() => setPending(null));
    }
  }, [user, clinic, loading, pending]);
  if (loading) return <Loading />;
  return <Stack key={clinic?.code || 'unlinked'} screenOptions={{ headerStyle: { backgroundColor: '#fff' }, headerTintColor: colors.ink, headerTitleStyle: { fontWeight:'700' }, contentStyle: { backgroundColor:colors.bg } }}>
    <Stack.Protected guard={!clinic}><Stack.Screen name="institucion" options={{headerShown:false}} /></Stack.Protected>
    <Stack.Protected guard={Boolean(clinic) && !user}><Stack.Screen name="login" options={{ headerShown:false }} /></Stack.Protected>
    <Stack.Protected guard={Boolean(user)}>
      <Stack.Screen name="index" options={{ title:'SYNESIS movil' }} />
      <Stack.Screen name="reservar" options={{ title:'Elegir horario' }} />
      <Stack.Screen name="turno/[id]" options={{ title:'Detalle del turno' }} />
      <Stack.Screen name="ajustes" options={{ title:'Mi cuenta' }} />
    </Stack.Protected>
  </Stack>;
}
export default function Root() { return <SafeAreaProvider><SessionProvider><Navigation /></SessionProvider></SafeAreaProvider>; }
