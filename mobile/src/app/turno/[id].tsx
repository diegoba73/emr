import React, { useCallback, useRef, useState } from 'react';
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { Alert } from 'react-native';
import { api } from '../../lib/api';
import { AnuncioRecepcion, RecepcionHoy, Slot, Turno } from '../../lib/types';
import { useSession } from '../../lib/session';
import { dateKey } from '../../lib/calendar';
import { Action, Body, Card, ErrorText, Field, Loading, Page, Title } from '../../components/ui';

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
  const loadGen = useRef(0);
  const [reprogFecha, setReprogFecha] = useState('');
  const [reprogSlots, setReprogSlots] = useState<Slot[]>([]);
  const [showReprog, setShowReprog] = useState(false);

  const refresh = useCallback(async () => {
    const gen = ++loadGen.current;
    const turnoId = id;
    setNow(Date.now());
    setLoading(true);
    setError('');
    try {
      const data = await api<Turno>(`/turnos/${turnoId}/`);
      if (gen !== loadGen.current) return;
      setTurno(data);
      if (user?.rol === 'paciente') {
        const recepcion = await api<RecepcionHoy>('/recepcion/hoy/');
        if (gen !== loadGen.current) return;
        setRecepcionHoy(recepcion);
      }
    } catch (e) {
      if (gen !== loadGen.current) return;
      setTurno(null);
      setError(e instanceof Error ? e.message : 'No se pudo cargar el turno.');
    } finally {
      if (gen === loadGen.current) setLoading(false);
    }
  }, [id, user?.rol]);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  const run = async (fn: () => Promise<void | 'skip-refresh'>, fail: string) => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    try {
      const outcome = await fn();
      if (outcome !== 'skip-refresh') {
        await refresh();
      }
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
                title="Confirmar este turno"
                disabled={busy}
                onPress={() =>
                  Alert.alert(
                    'Confirmar este turno',
                    'Esto confirma la reserva en la agenda. Después, cerca del día, te pediremos confirmar que vas a asistir. Si no podés, cancelá desde acá o contactá a secretaría.',
                    [
                      { text: 'Volver', style: 'cancel' },
                      { text: 'Sí, confirmo el turno', onPress: () => void confirmarTurno() },
                    ]
                  )
                }
              />
            )}

            {activo &&
              user?.rol === 'paciente' &&
              turno.viene_de_pedido_estudio &&
              turno.medico_id && (
                <Card>
                  <Body>¿Otro día u horario? Elegí fecha y un slot libre del mismo médico.</Body>
                  {!showReprog ? (
                    <Action title="Pedir otro horario" secondary disabled={busy} onPress={() => setShowReprog(true)} />
                  ) : (
                    <>
                      <Field
                        label="Fecha (AAAA-MM-DD)"
                        value={reprogFecha}
                        onChangeText={(v) => {
                          setReprogFecha(v);
                          setReprogSlots([]);
                        }}
                        editable={!busy}
                      />
                      <Action
                        title="Ver horarios"
                        secondary
                        disabled={busy || !/^\d{4}-\d{2}-\d{2}$/.test(reprogFecha)}
                        onPress={() =>
                          void run(async () => {
                            const r = await api<{ slots: Slot[]; detail?: string }>(
                              `/turnos/${id}/slots-reprogramacion/?fecha=${reprogFecha}`
                            );
                            setReprogSlots(r.slots || []);
                            if (!(r.slots || []).length) {
                              throw new Error(
                                r.detail || 'No hay horarios libres compatibles con tu estudio ese día.'
                              );
                            }
                          }, 'No se pudieron cargar horarios.')
                        }
                      />
                      {reprogSlots.map((s) => (
                        <Action
                          key={s.inicio}
                          title={
                            s.recurso_nombre
                              ? `${new Date(s.inicio).toLocaleString('es-AR')} · ${s.recurso_nombre}`
                              : new Date(s.inicio).toLocaleString('es-AR')
                          }
                          disabled={busy}
                          onPress={() =>
                            Alert.alert('Reprogramar', `¿Pasar el turno a ${new Date(s.inicio).toLocaleString('es-AR')}?`, [
                              { text: 'Volver', style: 'cancel' },
                              {
                                text: 'Sí',
                                onPress: () =>
                                  void run(async () => {
                                    const nuevo = await api<Turno>(
                                      `/turnos/${id}/reprogramar-horario/`,
                                      'POST',
                                      {
                                        horario_id: s.horario_id,
                                        inicio: s.inicio,
                                        motivo: 'Reprogramado por el paciente (pedido de estudio)',
                                      }
                                    );
                                    loadGen.current += 1;
                                    setTurno(nuevo);
                                    setShowReprog(false);
                                    setReprogSlots([]);
                                    Alert.alert('Listo', 'Turno reprogramado.');
                                    router.replace({
                                      pathname: '/turno/[id]',
                                      params: { id: String(nuevo.id) },
                                    });
                                    return 'skip-refresh';
                                  }, 'No se pudo reprogramar.'),
                              },
                            ])
                          }
                        />
                      ))}
                    </>
                  )}
                </Card>
              )}

            {activo &&
              user?.rol === 'paciente' &&
              turno.estado === 'CONFIRMADO' &&
              !turno.asistencia_confirmada_en && (
                <Action
                  title="Voy a asistir"
                  disabled={busy}
                  onPress={() =>
                    Alert.alert(
                      'Confirmar asistencia',
                      '¿Confirmás que vas a venir a este turno? (No es el anuncio de llegada: eso es «Estoy en sala» el día del turno.)',
                      [
                        { text: 'Volver', style: 'cancel' },
                        { text: 'Sí, voy a asistir', onPress: () => void confirmarAsistencia() },
                      ]
                    )
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

            {activo && user?.rol === 'paciente' && (
              <Action
                title="Cancelar turno"
                secondary
                disabled={busy}
                onPress={() =>
                  Alert.alert(
                    'Cancelar turno',
                    '¿Cancelás este turno? El horario queda libre. Si necesitás otro día, después podés reservar de nuevo o contactar a secretaría.',
                    [
                      { text: 'Volver', style: 'cancel' },
                      {
                        text: 'Sí, cancelar',
                        style: 'destructive',
                        onPress: () =>
                          void run(async () => {
                            await api(`/turnos/${id}/cancelar/`, 'POST', {
                              motivo: 'Cancelado por el paciente desde la app',
                            });
                            Alert.alert('Listo', 'Turno cancelado.');
                            router.replace('/');
                          }, 'No se pudo cancelar el turno.'),
                      },
                    ]
                  )
                }
              />
            )}
            {activo && user?.rol === 'medico' && (
              <Card>
                <Body>Para cancelar o cambiar de día, pedile a secretaría.</Body>
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
