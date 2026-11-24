import React, { useCallback, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { allPages, api } from '../../lib/api';
import {
  AnuncioRecepcion,
  EstudioResumen,
  RecepcionHoy,
  Turno,
} from '../../lib/types';
import { useSession } from '../../lib/session';
import { enVentanaEstoyEnSala } from '../../lib/estoyEnSala';
import { Action, Body, Card, colors, ErrorText, Field, Loading, Page, Title } from '../../components/ui';
import { formatFechaHoraDisplay, formatHora } from '../../utils/dateFieldFormat';

function esTurnoEstudio(t: Turno): boolean {
  if (t.tipo === 'ESTUDIO') return true;
  if (t.viene_de_pedido_estudio) return true;
  return Boolean(t.estudio_complementario?.id);
}

export default function EstudiosList() {
  const { user } = useSession();
  const [rows, setRows] = useState<EstudioResumen[]>([]);
  const [turnosEstudio, setTurnosEstudio] = useState<Turno[]>([]);
  const [recepcionHoy, setRecepcionHoy] = useState<RecepcionHoy | null>(null);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [now, setNow] = useState(() => Date.now());

  const load = useCallback(
    async (search = q) => {
      setLoading(true);
      setError('');
      setNow(Date.now());
      try {
        const path =
          search.trim() && user?.rol === 'medico'
            ? `/estudios/?q=${encodeURIComponent(search.trim())}`
            : '/estudios/';
        const data = await api<{ results: EstudioResumen[] }>(path);
        setRows(data.results || []);

        if (user?.rol === 'paciente') {
          const [lista, recepcion] = await Promise.all([
            allPages<Turno>('/turnos/'),
            api<RecepcionHoy>('/recepcion/hoy/'),
          ]);
          setTurnosEstudio(
            lista.filter(
              (t) =>
                esTurnoEstudio(t) &&
                ['RESERVADO', 'CONFIRMADO'].includes(t.estado) &&
                new Date(t.fecha_hora_inicio).getTime() > Date.now() - 60_000
            )
          );
          setRecepcionHoy(recepcion);
        } else {
          setTurnosEstudio([]);
          setRecepcionHoy(null);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'No se pudieron cargar los estudios.');
      } finally {
        setLoading(false);
      }
    },
    [q, user?.rol]
  );

  useFocusEffect(
    useCallback(() => {
      void load('');
    }, [load])
  );

  const estadoRecepcion = (turnoId: number) =>
    recepcionHoy?.turnos_estoy_en_sala?.find((x) => x.turno_id === turnoId);

  const puedeEstoyEnSala = (t: Turno) => {
    if (user?.rol !== 'paciente') return false;
    if (!enVentanaEstoyEnSala(t.fecha_hora_inicio, now)) return false;
    const st = estadoRecepcion(t.id);
    if (st) return st.puedo_estoy_en_sala;
    return true;
  };

  const anunciadoEnSala = (t: Turno) => Boolean(estadoRecepcion(t.id)?.anunciado);

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
      await load(q);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo anunciarte en recepción.');
    } finally {
      setBusyId(null);
    }
  };

  const turnosEnVentanaOHoy = turnosEstudio.filter(
    (t) =>
      enVentanaEstoyEnSala(t.fecha_hora_inicio, now) ||
      anunciadoEnSala(t) ||
      // Mostrar también estudios de hoy futuros (fuera de ventana) para contexto, sin botón.
      (user?.rol === 'paciente' &&
        new Date(t.fecha_hora_inicio).toDateString() === new Date(now).toDateString())
  );

  return (
    <Page>
      <Title>Mis estudios</Title>
      <Body>
        {user?.rol === 'paciente'
          ? 'Turnos de estudio de hoy (con anuncio en sala) e informes ya entregados.'
          : 'Estudios validados o entregados. Podés buscar por paciente o tipo.'}
      </Body>

      {user?.rol === 'paciente' && turnosEnVentanaOHoy.length > 0 && (
        <>
          <Body>Turnos de estudio</Body>
          {turnosEnVentanaOHoy.map((t) => (
            <Card key={`turno-${t.id}`}>
              <Text style={{ fontWeight: '800', fontSize: 17, color: colors.ink }}>
                {t.estudio_nombre ||
                  t.estudio_complementario?.tipo_estudio_nombre ||
                  'Estudio'}
              </Text>
              <Body>
                {formatFechaHoraDisplay(t.fecha_hora_inicio)} · {formatHora(new Date(t.fecha_hora_inicio))}
              </Body>
              <Body>{t.estado}</Body>
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
                onPress={() =>
                  router.push({ pathname: '/turno/[id]', params: { id: String(t.id) } })
                }
              />
            </Card>
          ))}
        </>
      )}

      {user?.rol === 'medico' && (
        <Card>
          <Field
            label="Buscar"
            placeholder="Paciente, DNI o tipo"
            value={q}
            onChangeText={setQ}
            autoCorrect={false}
            onSubmitEditing={() => void load(q)}
          />
          <Action title="Buscar" secondary disabled={loading} onPress={() => void load(q)} />
        </Card>
      )}
      <ErrorText text={error} />
      {loading ? (
        <Loading />
      ) : (
        <>
          <Body>Informes entregados</Body>
          {!rows.length && (
            <Card>
              <Body>No hay estudios para mostrar.</Body>
            </Card>
          )}
          {rows.map((r) => (
            <Card key={r.id}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
                <Text style={{ fontWeight: '800', fontSize: 17, color: colors.ink, flex: 1 }}>
                  {r.tipo_nombre}
                </Text>
                <Text style={{ color: colors.muted, fontSize: 13 }}>{r.estado_display}</Text>
              </View>
              {user?.rol === 'medico' && <Body>{r.paciente_nombre}</Body>}
              <Body>
                {r.fecha_solicitud
                  ? new Date(r.fecha_solicitud).toLocaleDateString('es-AR')
                  : 'Sin fecha'}
              </Body>
              <Action
                secondary
                title="Ver estudio"
                onPress={() =>
                  router.push({ pathname: '/estudios/[id]', params: { id: String(r.id) } })
                }
              />
            </Card>
          ))}
        </>
      )}
      <Action title="Actualizar" secondary disabled={loading} onPress={() => void load(q)} />
      <Action title="Volver" secondary onPress={() => router.replace('/')} />
    </Page>
  );
}
