import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { Platform } from 'react-native';
import { api } from './api';
Notifications.setNotificationHandler({ handleNotification: async () => ({ shouldPlaySound: true, shouldSetBadge: false, shouldShowBanner: true, shouldShowList: true }) });
export async function enableReminders() {
  if (!Device.isDevice) throw new Error('Probá los recordatorios en un teléfono físico.');
  const projectId = Constants.expoConfig?.extra?.eas?.projectId || Constants.easConfig?.projectId;
  if (!projectId) throw new Error('Los recordatorios estarán disponibles cuando se complete la configuración de la app.');
  if (Platform.OS === 'android') await Notifications.setNotificationChannelAsync('turnos', { name: 'Recordatorios de turnos', importance: Notifications.AndroidImportance.HIGH });
  let permissions = await Notifications.getPermissionsAsync();
  if (permissions.status !== 'granted') permissions = await Notifications.requestPermissionsAsync();
  if (permissions.status !== 'granted') throw new Error('Para recibir recordatorios, habilitá las notificaciones en los ajustes del celular.');
  const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data;
  const result = await api<{servicio_activo:boolean}>('/push/', 'POST', { token, plataforma: Platform.OS });
  if (!result.servicio_activo) throw new Error('Celular registrado. El servicio de recordatorios todavía no está habilitado por la administración.');
}
