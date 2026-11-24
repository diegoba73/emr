import React, { useCallback, useMemo, useState } from 'react';
import { Alert, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { useSession } from '../lib/session';
import { allPages, api } from '../lib/api';
import { AnuncioRecepcion, EstudioResumen, RecepcionHoy, Turno } from '../lib/types';
import AnnouncementsBanner from '../components/AnnouncementsBanner';
import { Action, Body, Card, ErrorText, Loading, Page, Title } from '../components/ui';
import { formatFechaHoraDisplay } from '../utils/dateFieldFormat';
import type { AnnouncementAudience } from '../lib/announcements';

/** Turnos futuros activos (pendientes de atención / confirmación). */
function countTurnosPendientes(turnos: Turno[], nowMs: number): number {
  return turnos.filter((t) => {
    if (t.estado === 'CANCELADO' || t.estado === 'REALIZADO' || t.estado === 'NO_ASISTIO') {
      return false;
    }
    if (new Date(t.fecha_hora_inicio).getTime() <= nowMs) return false;
    return (
      t.estado === 'RESERVADO' ||
      t.estado === 'CONFIRMADO' ||
      Boolean(t.requiere_aceptacion_paciente)
    );
  }).length;
}

/** Estudios disponibles en la bandeja móvil (validados/entregados según API). */
function countEstudiosPendientes(estudios: EstudioResumen[]): number {
  return estudios.length;
}

export default function Home() {
  const { user } = useSession();
  const puedeTurnos = Boolean(user?.puede_turnos ?? (user?.rol === 'paciente' || user?.rol === 'medico'));
  const puedeEstudios = user?.rol === 'paciente' || user?.rol === 'medico';
  const [turnos, setTurnos] = useState<Turno[]>([]);
  const [estudios, setEstudios] = useState<EstudioResumen[]>([]);
  const [loadingHome, setLoadingHome] = useState(
    Boolean(user?.rol === 'paciente' || puedeTurnos || puedeEstudios)
  );
  const [error, setError] = useState('');
  const [recepcionHoy, setRecepcionHoy] = useState<RecepcionHoy | null>(null);
  const [busyAnuncio, setBusyAnuncio] = useState(false);

  const audience: AnnouncementAudience = useMemo(() => {
    if (user?.rol === 'paciente') return 'paciente';
    if (user?.rol === 'medico' || user?.rol === 'bioquimico' || user?.rol === 'secretaria') return 'staff';
    return 'all';
  }, [user?.rol]);

  const refreshHome = useCallback(async () => {
    setError('');
    setLoadingHome(true);
    try {
      const tasks: Array<Promise<void>> = [];

      if (puedeTurnos) {
        tasks.push(
          allPages<Turno>('/turnos/').then((lista) => {
            setTurnos(lista);
          })
        );
      } else {
        setTurnos([]);
      }

      if (puedeEstudios) {
        tasks.push(
          api<{ results: EstudioResumen[] }>('/estudios/').then((data) => {
            setEstudios(data.results || []);
          })
        );
      } else {
        setEstudios([]);
      }

      if (user?.rol === 'paciente') {
        tasks.push(
          api<RecepcionHoy>('/recepcion/hoy/').then((recepcion) => {
            setRecepcionHoy(recepcion);
          })
        );
      } else {
        setRecepcionHoy(null);
      }

      await Promise.all(tasks);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo actualizar el inicio.');
    } finally {
      setLoadingHome(false);
    }
  }, [puedeEstudios, puedeTurnos, user?.rol]);

  useFocusEffect(
    useCallback(() => {
      void refreshHome();
    }, [refreshHome])
  );

  const now = Date.now();
  const badgeTurnos = countTurnosPendientes(turnos, now);
  const badgeEstudios = countEstudiosPendientes(estudios);

  const turnoActivoPaciente =
    user?.rol === 'paciente'
      ? turnos.find(
          (t) =>
            new Date(t.fecha_hora_inicio).getTime() > now &&
            (t.estado === 'RESERVADO' || t.estado === 'CONFIRMADO')
        )
      : undefined;

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
      await refreshHome();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo anunciarte en recepción.');
    } finally {
      setBusyAnuncio(false);
    }
  }, [refreshHome]);

  const anuncioLab = useCallback(async () => {
    setBusyAnuncio(true);
    setError('');
    try {
      const data = await api<AnuncioRecepcion>('/recepcion/anuncio-lab/', 'POST', {});
      mostrarAnuncio(data, 'Laboratorio');
      await refreshHome();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo anunciarte al laboratorio.');
    } finally {
      setBusyAnuncio(false);
    }
  }, [refreshHome]);

  return (
    <Page>
      <View style={{ gap: 6 }}>
        <Body>{user?.nombre}</Body>
        <Title>Inicio</Title>
      </View>

      <AnnouncementsBanner audience={audience} />

      <View style={{ flexDirection: 'row', gap: 10 }}>
        <View style={{ flex: 1 }}>
          <Action secondary title="Mi cuenta" onPress={() => router.push('/ajustes')} />
        </View>
        <View style={{ flex: 1 }}>
          <Action secondary title="Informes" onPress={() => router.push('/informes')} />
        </View>
      </View>

      {puedeTurnos && (
        <Action
          title={user?.rol === 'medico' ? 'Mi agenda' : 'Mis turnos'}
          badge={badgeTurnos}
          onPress={() => router.push('/turnos')}
        />
      )}

      {puedeEstudios && (
        <Action
          title="Mis estudios"
          badge={badgeEstudios}
          onPress={() => router.push('/estudios')}
        />
      )}

      {user?.rol === 'paciente' && (
        <Action title="Consultas pasadas" secondary onPress={() => router.push('/consultas')} />
      )}
      {user?.puede_pedir_lab && (
        <Action title="Pedir laboratorio" secondary onPress={() => router.push('/lab')} />
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

      {user?.rol === 'paciente' && loadingHome && <Loading />}

      {user?.rol === 'paciente' && !loadingHome && turnoActivoPaciente && (
        <Card>
          <Body>
            Ya tenés un turno el {formatFechaHoraDisplay(turnoActivoPaciente.fecha_hora_inicio)}.
            No podés sacar otro desde la app; si necesitás cambiarlo, contactá a secretaría.
          </Body>
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

      <ErrorText text={error} />

      {!puedeTurnos && !puedeEstudios && (
        <Card>
          <Body>
            Con tu rol ({user?.rol}) podés consultar informes de laboratorio
            {user?.rol === 'bioquimico' ? ' y validar u informar parcialmente' : ''}.
          </Body>
        </Card>
      )}

      {user?.rol === 'paciente' && (
        <Action
          title="Reservar un turno"
          disabled={Boolean(turnoActivoPaciente) || loadingHome}
          onPress={() => router.push('/reservar')}
        />
      )}
    </Page>
  );
}
