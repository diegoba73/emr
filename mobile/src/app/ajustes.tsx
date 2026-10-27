import { Alert } from 'react-native';
import React, { useState } from 'react';
import { useSession } from '../lib/session';
import { api } from '../lib/api';
import { enableReminders, pushUnavailableInExpoGo } from '../lib/notifications';
import { Action, Body, Card, ErrorText, Page, Title } from '../components/ui';

export default function Settings() {
  const { user, logout, changeClinic } = useSession();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const run = async (fn: () => Promise<void>, text: string) => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await fn();
      setMessage(text);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo completar la operación.');
    } finally {
      setBusy(false);
    }
  };
  const expoGoPush = pushUnavailableInExpoGo();

  return (
    <Page>
      <Title>Mi cuenta</Title>
      <Body>{user?.nombre}</Body>
      <ErrorText text={error} />
      {message && <Body>{message}</Body>}
      {user?.rol === 'paciente' && (
        <Card>
          <Title>Avisos y llamados</Title>
          <Body>
            Con la app abierta (o en segundo plano reciente), cuando el médico te llame el celular
            vibra y muestra el destino — no hace falta Expo Push para eso.
          </Body>
          {expoGoPush ? (
            <Body>
              Estás en Expo Go: el aviso por polling ya funciona. El push con la app cerrada
              requiere la APK de desarrollo (SYNESIS Dev).
            </Body>
          ) : (
            <Body>
              Opcional: activá también el push de Expo para avisos con la app cerrada y
              recordatorios del día anterior.
            </Body>
          )}
          <Action
            title={
              expoGoPush
                ? 'Probar alerta (vibración)'
                : 'Activar avisos push (app cerrada + recordatorios)'
            }
            disabled={busy}
            onPress={() =>
              run(
                async () => {
                  if (expoGoPush) {
                    const { handleLlamadoForeground } = await import('../lib/notifications');
                    handleLlamadoForeground(
                      { tipo: 'llamado_medico', destino: 'Consultorio (prueba)' },
                      'Prueba de llamado'
                    );
                    return;
                  }
                  await enableReminders();
                },
                expoGoPush
                  ? 'Si sentiste la vibración, los llamados del médico van a avisarte igual.'
                  : 'Avisos push activados en este celular.'
              )
            }
          />
          {!expoGoPush && (
            <Action
              title="Desactivar push en este celular"
              secondary
              disabled={busy}
              onPress={() =>
                run(async () => {
                  await api('/push/', 'DELETE');
                }, 'Avisos push desactivados.')
              }
            />
          )}
        </Card>
      )}
      <Body>
        La configuración de horarios de atención corresponde a secretaría y administración, desde
        el EMR.
      </Body>
      <Action
        title="Cambiar clínica"
        secondary
        disabled={busy}
        onPress={() =>
          Alert.alert(
            'Cambiar clínica',
            'Se cerrará tu sesión. Deberás ingresar con el usuario de la otra institución.',
            [
              { text: 'Volver', style: 'cancel' },
              { text: 'Continuar', onPress: () => run(changeClinic, '') },
            ]
          )
        }
      />
      <Action title="Cerrar sesión" secondary disabled={busy} onPress={() => run(logout, '')} />
    </Page>
  );
}
