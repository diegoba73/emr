import React from 'react';
import { router } from 'expo-router';
import { Action, Body, Page, Title } from '../components/ui';

/** Ruta legacy: ya no se aceptan pedidos de estudio desde la app. */
export default function MisPedidos() {
  return (
    <Page>
      <Title>Estudios</Title>
      <Body>
        Los turnos de estudio solo los agenda secretaría, de forma presencial o por teléfono con el
        pedido médico. Desde la app solo podés reservar consultas.
      </Body>
      <Action title="Reservar consulta" onPress={() => router.replace('/reservar')} />
      <Action title="Volver" secondary onPress={() => router.replace('/')} />
    </Page>
  );
}
