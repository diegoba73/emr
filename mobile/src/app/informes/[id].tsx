import React, { useCallback, useState } from 'react';
import { Alert, Text, View } from 'react-native';
import { useLocalSearchParams, useFocusEffect } from 'expo-router';
import { api } from '../../lib/api';
import { downloadInformePdf } from '../../lib/informePdf';
import { InformeResumen, ResultadoMovil } from '../../lib/types';
import { useSession } from '../../lib/session';
import { Action, Body, Card, colors, ErrorText, Loading, Page, Title } from '../../components/ui';

type Detalle = {
  informe: InformeResumen;
  orden?: {
    resultados?: ResultadoMovil[];
    estado?: string;
  };
      historial?: {
    analitos?: Array<{
      tipo_examen_nombre: string;
      previos: Array<{ valor?: string; fecha?: string }>;
    }>;
  } | null;
  analisis?: {
    alertas?: Array<{ mensaje?: string; severidad?: string }>;
  } | null;
};

export default function InformeDetalle() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { user } = useSession();
  const [data, setData] = useState<Detalle | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError('');
    try {
      setData(await api<Detalle>(`/informes/${id}/`));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo abrir el informe.');
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useFocusEffect(
    useCallback(() => {
      void load();
    }, [load])
  );

  const run = async (fn: () => Promise<void>, ok: string) => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      await fn();
      setMessage(ok);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo completar la operación.');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <Page>
        <Loading />
      </Page>
    );
  }
  if (!data?.informe) {
    return (
      <Page>
        <ErrorText text={error || 'Informe no encontrado.'} />
      </Page>
    );
  }

  const inf = data.informe;
  const resultados = data.orden?.resultados || [];
  const esBio = user?.rol === 'bioquimico' || user?.puede_validar_informes;

  return (
    <Page>
      <View style={{ gap: 6 }}>
        <Title>{inf.numero || `Informe #${inf.id}`}</Title>
        <Body>{inf.paciente_nombre}</Body>
        <Body>{inf.estado_display}</Body>
      </View>

      {inf.es_parcial && (
        <Card>
          <Text style={{ color: '#856404', fontWeight: '800', fontSize: 16 }}>
            INFORME PARCIAL
          </Text>
          <Body>
            Algunos resultados aún están pendientes. El PDF descargado también lo indica de forma
            destacada.
          </Body>
        </Card>
      )}

      <ErrorText text={error} />
      {message ? <Body>{message}</Body> : null}

      {inf.puede_descargar_pdf && (
        <Action
          title={busy ? 'Preparando PDF…' : 'Descargar PDF'}
          disabled={busy}
          onPress={() =>
            void run(async () => {
              const { esParcial } = await downloadInformePdf(inf.id);
              if (esParcial) {
                Alert.alert('Informe parcial', 'El PDF indica claramente que es un informe parcial.');
              }
            }, 'PDF listo para compartir o guardar.')
          }
        />
      )}

      {esBio && (
        <>
          {inf.puede_validar && (
            <Action
              title={busy ? 'Validando…' : 'Validar informe'}
              disabled={busy}
              onPress={() =>
                Alert.alert(
                  'Validar',
                  'La orden pasará a validada (FINALIZADO) y quedará bloqueada para edición.',
                  [
                    { text: 'Cancelar', style: 'cancel' },
                    {
                      text: 'Validar',
                      onPress: () =>
                        void run(
                          async () => {
                            await api(`/informes/${inf.id}/validar/`, 'POST', {
                              confirmar_criticos: true,
                            });
                          },
                          'Informe validado.'
                        ),
                    },
                  ]
                )
              }
            />
          )}
          {inf.puede_informar_parcial && !inf.es_parcial && (
            <Action
              secondary
              title={busy ? 'Informando…' : 'Informar parcialmente'}
              disabled={busy}
              onPress={() =>
                void run(
                  async () => {
                    await api(`/informes/${inf.id}/informar-parcial/`, 'POST', {});
                  },
                  'Informe marcado como parcial.'
                )
              }
            />
          )}

          <Card>
            <Text style={{ fontWeight: '800', fontSize: 18, color: colors.ink }}>Resultados</Text>
            {!resultados.length && <Body>Sin resultados cargados.</Body>}
            {resultados.map((r) => (
              <View
                key={r.id}
                style={{
                  borderTopWidth: 1,
                  borderTopColor: colors.border,
                  paddingTop: 10,
                  gap: 2,
                }}
              >
                <Text style={{ fontWeight: '700', color: colors.ink }}>
                  {r.tipo_examen_nombre || r.tipo_examen_codigo || `Examen ${r.tipo_examen}`}
                </Text>
                <Body>
                  Valor: {r.valor_obtenido ?? r.valor_numerico ?? '—'}
                  {r.unidad ? ` ${r.unidad}` : ''}
                </Body>
                <Body>Referencia: {r.rango_referencia_snapshot || r.tipo_examen_rango_referencia || '—'}</Body>
                {(r.es_patologico || r.es_critico) && (
                  <Text style={{ color: colors.danger, fontWeight: '700' }}>
                    {r.es_critico ? 'Crítico' : 'Fuera de rango'}
                  </Text>
                )}
              </View>
            ))}
          </Card>

          {Boolean(data.historial?.analitos?.length) && (
            <Card>
              <Text style={{ fontWeight: '800', fontSize: 18, color: colors.ink }}>Históricos</Text>
              {data.historial!.analitos!.map((a, idx) => (
                <View key={`${a.tipo_examen_nombre}-${idx}`} style={{ gap: 4 }}>
                  <Text style={{ fontWeight: '700', color: colors.ink }}>{a.tipo_examen_nombre}</Text>
                  {!a.previos?.length && <Body>Sin valores previos.</Body>}
                  {a.previos?.slice(0, 5).map((p, i) => (
                    <Body key={i}>
                      {p.fecha ? new Date(p.fecha).toLocaleDateString('es-AR') : '—'} ·{' '}
                      {p.valor || '—'}
                    </Body>
                  ))}
                </View>
              ))}
            </Card>
          )}

          {Boolean(data.analisis?.alertas?.length) && (
            <Card>
              <Text style={{ fontWeight: '800', fontSize: 18, color: colors.ink }}>Alertas</Text>
              {data.analisis!.alertas!.map((a, i) => (
                <Body key={i}>{a.mensaje || a.severidad || 'Alerta'}</Body>
              ))}
            </Card>
          )}
        </>
      )}

      {!esBio && !inf.puede_descargar_pdf && (
        <Card>
          <Body>Este informe aún no está disponible para descarga.</Body>
        </Card>
      )}
    </Page>
  );
}
