import React, { useEffect, useRef, useState } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import { Alert, Text, View } from 'react-native';
import { allPages, api } from '../lib/api';
import { useSession } from '../lib/session';
import { Medico, Slot, Turno } from '../lib/types';
import { dateKey } from '../lib/calendar';
import Calendar from '../components/Calendar';
import { Action, Body, Card, colors, ErrorText, Field, Loading, Page, Title } from '../components/ui';
import { formatFechaHoraDisplay, formatHoraDisplay } from '../utils/dateFieldFormat';
import { useLiveRefresh } from '../lib/useLiveRefresh';

export default function Booking() {
  const { user, clinic } = useSession();
  const params = useLocalSearchParams<{ reprogramar?: string }>();
  const reprogramarId = params.reprogramar ? Number(params.reprogramar) : null;
  const esReprogramar = Boolean(reprogramarId && !Number.isNaN(reprogramarId));

  const [medicos, setMedicos] = useState<Medico[]>([]);
  const [medico, setMedico] = useState<number | null>(null);
  const [busqueda, setBusqueda] = useState('');
  const normalizar = (texto: string) =>
    texto.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const palabras = normalizar(busqueda).trim().split(/\s+/).filter(Boolean);
  const coincidencias = palabras.length
    ? medicos.filter((m) =>
        palabras.every((p) =>
          normalizar(`${m.nombre_completo || ''} ${m.nombre} ${m.apellido}`).includes(p)
        )
      )
    : [];
  const seleccionado = medicos.find((m) => m.id === medico);
  const [fecha, setFecha] = useState(dateKey(new Date()));
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [motivo, setMotivo] = useState('');
  const [reload, setReload] = useState(0);
  const lock = useRef(false);
  const [bloqueado, setBloqueado] = useState(false);
  const [coberturaIncompleta, setCoberturaIncompleta] = useState(false);
  const [coberturaMsg, setCoberturaMsg] = useState('');

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        if (user?.rol === 'paciente') {
          const me = await api<typeof user>('/me/');
          if (!active) return;
          if (me.cobertura_completa === false) {
            setCoberturaIncompleta(true);
            setCoberturaMsg(
              me.cobertura_mensaje ||
                'Completá obra social, número de afiliado y plan antes de reservar.'
            );
            return;
          }
        }

        if (esReprogramar && reprogramarId) {
          const t = await api<Turno>(`/turnos/${reprogramarId}/`);
          if (!active) return;
          if (!t.puede_reprogramar) {
            setError(t.motivo_bloqueo_reprogramar || 'No podés reprogramar este turno.');
            setBloqueado(true);
            return;
          }
          setMedico(t.medico_id);
          setBusqueda(t.medico_nombre || '');
          setMedicos([
            {
              id: t.medico_id,
              nombre: t.medico_nombre,
              apellido: '',
              nombre_completo: t.medico_nombre,
            } as Medico,
          ]);
          return;
        }

        const propios = await allPages<Turno>('/turnos/');
        const ahora = Date.now();
        if (
          propios.some(
            (t) =>
              new Date(t.fecha_hora_inicio).getTime() > ahora &&
              (t.estado === 'RESERVADO' || t.estado === 'CONFIRMADO')
          )
        ) {
          if (active) setBloqueado(true);
          return;
        }
        const m = await allPages<Medico>('/medicos/');
        if (active) setMedicos(m);
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : 'No se pudo cargar la agenda.');
      }
    })();
    return () => {
      active = false;
    };
  }, [esReprogramar, reprogramarId, user?.rol]);

  useEffect(() => {
    let active = true;
    setSlots([]);
    if (!medico) {
      setLoading(false);
      return;
    }
    setLoading(true);
    api<{ slots: Slot[] }>(`/medicos/${medico}/slots/?fecha=${fecha}&tipo=CONSULTA`)
      .then((r) => {
        if (active) setSlots(r.slots);
      })
      .catch((e) => {
        if (active) setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [medico, fecha, reload]);

  useLiveRefresh(
    () => {
      if (!medico) return;
      return api<{ slots: Slot[] }>(`/medicos/${medico}/slots/?fecha=${fecha}&tipo=CONSULTA`)
        .then((r) => setSlots(r.slots))
        .catch(() => undefined);
    },
    {
      enabled: Boolean(medico) && !bloqueado && !coberturaIncompleta,
      getRevision: async () => {
        const data = await api<{ revision: string }>('/turnos/revision/');
        return data.revision;
      },
    }
  );

  const submitConsulta = async (slot: Slot) => {
    if (lock.current) return;
    lock.current = true;
    setBusy(true);
    setError('');
    try {
      if (esReprogramar && reprogramarId) {
        const t = await api<Turno>(`/turnos/${reprogramarId}/reprogramar-horario/`, 'POST', {
          horario_id: slot.horario_id,
          inicio: slot.inicio,
          motivo: motivo.trim() || 'Reprogramación desde la app',
        });
        router.replace({ pathname: '/turno/[id]', params: { id: t.id } });
        return;
      }
      const t = await api<Turno>('/turnos/reservar-horario/', 'POST', {
        horario_id: slot.horario_id,
        inicio: slot.inicio,
        motivo,
      });
      router.replace({ pathname: '/turno/[id]', params: { id: t.id } });
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'No se pudo guardar el turno.';
      setError(msg);
      if (/cobertura|afiliado|plan/i.test(msg)) {
        setCoberturaIncompleta(true);
        setCoberturaMsg(msg);
      }
      setReload((v) => v + 1);
    } finally {
      lock.current = false;
      setBusy(false);
    }
  };

  const choose = (slot: Slot) =>
    Alert.alert(
      esReprogramar ? 'Confirmar reprogramación' : 'Confirmar reserva',
      `${clinic?.name}\n${formatFechaHoraDisplay(slot.inicio)} · ${slot.duracion_min} minutos`,
      [
        { text: 'Volver', style: 'cancel' },
        {
          text: esReprogramar ? 'Reprogramar' : 'Confirmar',
          onPress: () => submitConsulta(slot),
        },
      ]
    );

  if (user?.rol === 'medico')
    return (
      <Page>
        <Body>
          La reserva de turnos nuevos es para pacientes. La gestión de agenda corresponde a
          secretaría.
        </Body>
      </Page>
    );

  if (coberturaIncompleta)
    return (
      <Page>
        <Title>{esReprogramar ? 'Reprogramar turno' : 'Reservar un turno'}</Title>
        <Body>{coberturaMsg}</Body>
        <Body>
          Si te registraste como obra social, necesitás número de afiliado y plan. Particular no
          los requiere. Podés corregirlo en secretaría o crear la cuenta de nuevo con esos datos.
        </Body>
        <Action title="Ir a mi cuenta" secondary onPress={() => router.replace('/ajustes')} />
        <Action title="Volver" secondary onPress={() => router.replace('/')} />
      </Page>
    );

  if (bloqueado && !esReprogramar)
    return (
      <Page>
        <Title>Reservar un turno</Title>
        <Body>
          Ya tenés un turno reservado. Desde la app podés reprogramarlo una sola vez si faltan al
          menos 48 horas. Si necesitás cancelarlo, contactá a secretaría.
        </Body>
        <Action title="Volver" secondary onPress={() => router.replace('/')} />
      </Page>
    );

  if (bloqueado && esReprogramar)
    return (
      <Page>
        <Title>Reprogramar turno</Title>
        <ErrorText text={error} />
        <Action title="Volver" secondary onPress={() => router.back()} />
      </Page>
    );

  const duracionLabel = slots[0]?.duracion_min;
  return (
    <Page>
      <Title>{esReprogramar ? 'Reprogramar turno' : 'Reservar un turno'}</Title>
      <Body>
        {esReprogramar
          ? 'Elegí un nuevo horario de consulta con el mismo médico. Solo una reprogramación y con ≥ 48 h de anticipación.'
          : 'Solo consultas. Los estudios los agenda secretaría (presencial o por teléfono).'}
      </Body>
      <ErrorText text={error} />
      {!esReprogramar && (
        <Field
          label="Buscar médico"
          placeholder="Escribí nombre o apellido"
          value={busqueda}
          autoCorrect={false}
          editable={!busy}
          onChangeText={(texto) => {
            setBusqueda(texto);
            setMedico(null);
            setSlots([]);
            setError('');
          }}
        />
      )}
      {seleccionado ? (
        <Card>
          <Body>
            Médico seleccionado:{' '}
            {seleccionado.nombre_completo || `${seleccionado.apellido}, ${seleccionado.nombre}`}
          </Body>
          {!esReprogramar && (
            <Action
              secondary
              title="Cambiar médico"
              disabled={busy}
              onPress={() => {
                setMedico(null);
                setSlots([]);
                setBusqueda('');
              }}
            />
          )}
        </Card>
      ) : (
        !esReprogramar && (
          <>
            {!palabras.length && <Body>Escribí para buscar y luego seleccioná un médico.</Body>}
            {palabras.length > 0 && coincidencias.length === 0 && (
              <Body>No encontramos médicos con ese nombre o apellido.</Body>
            )}
            {coincidencias.slice(0, 8).map((m) => (
              <Action
                key={m.id}
                secondary
                title={m.nombre_completo || `${m.apellido}, ${m.nombre}`}
                disabled={busy}
                onPress={() => {
                  setMedico(m.id);
                  setBusqueda(m.nombre_completo || `${m.apellido}, ${m.nombre}`);
                  setError('');
                }}
              />
            ))}
          </>
        )
      )}
      <Card>
        <Calendar
          value={fecha}
          onChange={(d) => {
            if (!busy) {
              setFecha(d);
              setError('');
            }
          }}
          futureOnly
        />
      </Card>
      <Field
        label={esReprogramar ? 'Motivo' : 'Motivo (opcional)'}
        value={motivo}
        onChangeText={setMotivo}
        maxLength={255}
        editable={!busy}
      />
      {loading ? (
        <Loading />
      ) : (
        medico && (
          <Card>
            <Text style={{ fontSize: 18, fontWeight: '700', color: colors.ink }}>
              Horarios disponibles{duracionLabel ? ` · ${duracionLabel} minutos` : ''}
            </Text>
            {!slots.length && <Body>No hay horarios libres para este día. Probá otra fecha.</Body>}
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
              {slots.map((slot) => (
                <View key={slot.inicio} style={{ width: '30%' }}>
                  <Action
                    title={formatHoraDisplay(new Date(slot.inicio))}
                    disabled={busy}
                    onPress={() => choose(slot)}
                  />
                </View>
              ))}
            </View>
          </Card>
        )
      )}
    </Page>
  );
}
