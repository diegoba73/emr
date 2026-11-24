import React, { useCallback, useMemo, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { useSession } from '../lib/session';
import { allPages, api } from '../lib/api';
import { AnuncioRecepcion, RecepcionHoy, Turno } from '../lib/types';
import { dateKey } from '../lib/calendar';
import { enVentanaEstoyEnSala } from '../lib/estoyEnSala';
import Calendar from '../components/Calendar';
import { Action, Body, Card, colors, ErrorText, Loading, Page, Title } from '../components/ui';
import { formatHora } from '../utils/dateFieldFormat';
import { useLiveRefresh } from '../lib/useLiveRefresh';

function esPendienteAtencion(t: Turno, nowMs: number): boolean {
  if (['CANCELADO', 'REALIZADO', 'NO_ASISTIO'].includes(t.estado)) return false;
  return new Date(t.fecha_hora_inicio).getTime() > nowMs;
}

function esPasado(t: Turno, nowMs: number): boolean {
  if (['CANCELADO', 'REALIZADO', 'NO_ASISTIO'].includes(t.estado)) return true;
  return new Date(t.fecha_hora_inicio).getTime() <= nowMs;
}

/**
 * Lista / agenda de turnos (separada del menú de inicio).
 */
export default function MisTurnos() {
  const [now, setNow] = useState(() => Date.now());
  const { user } = useSession();
  const puedeTurnos = Boolean(user?.puede_turnos ?? (user?.rol === 'paciente' || user?.rol === 'medico'));
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [recepcionHoy, setRecepcionHoy] = useState<RecepcionHoy | null>(null);
  const [loading, setLoading] = useState(puedeTurnos);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [fecha, setFecha] = useState(dateKey(new Date()));
  const [porDia, setPorDia] = useState(user?.rol === 'medico');

  const refresh = useCallback(async (opts?: { silent?: boolean }) => {
    setNow(Date.now());
    if (!opts?.silent) {
      setLoading(true);
      setError('');
    }
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
      if (!opts?.silent) {
        setError(e instanceof Error ? e.message : 'No se pudo consultar la agenda.');
      }
    } finally {
      if (!opts?.silent) setLoading(false);
    }
  }, [puedeTurnos, user?.rol]);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  useLiveRefresh(() => refresh({ silent: true }), {
    enabled: Boolean(puedeTurnos),
    getRevision: async () => {
      const data = await api<{ revision: string }>('/turnos/revision/');
      return data.revision;
    },
  });

  const { pendientes, pasados } = useMemo(() => {
    const base = porDia
      ? turnos.filter((t) => dateKey(new Date(t.fecha_hora_inicio)) === fecha)
      : turnos.filter((t) => t.estado !== 'CANCELADO');

    const pend = base
      .filter((t) => esPendienteAtencion(t, now))
      .sort(
        (a, b) =>
          new Date(a.fecha_hora_inicio).getTime() - new Date(b.fecha_hora_inicio).getTime()
      );
    const past = base
      .filter((t) => esPasado(t, now))
      .sort(
        (a, b) =>
          new Date(b.fecha_hora_inicio).getTime() - new Date(a.fecha_hora_inicio).getTime()
      )
      .slice(0, porDia ? 50 : 15);

    return { pendientes: pend, pasados: past };
  }, [turnos, porDia, fecha, now]);

  const estadoRecepcion = (turnoId: number) =>
    recepcionHoy?.turnos_estoy_en_sala?.find((x) => x.turno_id === turnoId);

  const puedeEstoyEnSala = (t: Turno) => {
    if (user?.rol !== 'paciente') return false;
    if (!['RESERVADO', 'CONFIRMADO'].includes(t.estado)) return false;
    if (!enVentanaEstoyEnSala(t.fecha_hora_inicio, now)) return false;
    const st = estadoRecepcion(t.id);
    if (st) return st.puedo_estoy_en_sala;
    return true;
  };

  const anunciadoEnSala = (t: Turno) => {
    const st = estadoRecepcion(t.id);
    return Boolean(st?.anunciado);
  };

  const estoyEnSala = async (turnoId: number) => {
    setBusyId(turnoId);
    setError('');
    try {
      const data = await api<AnuncioRecepcion>('/recepcion/estoy-en-sala/', 'POST', {
        turno_id: turnoId,
      });
      Alert.alert(
        'Estoy en sala',
        data.codigo_llamado
          ? `${data.mensaje}\n\nCódigo: ${data.codigo_llamado}`
          : data.mensaje
      );
      await refresh({ silent: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo anunciarte en recepción.');
    } finally {
      setBusyId(null);
    }
  };

  const renderTurno = (t: Turno, tone: 'alive' | 'past') => (
    <Card key={t.id} tone={tone}>
      <Text
        style={{
          fontWeight: '700',
          fontSize: 17,
          color: tone === 'past' ? colors.muted : colors.ink,
        }}
      >
        {(() => {
          const d = new Date(t.fecha_hora_inicio);
          const dia = d.toLocaleDateString('es-AR', {
            weekday: 'short',
            day: 'numeric',
            month: 'short',
          });
          return `${dia} ${formatHora(d)}`;
        })()}
      </Text>
      <Body>
        {user?.rol === 'medico' ? t.paciente_nombre : t.medico_nombre} ·{' '}
        {t.tipo === 'ESTUDIO' ? 'Estudio' : 'Consulta'}
      </Body>
      <Body>
        {tone === 'alive' ? 'Pendiente de atención' : 'Ya pasó / atendido'} · {t.estado}
        {t.asistencia_confirmada_en
          ? ' · Asistencia confirmada'
          : t.estado === 'CONFIRMADO' && tone === 'alive'
            ? ' · Sin respuesta de asistencia'
            : ''}
      </Body>
      {anunciadoEnSala(t) && (
        <Body>
          Ya estás anunciado
          {estadoRecepcion(t.id)?.codigo_llamado
            ? ` · código ${estadoRecepcion(t.id)?.codigo_llamado}`
            : ''}
          .
        </Body>
      )}
      {puedeEstoyEnSala(t) && (
        <Action
          title="Estoy en sala"
          disabled={busyId === t.id}
          onPress={() => void estoyEnSala(t.id)}
        />
      )}
      <Action
        secondary
        title="Ver turno"
        onPress={() => router.push({ pathname: '/turno/[id]', params: { id: String(t.id) } })}
      />
    </Card>
  );

  if (!puedeTurnos) {
    return (
      <Page>
        <Title>Mis turnos</Title>
        <Card>
          <Body>Con tu rol ({user?.rol}) no hay agenda de turnos en la app.</Body>
        </Card>
      </Page>
    );
  }

  return (
    <Page>
      <View style={{ gap: 6 }}>
        <Title>{user?.rol === 'medico' ? 'Mi agenda' : 'Mis turnos'}</Title>
        <Body>{user?.nombre}</Body>
      </View>

      <Action
        secondary
        title={porDia ? 'Ver lista' : 'Ver calendario'}
        onPress={() => setPorDia((v) => !v)}
      />

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
          {!pendientes.length && !pasados.length && (
            <Card>
              <Body>No hay turnos {porDia ? 'para este día' : 'para mostrar'}.</Body>
            </Card>
          )}

          {pendientes.length > 0 && (
            <>
              <Text style={{ color: colors.primary, fontWeight: '800', fontSize: 15 }}>
                Por atender
              </Text>
              {pendientes.map((t) => renderTurno(t, 'alive'))}
            </>
          )}

          {pasados.length > 0 && (
            <>
              <Text style={{ color: colors.muted, fontWeight: '700', fontSize: 15, marginTop: 4 }}>
                Ya pasaron
              </Text>
              {pasados.map((t) => renderTurno(t, 'past'))}
            </>
          )}
        </>
      )}
      <Action title="Actualizar" secondary disabled={loading} onPress={() => void refresh()} />
    </Page>
  );
}
