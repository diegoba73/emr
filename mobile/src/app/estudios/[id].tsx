import React, { useCallback, useState } from 'react';
import { Alert } from 'react-native';
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { api } from '../../lib/api';
import { EstudioResumen } from '../../lib/types';
import { downloadEstudioInformePdf } from '../../lib/estudioPdf';
import { Action, Body, Card, ErrorText, Loading, Page, Title } from '../../components/ui';

export default function EstudioDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [estudio, setEstudio] = useState<EstudioResumen | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setEstudio(await api<EstudioResumen>(`/estudios/${id}/`));
    } catch (e) {
      setEstudio(null);
      setError(e instanceof Error ? e.message : 'No se pudo cargar el estudio.');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load])
  );

  const descargar = async (informeId: number) => {
    setBusy(true);
    setError('');
    try {
      await downloadEstudioInformePdf(Number(id), informeId);
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'No se pudo descargar el PDF.';
      setError(msg);
      Alert.alert('PDF', msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page>
      <ErrorText text={error} />
      {loading ? (
        <Loading />
      ) : estudio ? (
        <>
          <Title>{estudio.tipo_nombre}</Title>
          <Card>
            <Body>{estudio.paciente_nombre}</Body>
            <Body>{estudio.estado_display}</Body>
            <Body>
              {estudio.fecha_solicitud
                ? new Date(estudio.fecha_solicitud).toLocaleString('es-AR')
                : 'Sin fecha de solicitud'}
            </Body>
          </Card>
          {(estudio.informes || []).length === 0 ? (
            <Card>
              <Body>Este estudio todavía no tiene informes descargables.</Body>
            </Card>
          ) : (
            estudio.informes.map((inf) => (
              <Card key={inf.id}>
                <Body>
                  {inf.titulo} · {inf.estado_display || inf.estado}
                  {inf.es_vigente ? ' · vigente' : ''}
                </Body>
                {inf.puede_descargar_pdf ? (
                  <Action
                    title="Descargar PDF"
                    disabled={busy}
                    onPress={() => void descargar(inf.id)}
                  />
                ) : (
                  <Body>PDF no disponible para este informe.</Body>
                )}
              </Card>
            ))
          )}
        </>
      ) : null}
      <Action title="Actualizar" secondary disabled={busy || loading} onPress={() => void load()} />
      <Action title="Volver" secondary disabled={busy} onPress={() => router.back()} />
    </Page>
  );
}
