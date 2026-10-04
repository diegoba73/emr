import React, { useCallback, useState } from 'react';
import { Text, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { api } from '../../lib/api';
import { InformeResumen } from '../../lib/types';
import { Action, Body, Card, colors, ErrorText, Field, Loading, Page, Title } from '../../components/ui';

export default function InformesList() {
  const [rows, setRows] = useState<InformeResumen[]>([]);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async (search = q) => {
    setLoading(true);
    setError('');
    try {
      const path = search.trim()
        ? `/informes/?q=${encodeURIComponent(search.trim())}`
        : '/informes/';
      const data = await api<{ results: InformeResumen[] }>(path);
      setRows(data.results || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudieron cargar los informes.');
    } finally {
      setLoading(false);
    }
  }, [q]);

  useFocusEffect(
    useCallback(() => {
      void load('');
    }, [load])
  );

  return (
    <Page>
      <Title>Informes</Title>
      <Body>
        Solo aparecen informes validados o parciales. En parciales ves los valores en pantalla; el
        PDF se habilita cuando el informe está validado.
      </Body>
      <Card>
        <Field
          label="Buscar"
          placeholder="Número, paciente o DNI"
          value={q}
          onChangeText={setQ}
          autoCorrect={false}
          onSubmitEditing={() => void load(q)}
        />
        <Action title="Buscar" secondary disabled={loading} onPress={() => void load(q)} />
      </Card>
      <ErrorText text={error} />
      {loading ? (
        <Loading />
      ) : (
        <>
          {!rows.length && (
            <Card>
              <Body>No hay informes para mostrar.</Body>
            </Card>
          )}
          {rows.map((r) => (
            <Card key={r.id}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
                <Text style={{ fontWeight: '800', fontSize: 17, color: colors.ink, flex: 1 }}>
                  {r.numero || `#${r.id}`}
                </Text>
                {r.es_parcial && (
                  <Text
                    style={{
                      backgroundColor: '#fff3cd',
                      color: '#856404',
                      fontWeight: '700',
                      fontSize: 12,
                      paddingHorizontal: 8,
                      paddingVertical: 4,
                      borderRadius: 8,
                      overflow: 'hidden',
                    }}
                  >
                    PARCIAL
                  </Text>
                )}
              </View>
              <Body>{r.paciente_nombre}</Body>
              <Body>{r.estado_display}</Body>
              <Action
                secondary
                title="Ver informe"
                onPress={() => router.push({ pathname: '/informes/[id]', params: { id: String(r.id) } })}
              />
            </Card>
          ))}
        </>
      )}
      <Action title="Actualizar" secondary disabled={loading} onPress={() => void load(q)} />
    </Page>
  );
}
