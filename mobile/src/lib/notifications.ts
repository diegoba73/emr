import { isRunningInExpoGo } from 'expo';
import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { Alert, Platform, Vibration } from 'react-native';
import { api } from './api';

type NotificationsModule = typeof import('expo-notifications');

const expoGo = isRunningInExpoGo();

let notificationsPromise: Promise<NotificationsModule | null> | null = null;

/** En Expo Go (Android SDK 53+) no se puede ni importar el módulo de push. */
function loadNotifications(): Promise<NotificationsModule | null> {
  if (expoGo) return Promise.resolve(null);
  if (!notificationsPromise) {
    notificationsPromise = import('expo-notifications').then((Notifications) => {
      Notifications.setNotificationHandler({
        handleNotification: async () => ({
          shouldPlaySound: true,
          shouldSetBadge: false,
          shouldShowBanner: true,
          shouldShowList: true,
        }),
      });
      return Notifications;
    });
  }
  return notificationsPromise;
}

void loadNotifications();

async function ensureTurnosChannel(Notifications: NotificationsModule) {
  if (Platform.OS !== 'android') return;
  await Notifications.setNotificationChannelAsync('turnos', {
    name: 'Turnos y llamados',
    importance: Notifications.AndroidImportance.MAX,
    vibrationPattern: [0, 400, 120, 400, 120, 400, 800],
    sound: 'default',
    enableVibrate: true,
  });
}

export function isLlamadoNotification(data: Record<string, unknown> | undefined): boolean {
  const tipo = data?.tipo;
  return tipo === 'llamado_medico' || tipo === 'llamado_recepcion';
}

let llamadoAlertActivo = false;
let vibracionInterval: ReturnType<typeof setInterval> | null = null;
let speechLoop = false;

function stopLlamadoAlerta() {
  llamadoAlertActivo = false;
  speechLoop = false;
  try {
    Vibration.cancel();
  } catch {
    /* ignore */
  }
  if (vibracionInterval) {
    clearInterval(vibracionInterval);
    vibracionInterval = null;
  }
  void import('expo-speech')
    .then((Speech) => Speech.stop())
    .catch(() => undefined);
}

function startLlamadoVibracion() {
  const pattern = [0, 500, 180, 500, 180, 500, 180, 900];
  try {
    if (Platform.OS === 'android') {
      // true = repetir hasta Vibration.cancel()
      Vibration.vibrate(pattern, true);
    } else {
      Vibration.vibrate(pattern);
      vibracionInterval = setInterval(() => {
        try {
          Vibration.vibrate(pattern);
        } catch {
          /* ignore */
        }
      }, 2200);
    }
  } catch {
    /* ignore */
  }
}

function startLlamadoSonido(mensaje: string) {
  speechLoop = true;
  const speak = () => {
    if (!speechLoop) return;
    void import('expo-speech')
      .then((Speech) => {
        if (!speechLoop) return;
        Speech.speak(mensaje, {
          language: 'es-AR',
          rate: 0.95,
          pitch: 1.05,
          onDone: () => {
            if (speechLoop) setTimeout(speak, 400);
          },
          onStopped: () => undefined,
          onError: () => {
            if (speechLoop) setTimeout(speak, 1200);
          },
        });
      })
      .catch(() => undefined);
  };
  speak();
}

/** Alerta en primer plano: vibra + habla en bucle hasta «Ya voy». */
export function handleLlamadoForeground(data: Record<string, unknown> | undefined, body?: string) {
  if (!isLlamadoNotification(data)) return;
  if (llamadoAlertActivo) return;

  const destino = typeof data?.destino === 'string' ? data.destino : '';
  const mensaje =
    destino ? `Te están llamando. Andá a ${destino}.` : body || 'Te están llamando. Acercate al consultorio.';

  llamadoAlertActivo = true;
  startLlamadoVibracion();
  startLlamadoSonido(mensaje);

  Alert.alert(
    'Te están llamando',
    mensaje,
    [
      {
        text: 'Ya voy',
        onPress: () => {
          stopLlamadoAlerta();
          // Avisa al backend para sacar el destacado de la TV.
          void api('/llamado-activo/', 'POST', {}).catch(() => undefined);
        },
      },
    ],
    { cancelable: false }
  );
}

