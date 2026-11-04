import React, { useCallback, useState } from 'react';
import { Text, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { api } from '../../lib/api';
import { EstudioResumen } from '../../lib/types';
import { useSession } from '../../lib/session';
import { Action, Body, Card, colors, ErrorText, Field, Loading, Page, Title } from '../../components/ui';

export default function EstudiosList() {
  const { user } = useSession();
  const [rows, setRows] = useState<EstudioResumen[]>([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(
    async (search = q) => {
      setLoading(true);
      setError('');
      try {
        const path =
          search.trim() && user?.rol === 'medico'
            ? `/estudios/?q=${encodeURIComponent(search.trim())}`
            : '/estudios/';
        const data = await api<{ results: EstudioResumen[] }>(path);
        setRows(data.results || []);
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

  return (
    <Page>
      <Title>Estudios</Title>
      <Body>
        {user?.rol === 'paciente'
          ? 'Solo ves estudios ya entregados, con el PDF del informe cuando esté disponible.'
          : 'Estudios validados o entregados. Podés buscar por paciente o tipo.'}
      </Body>
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
