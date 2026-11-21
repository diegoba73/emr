import React, { useCallback, useState } from 'react';
import { router, useFocusEffect } from 'expo-router';
import { api } from '../lib/api';
import { PedidoEstudio } from '../lib/types';
import { Action, Body, Card, ErrorText, Loading, Page, Title } from '../components/ui';
import { formatFechaHoraDisplay } from '../utils/dateFieldFormat';

export default function MisPedidos() {
  const [pedidos, setPedidos] = useState<PedidoEstudio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api<PedidoEstudio[] | { results: PedidoEstudio[] }>('/pedidos-estudio/');
      setPedidos(Array.isArray(data) ? data : data.results || []);
    } catch (e) {
      setPedidos([]);
      setError(e instanceof Error ? e.message : 'No se pudieron cargar tus pedidos.');
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh])
  );

  return (
    <Page>
      <Title>Mis pedidos de estudio</Title>
      <ErrorText text={error} />
      {loading ? (
        <Loading />
      ) : pedidos.length === 0 && !error ? (
        <Body>No tenés pedidos enviados. Desde Reservar → Estudio podés mandar la foto del pedido médico.</Body>
      ) : (
        pedidos.map((p) => (
          <Card key={p.id}>
            <Body>
              Pedido #{p.id} · {p.estado}
            </Body>
            <Body>
              {p.created_at ? formatFechaHoraDisplay(p.created_at) : 'Sin fecha'}
            </Body>
            {p.notas ? <Body>{p.notas}</Body> : null}
            {p.estado === 'PENDIENTE' && (
              <Body>Secretaría tipifica el estudio y te propone un horario.</Body>
            )}
            {p.turno ? (
              <Action
                title={`Ver turno #${p.turno}`}
                onPress={() =>
                  router.push({ pathname: '/turno/[id]', params: { id: String(p.turno) } })
                }
              />
            ) : null}
          </Card>
        ))
      )}
      <Action title="Actualizar" secondary onPress={() => void refresh()} />
      <Action title="Volver" secondary onPress={() => router.replace('/')} />
    </Page>
  );
}
