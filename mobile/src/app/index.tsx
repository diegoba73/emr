import React, { useCallback, useState } from 'react';
import { Text, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { useSession } from '../lib/session';
import { allPages } from '../lib/api';
import { Turno } from '../lib/types';
import { dateKey } from '../lib/calendar';
import Calendar from '../components/Calendar';
import { Action, Body, Card, colors, ErrorText, Loading, Page, Title } from '../components/ui';

export default function Home() {
  const [now, setNow] = useState(() => Date.now());
  const { user } = useSession();
  const puedeTurnos = Boolean(user?.puede_turnos ?? (user?.rol === 'paciente' || user?.rol === 'medico'));
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [loading, setLoading] = useState(puedeTurnos);
  const [error, setError] = useState('');
  const [fecha, setFecha] = useState(dateKey(new Date()));
  const [porDia, setPorDia] = useState(user?.rol === 'medico');

  const refresh = useCallback(async () => {
    if (!puedeTurnos) {
      setLoading(false);
      return;
    }
    setNow(Date.now());
    setLoading(true);
    setError('');
    try {
      setTurnos(await allPages<Turno>('/turnos/'));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo consultar la agenda.');
    } finally {
      setLoading(false);
    }
  }, [puedeTurnos]);

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
      {user?.puede_pedir_lab && (
        <Action title="Pedir laboratorio" onPress={() => router.push('/lab')} />
      )}

      {user?.rol === 'paciente' && (
        <Action title="Reservar un turno" onPress={() => router.push('/reservar')} />
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
                      : 'Sin respuesta de asistencia'}
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
