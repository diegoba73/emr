import React, { useCallback, useRef, useState } from 'react';
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { Alert } from 'react-native';
import { api } from '../../lib/api';
import { AnuncioRecepcion, RecepcionHoy, Turno } from '../../lib/types';
import { useSession } from '../../lib/session';
import { dateKey } from '../../lib/calendar';
import { Action, Body, Card, ErrorText, Loading, Page, Title } from '../../components/ui';

export default function Detail() {
  const [now, setNow] = useState(() => Date.now());
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useSession();
  const [turno, setTurno] = useState<Turno | null>(null);
  const [recepcionHoy, setRecepcionHoy] = useState<RecepcionHoy | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const lock = useRef(false);

  const refresh = useCallback(async () => {
    setNow(Date.now());
    setLoading(true);
    setError('');
    try {
      setTurno(await api<Turno>(`/turnos/${id}/`));
      if (user?.rol === 'paciente') {
        setRecepcionHoy(await api<RecepcionHoy>('/recepcion/hoy/'));
      }
    } catch (e) {
      setTurno(null);
      setError(e instanceof Error ? e.message : 'No se pudo cargar el turno.');
    } finally {
      setLoading(false);
    }
  }, [id, user?.rol]);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  const run = async (fn: () => Promise<void>, fail: string) => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    try {
      await fn();
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : fail);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };

  const confirmarTurno = () =>
    run(async () => {
      await api(`/turnos/${id}/confirmar/`, 'POST', {});
    }, 'No se pudo confirmar el turno.');

  const confirmarAsistencia = () =>
    run(async () => {
      await api(`/turnos/${id}/asistencia/`, 'POST', {});
    }, 'No se pudo confirmar la asistencia.');

  const estoyEnSala = () =>
    run(async () => {
      const data = await api<AnuncioRecepcion>('/recepcion/estoy-en-sala/', 'POST', {
        turno_id: Number(id),
      });
      Alert.alert(
        'Estoy en sala',
        data.codigo_llamado
          ? `${data.mensaje}\n\nCódigo: ${data.codigo_llamado}`
          : data.mensaje
      );
    }, 'No se pudo anunciarte en recepción.');

  const activo =
    turno &&
    ['RESERVADO', 'CONFIRMADO'].includes(turno.estado) &&
    new Date(turno.fecha_hora_inicio).getTime() > now;

  const esHoy =
    turno && dateKey(new Date(turno.fecha_hora_inicio)) === dateKey(new Date());

  const puedeEstoyEnSala =
    user?.rol === 'paciente' &&
    esHoy &&
    turno &&
    ['RESERVADO', 'CONFIRMADO'].includes(turno.estado) &&
    recepcionHoy?.puedo_estoy_en_sala &&
    recepcionHoy.turno_hoy_id === turno.id;

  return (
    <Page>
      <ErrorText text={error} />
      {loading ? (
        <Loading />
      ) : (
        turno && (
          <>
            <Title>{turno.tipo === 'ESTUDIO' ? 'Estudio' : 'Consulta'}</Title>
            <Card>
              <Title>
                {new Date(turno.fecha_hora_inicio).toLocaleDateString('es-AR', {
                  weekday: 'long',
                  day: 'numeric',
                  month: 'long',
                })}
              </Title>
              <Body>
                {new Date(turno.fecha_hora_inicio).toLocaleTimeString('es-AR', {
                  hour: '2-digit',
                  minute: '2-digit',
                })}{' '}
                · {turno.medico_nombre}
              </Body>
              {user?.rol === 'medico' && <Body>{turno.paciente_nombre}</Body>}
              <Body>Estado: {turno.estado}</Body>
              <Body>
                {turno.asistencia_confirmada_en
                  ? 'El paciente confirmó su asistencia.'
                  : turno.estado === 'CONFIRMADO'
                    ? 'La asistencia todavía no fue confirmada por el paciente.'
                    : 'Primero hay que confirmar el turno; después se pide la asistencia.'}
              </Body>
            </Card>

            {activo && user?.rol === 'paciente' && turno.estado === 'RESERVADO' && (
              <Action
                title="Confirmar turno"
                disabled={busy}
                onPress={() =>
                  Alert.alert(
                    'Confirmar turno',
                    '¿Confirmás que vas a asistir en esta fecha? Si no podés, contactá a secretaría para liberar el horario.',
                    [
                      { text: 'Volver', style: 'cancel' },
                      { text: 'Sí, confirmo', onPress: () => void confirmarTurno() },
                    ]
                  )
                }
              />
            )}

            {activo &&
              user?.rol === 'paciente' &&
              turno.estado === 'CONFIRMADO' &&
              !turno.asistencia_confirmada_en && (
                <Action
                  title="Confirmar mi asistencia"
                  disabled={busy}
                  onPress={() =>
                    Alert.alert('Confirmar asistencia', '¿Vas a asistir a este turno?', [
                      { text: 'Volver', style: 'cancel' },
                      { text: 'Sí, voy a asistir', onPress: () => void confirmarAsistencia() },
                    ])
                  }
                />
              )}

            {puedeEstoyEnSala && (
              <Action title="Estoy en sala" disabled={busy} onPress={() => void estoyEnSala()} />
            )}
            {user?.rol === 'paciente' &&
              esHoy &&
              recepcionHoy?.estoy_en_sala &&
              recepcionHoy.turno_hoy_id === turno.id && (
                <Card>
                  <Body>
                    Ya estás anunciado
                    {recepcionHoy.estoy_en_sala.codigo_llamado
                      ? ` · código ${recepcionHoy.estoy_en_sala.codigo_llamado}`
                      : ''}
                    . Esperá el llamado de recepción.
                  </Body>
                </Card>
              )}

            {activo && (
              <Card>
                <Body>
                  Para cancelar o cambiar de día el turno, contactá a secretaría.
                </Body>
              </Card>
            )}
          </>
        )
      )}
      <Action title="Actualizar" secondary disabled={busy || loading} onPress={refresh} />
      <Action
        title="Volver a mi agenda"
        secondary
        disabled={busy}
        onPress={() => router.replace('/')}
      />
    </Page>
  );
}
