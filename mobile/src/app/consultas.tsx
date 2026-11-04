import React, { useCallback, useState } from 'react';
import { Text } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { api } from '../lib/api';
import { ConsultaResumen } from '../lib/types';
import { Action, Body, Card, colors, ErrorText, Loading, Page, Title } from '../components/ui';

export default function ConsultasList() {
  const [rows, setRows] = useState<ConsultaResumen[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api<{ results: ConsultaResumen[] }>('/consultas/');
      setRows(data.results || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudieron cargar las consultas.');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load])
  );

  return (
    <Page>
      <Title>Consultas pasadas</Title>
      <Body>
        Resumen de tus atenciones finalizadas (fecha y médico). El detalle clínico queda en la
        historia del EMR.
      </Body>
      <ErrorText text={error} />
      {loading ? (
        <Loading />
      ) : (
        <>
          {!rows.length && (
            <Card>
              <Body>Todavía no hay consultas finalizadas para mostrar.</Body>
            </Card>
          )}
          {rows.map((r) => (
            <Card key={r.id}>
              <Text style={{ fontWeight: '800', fontSize: 17, color: colors.ink }}>
                {r.fecha
                  ? new Date(r.fecha).toLocaleString('es-AR', {
                      weekday: 'short',
                      day: 'numeric',
                      month: 'short',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })
                  : 'Sin fecha'}
              </Text>
              <Body>{r.medico_nombre || 'Médico'}</Body>
              <Body>
                {r.tipo_intervencion_display}
                {r.contexto_display ? ` · ${r.contexto_display}` : ''}
              </Body>
            </Card>
          ))}
        </>
      )}
      <Action title="Actualizar" secondary disabled={loading} onPress={() => void load()} />
      <Action title="Volver" secondary onPress={() => router.replace('/')} />
    </Page>
  );
}