export function pushUnavailableInExpoGo(): boolean {
  return expoGo;
}

export async function enableReminders() {
  if (expoGo) {
    throw new Error(
      'Los avisos push no funcionan en Expo Go (SDK 53+). Hace falta un development build de la app.'
    );
  }
  if (!Device.isDevice) throw new Error('Probá los avisos en un teléfono físico.');
  const Notifications = await loadNotifications();
  if (!Notifications) {
    throw new Error('Los avisos no están disponibles en este entorno.');
  }
  const projectId =
    Constants.expoConfig?.extra?.eas?.projectId || Constants.easConfig?.projectId;
  if (!projectId) {
    throw new Error('Los avisos estarán disponibles cuando se complete la configuración de la app.');
  }
  await ensureTurnosChannel(Notifications);
  let permissions = await Notifications.getPermissionsAsync();
  if (permissions.status !== 'granted') {
    permissions = await Notifications.requestPermissionsAsync();
  }
  if (permissions.status !== 'granted') {
    throw new Error(
      'Para recibir llamados y recordatorios, habilitá las notificaciones en los ajustes del celular.'
    );
  }
  const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
  const result = await api<{ servicio_activo: boolean }>('/push/', 'POST', {
    token,
    plataforma: Platform.OS,
  });
  if (!result.servicio_activo) {
    throw new Error(
      'Celular registrado. El servicio de avisos todavía no está habilitado por la administración (MOBILE_PUSH_ENABLED).'
    );
  }
}

/** Intento best-effort al iniciar sesión como paciente (no bloquea el login). */
export async function tryEnablePushSilent(): Promise<boolean> {
  try {
    await enableReminders();
    return true;
  } catch {
    return false;
  }
}

export type NotificationSubscription = { remove: () => void };

/** Listeners de notificación; no-op en Expo Go. */
export async function attachNotificationListeners(handlers: {
  onResponse: (data: Record<string, unknown>, body?: string) => void;
  onReceived: (data: Record<string, unknown>, body?: string) => void;
}): Promise<{
  getPendingTurno: () => { id: string; code: string } | null;
  clearLastResponse: () => Promise<void>;
  remove: () => void;
}> {
  const empty = {
    getPendingTurno: () => null as { id: string; code: string } | null,
    clearLastResponse: async () => undefined,
    remove: () => undefined,
  };
  const Notifications = await loadNotifications();
  if (!Notifications) return empty;

  const { notificationTurnoId } = await import('./calendar');

  const readResponse = (response: import('expo-notifications').NotificationResponse) => {
    const data = response.notification.request.content.data as Record<string, unknown>;
    const body = response.notification.request.content.body || undefined;
    handlers.onResponse(data, body);
  };

  const initial = Notifications.getLastNotificationResponse();
  let pending: { id: string; code: string } | null = null;
  if (initial) {
    const data = initial.notification.request.content.data as Record<string, unknown>;
    if (!isLlamadoNotification(data)) {
      const id = notificationTurnoId(data);
      const code = data?.institucion;
      if (id && typeof code === 'string') pending = { id, code };
    } else {
      readResponse(initial);
    }
  }

  const responseListener = Notifications.addNotificationResponseReceivedListener(readResponse);
  const receivedListener = Notifications.addNotificationReceivedListener((notification) => {
    const data = notification.request.content.data as Record<string, unknown>;
    handlers.onReceived(data, notification.request.content.body || undefined);
  });

  return {
    getPendingTurno: () => pending,
    clearLastResponse: () => Notifications.clearLastNotificationResponseAsync(),
    remove: () => {
      responseListener.remove();
      receivedListener.remove();
    },
  };
}
