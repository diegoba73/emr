import React, { useCallback, useState } from 'react';
import { Text, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { api } from '../../lib/api';
import { OrdenLabMovilResumen } from '../../lib/types';
import { useSession } from '../../lib/session';
import { Action, Body, Card, colors, ErrorText, Loading, Page, Title } from '../../components/ui';

export default function LabOrdenesHoy() {
  const { user } = useSession();
  const [rows, setRows] = useState<OrdenLabMovilResumen[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api<{ results: OrdenLabMovilResumen[] }>('/lab/ordenes/');
      setRows(data.results || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudieron cargar tus pedidos.');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load])
  );

  if (!user?.puede_pedir_lab) {
    return (
      <Page>
        <Title>Laboratorio</Title>
        <Body>Solo médicos con ficha vinculada pueden pedir análisis desde la app.</Body>
      </Page>
    );
  }

  return (
    <Page>
      <Title>Pedir laboratorio</Title>
      <Body>Pedidos de hoy. Lab recibe la orden apenas la confirmás.</Body>
      <Action title="Nuevo pedido" onPress={() => router.push('/lab/nueva')} />
      <ErrorText text={error} />
      {loading ? (
        <Loading />
      ) : (
        <>
          {!rows.length && (
            <Card>
              <Body>Todavía no pediste análisis hoy.</Body>
            </Card>
          )}
          {rows.map((o) => (
            <Card key={o.id}>
              <Text style={{ fontWeight: '800', fontSize: 18, color: colors.ink }}>
                {o.numero || `Orden #${o.id}`}
              </Text>
              <Body>{o.paciente_nombre}</Body>
              <Body>
                {o.origen_display} · {o.estado}
              </Body>
            </Card>
          ))}
          <Action title="Actualizar" secondary disabled={loading} onPress={() => void load()} />
        </>
      )}
    </Page>
  );
}
