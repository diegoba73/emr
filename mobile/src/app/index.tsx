import React, { useCallback, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { useSession } from '../lib/session';
import { allPages, api } from '../lib/api';
import { AnuncioRecepcion, RecepcionHoy, Turno } from '../lib/types';
import { dateKey } from '../lib/calendar';
import Calendar from '../components/Calendar';
import { Action, Body, Card, colors, ErrorText, Loading, Page, Title } from '../components/ui';

export default function Home() {
  const [now, setNow] = useState(() => Date.now());
  const { user } = useSession();
  const puedeTurnos = Boolean(user?.puede_turnos ?? (user?.rol === 'paciente' || user?.rol === 'medico'));
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [loading, setLoading] = useState(puedeTurnos || user?.rol === 'paciente');
  const [error, setError] = useState('');
  const [fecha, setFecha] = useState(dateKey(new Date()));
  const [porDia, setPorDia] = useState(user?.rol === 'medico');
  const [recepcionHoy, setRecepcionHoy] = useState<RecepcionHoy | null>(null);
  const [busyAnuncio, setBusyAnuncio] = useState(false);

  const refresh = useCallback(async () => {
    setNow(Date.now());
    setLoading(true);
    setError('');
    try {
      if (puedeTurnos) {
        setTurnos(await allPages<Turno>('/turnos/'));
      }
      if (user?.rol === 'paciente') {
        setRecepcionHoy(await api<RecepcionHoy>('/recepcion/hoy/'));
      } else {
        setRecepcionHoy(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo consultar la agenda.');
    } finally {
      setLoading(false);
    }
  }, [puedeTurnos, user?.rol]);

  const mostrarAnuncio = (data: AnuncioRecepcion, titulo: string) => {
    Alert.alert(
      titulo,
      data.codigo_llamado
        ? `${data.mensaje}\n\nCódigo: ${data.codigo_llamado}`
        : data.mensaje
    );
  };

  const estoyEnSala = useCallback(async () => {
    setBusyAnuncio(true);
    setError('');
    try {
      const data = await api<AnuncioRecepcion>('/recepcion/estoy-en-sala/', 'POST', {});
      mostrarAnuncio(data, 'Estoy en sala');
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo anunciarte en recepción.');
    } finally {
      setBusyAnuncio(false);
    }
  }, [refresh]);

  const anuncioLab = useCallback(async () => {
    setBusyAnuncio(true);
    setError('');
    try {
      const data = await api<AnuncioRecepcion>('/recepcion/anuncio-lab/', 'POST', {});
      mostrarAnuncio(data, 'Laboratorio');
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo anunciarte al laboratorio.');
    } finally {
      setBusyAnuncio(false);
    }
  }, [refresh]);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  const visibles = turnos.filter((t) =>
    porDia
      ? dateKey(new Date(t.fecha_hora_inicio)) === fecha
      : new Date(t.fecha_hora_inicio).getTime() > now && t.estado !== 'CANCELADO'
  );
  const turnoActivoPaciente =
    user?.rol === 'paciente'
      ? turnos.find(
          (t) =>
            new Date(t.fecha_hora_inicio).getTime() > now &&
            (t.estado === 'RESERVADO' || t.estado === 'CONFIRMADO')
        )
      : undefined;

  return (
    <Page>
      <View style={{ gap: 6 }}>
        <Body>{user?.nombre}</Body>
        <Title>{puedeTurnos ? (user?.rol === 'medico' ? 'Mi agenda' : 'Mis turnos') : 'Inicio'}</Title>
      </View>

      <View style={{ flexDirection: 'row', gap: 10 }}>
        {puedeTurnos && (
          <View style={{ flex: 1 }}>
            <Action
              secondary
              title={porDia ? 'Ver próximos' : 'Ver calendario'}
              onPress={() => setPorDia((v) => !v)}
            />
          </View>
        )}
        <View style={{ flex: 1 }}>
          <Action secondary title="Mi cuenta" onPress={() => router.push('/ajustes')} />
        </View>
      </View>

      <Action title="Informes de laboratorio" onPress={() => router.push('/informes')} />
      {(user?.rol === 'paciente' || user?.rol === 'medico') && (
        <Action title="Estudios" onPress={() => router.push('/estudios')} />
      )}
      {user?.rol === 'paciente' && (
        <Action title="Consultas pasadas" onPress={() => router.push('/consultas')} />
      )}
      {user?.puede_pedir_lab && (
        <Action title="Pedir laboratorio" onPress={() => router.push('/lab')} />
      )}

      {user?.rol === 'paciente' && (
        <Card>
          <Body>
            Cuando llegues a la clínica: anunciate acá. Secretaría te llama para el registro
            administrativo; el médico te llama después.
          </Body>
          {recepcionHoy?.estoy_en_sala ? (
            <Body>
              Ya estás en sala
              {recepcionHoy.estoy_en_sala.codigo_llamado
                ? ` · código ${recepcionHoy.estoy_en_sala.codigo_llamado}`
                : ''}
              .
            </Body>
          ) : recepcionHoy?.puedo_estoy_en_sala ? (
            <Action
              title="Estoy en sala"
              disabled={busyAnuncio}
              onPress={() => void estoyEnSala()}
            />
          ) : null}
          {recepcionHoy?.lab ? (
            <Body>
              Laboratorio
              {recepcionHoy.lab.codigo_llamado
                ? ` · código ${recepcionHoy.lab.codigo_llamado}`
                : ''}
              .
            </Body>
          ) : (
            <Action
              title="Anunciarme al laboratorio"
              secondary
              disabled={busyAnuncio}
              onPress={() => void anuncioLab()}
            />
          )}
        </Card>
      )}

      {user?.rol === 'paciente' && !turnoActivoPaciente && (
        <Action title="Reservar un turno" onPress={() => router.push('/reservar')} />
      )}
      {user?.rol === 'paciente' && turnoActivoPaciente && (
        <Card>
          <Body>
            Ya tenés un turno el{' '}
            {new Date(turnoActivoPaciente.fecha_hora_inicio).toLocaleString('es-AR')}. No
            podés sacar otro desde la app; si necesitás cambiarlo, contactá a secretaría.
          </Body>
          {turnoActivoPaciente.estado === 'RESERVADO' && (
            <Body>Pendiente de confirmación: abrí el turno y confirmalo.</Body>
          )}
          <Action
            secondary
            title="Ver turno"
            onPress={() =>
              router.push({
                pathname: '/turno/[id]',
                params: { id: String(turnoActivoPaciente.id) },
              })
            }
          />
        </Card>
      )}

      {puedeTurnos && (
        <>
          {porDia && (
            <Card>
              <Calendar value={fecha} onChange={setFecha} />
            </Card>
          )}
          <ErrorText text={error} />
          {loading ? (
            <Loading />
          ) : (
            <>
              {!visibles.length && (
                <Card>
                  <Body>No hay turnos {porDia ? 'para este día' : 'próximos'}.</Body>
                </Card>
              )}
              {visibles.map((t) => (
                <Card key={t.id}>
                  <Text style={{ fontWeight: '700', fontSize: 17, color: colors.ink }}>
                    {new Date(t.fecha_hora_inicio).toLocaleString('es-AR', {
                      weekday: 'short',
                      day: 'numeric',
                      month: 'short',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </Text>
                  <Body>
                    {user?.rol === 'medico' ? t.paciente_nombre : t.medico_nombre} ·{' '}
                    {t.tipo === 'ESTUDIO' ? 'Estudio' : 'Consulta'}
                  </Body>
                  <Body>
                    {t.estado} ·{' '}
                    {t.asistencia_confirmada_en
                      ? 'Asistencia confirmada'
                      : t.estado === 'CONFIRMADO'
                        ? 'Sin respuesta de asistencia'
                        : 'Pendiente de confirmación'}
                  </Body>
                  <Action
                    secondary
                    title="Ver turno"
                    onPress={() => router.push({ pathname: '/turno/[id]', params: { id: String(t.id) } })}
                  />
                </Card>
              ))}
            </>
          )}
          <Action title="Actualizar agenda" secondary disabled={loading} onPress={refresh} />
        </>
      )}

      {!puedeTurnos && (
        <Card>
          <Body>
            Con tu rol ({user?.rol}) podés consultar informes de laboratorio
            {user?.rol === 'bioquimico' ? ' y validar u informar parcialmente' : ''}.
          </Body>
        </Card>
      )}
    </Page>
  );
}
