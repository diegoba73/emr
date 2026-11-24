import React, { useCallback, useRef, useState } from 'react';
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { Alert } from 'react-native';
import { api } from '../../lib/api';
import { AnuncioRecepcion, RecepcionHoy, Turno } from '../../lib/types';
import { useSession } from '../../lib/session';
import { dateKey } from '../../lib/calendar';
import { Action, Body, Card, ErrorText, Loading, Page, Title } from '../../components/ui';
import { formatFechaHoraDisplay, formatHoraDisplay } from '../../utils/dateFieldFormat';
import { useLiveRefresh } from '../../lib/useLiveRefresh';
import { enVentanaEstoyEnSala } from '../../lib/estoyEnSala';

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

  const refresh = useCallback(async (opts?: { silent?: boolean }) => {
    const gen = ++loadGen.current;
    const turnoId = id;
    setNow(Date.now());
    if (!opts?.silent) {
      setLoading(true);
      setError('');
    }
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
      if (!opts?.silent) {
        setTurno(null);
        setError(e instanceof Error ? e.message : 'No se pudo cargar el turno.');
      }
    } finally {
      if (gen === loadGen.current && !opts?.silent) setLoading(false);
    }
  }, [id, user?.rol]);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  useLiveRefresh(() => refresh({ silent: true }), {
    enabled: Boolean(id),
    getRevision: async () => {
      const data = await api<{ revision: string }>('/turnos/revision/');
      return data.revision;
    },
  });

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

  const estadoRecepcionTurno = recepcionHoy?.turnos_estoy_en_sala?.find(
    (x) => x.turno_id === turno?.id
  );
  const puedeEstoyEnSala =
    user?.rol === 'paciente' &&
    Boolean(turno) &&
    ['RESERVADO', 'CONFIRMADO'].includes(turno!.estado) &&
    enVentanaEstoyEnSala(turno!.fecha_hora_inicio, now) &&
    (estadoRecepcionTurno
      ? estadoRecepcionTurno.puedo_estoy_en_sala
      : Boolean(recepcionHoy?.puedo_estoy_en_sala && recepcionHoy.turno_hoy_id === turno!.id));

  const esEstudio =
    Boolean(turno?.viene_de_pedido_estudio) || Boolean(turno?.estudio_complementario?.id);
  const pideAceptacion = Boolean(turno?.requiere_aceptacion_paciente);
  const puedeAceptarOConfirmar =
    Boolean(activo) &&
    user?.rol === 'paciente' &&
    turno?.estado === 'RESERVADO' &&
    (!esEstudio || pideAceptacion);
  const puedeRechazarReprogramacion =
    Boolean(activo) && user?.rol === 'paciente' && Boolean(turno?.puede_cancelar) && pideAceptacion;
  const puedeReprogramar =
    Boolean(activo) && user?.rol === 'paciente' && Boolean(turno?.puede_reprogramar);
  const mostrarAyudaCancel =
    Boolean(activo) &&
    user?.rol === 'paciente' &&
    !pideAceptacion &&
    !esEstudio;

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
              {turno.tipo === 'ESTUDIO' && (
                <Body>
                  {turno.estudio_nombre ||
                    turno.estudio_complementario?.tipo_estudio_nombre ||
                    (turno.motivo_reserva
                      ? turno.motivo_reserva.replace(/^(Estudio|Procedimiento)\s*:\s*/i, '')
                      : 'Estudio')}
                </Body>
              )}
              <Body>
                {formatHoraDisplay(new Date(turno.fecha_hora_inicio))} · {turno.medico_nombre}
              </Body>
              {user?.rol === 'medico' && <Body>{turno.paciente_nombre}</Body>}
              <Body>Estado: {turno.estado}</Body>
              <Body>
                {pideAceptacion
                  ? 'Secretaría reprogramó este turno: aceptá o rechazá el nuevo horario.'
                  : turno.asistencia_confirmada_en
                    ? 'El paciente confirmó su asistencia.'
                    : turno.estado === 'CONFIRMADO'
                      ? 'La asistencia todavía no fue confirmada por el paciente.'
                      : 'Primero hay que confirmar el turno; después se pide la asistencia.'}
              </Body>
            </Card>

            {puedeAceptarOConfirmar && (
              <Action
                title={pideAceptacion ? 'Aceptar nuevo horario' : 'Confirmar este turno'}
                disabled={busy}
                onPress={() =>
                  Alert.alert(
                    pideAceptacion ? 'Aceptar nuevo horario' : 'Confirmar este turno',
                    pideAceptacion
                      ? 'Secretaría cambió tu turno a este horario. ¿Estás de acuerdo? Si no, rechazalo con «Rechazar nuevo horario».'
                      : 'Esto confirma la reserva en la agenda. Después, cerca del día, te pediremos confirmar que vas a asistir. Si no podés venir, contactá a secretaría para cancelar.',
                    [
                      { text: 'Volver', style: 'cancel' },
                      {
                        text: pideAceptacion ? 'Sí, acepto el horario' : 'Sí, confirmo el turno',
                        onPress: () => void confirmarTurno(),
                      },
                    ]
                  )
                }
              />
            )}

            {activo && user?.rol === 'paciente' && esEstudio && !pideAceptacion && (
              <Card>
                <Body>
                  Este turno de estudio lo gestiona secretaría. Si necesitás cambiarlo, contactalos
                  (presencial o por teléfono).
                </Body>
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

            {puedeReprogramar && (
              <Action
                title="Reprogramar"
                disabled={busy}
                onPress={() =>
                  router.push({
                    pathname: '/reservar',
                    params: { reprogramar: String(id) },
                  })
                }
              />
            )}
            {mostrarAyudaCancel && !puedeReprogramar && Boolean(turno?.motivo_bloqueo_reprogramar) && (
              <Card>
                <Body>{turno?.motivo_bloqueo_reprogramar}</Body>
              </Card>
            )}
            {mostrarAyudaCancel && (
              <Card>
                <Body>
                  Para cancelar el turno contactá a secretaría (presencial o por teléfono). Desde la
                  app no se cancela.
                </Body>
              </Card>
            )}
            {puedeRechazarReprogramacion && (
              <Action
                title="Rechazar nuevo horario"
                secondary
                disabled={busy}
                onPress={() =>
                  Alert.alert(
                    'Rechazar nuevo horario',
                    '¿Rechazás el horario que propuso secretaría? El turno se cancela y el horario queda libre. Después podés pedir otro turno o contactar a secretaría.',
                    [
                      { text: 'Volver', style: 'cancel' },
                      {
                        text: 'Sí, rechazar',
                        style: 'destructive',
                        onPress: () =>
                          void run(async () => {
                            await api(`/turnos/${id}/cancelar/`, 'POST', {
                              motivo: 'Paciente rechazó el horario reprogramado desde la app',
                            });
                            Alert.alert(
                              'Listo',
                              'Rechazaste el nuevo horario. El turno quedó cancelado.'
                            );
                            router.replace('/');
                          }, 'No se pudo rechazar el horario.'),
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
