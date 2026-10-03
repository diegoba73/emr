import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Alert, Pressable, Text, View } from 'react-native';
import { router } from 'expo-router';
import { api } from '../../lib/api';
import {
  ContextoLab,
  LabCatalogItem,
  PacienteLabMovil,
  PaqueteLabMovil,
} from '../../lib/types';
import { Action, Body, Card, colors, ErrorText, Field, Loading, Page, Title } from '../../components/ui';
import { useSession } from '../../lib/session';

type Step = 'paciente' | 'contexto' | 'items' | 'confirmar';

type SelectionKey = string;

const CONTEXTOS_FALLBACK: Array<{ id: ContextoLab; label: string }> = [
  { id: 'GUARDIA', label: 'Guardia' },
  { id: 'AMBULATORIO', label: 'Ambulatorio' },
  { id: 'INTERNACION', label: 'Internado' },
];

function keyOf(item: Pick<LabCatalogItem, 'kind' | 'id'>): SelectionKey {
  return `${item.kind}:${item.id}`;
}

function Chip({
  label,
  selected,
  onPress,
}: {
  label: string;
  selected: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={{
        paddingVertical: 10,
        paddingHorizontal: 14,
        borderRadius: 999,
        backgroundColor: selected ? colors.primary : '#e3eff2',
      }}
    >
      <Text style={{ color: selected ? '#fff' : colors.ink, fontWeight: '700' }}>{label}</Text>
    </Pressable>
  );
}

function SelectRow({
  item,
  selected,
  onToggle,
  onToggleFav,
}: {
  item: LabCatalogItem;
  selected: boolean;
  onToggle: () => void;
  onToggleFav?: () => void;
}) {
  return (
    <View
      style={{
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        borderTopWidth: 1,
        borderTopColor: colors.border,
        paddingTop: 10,
      }}
    >
      <Pressable onPress={onToggle} style={{ flex: 1, gap: 2 }}>
        <Text style={{ fontWeight: '700', color: colors.ink }}>
          {selected ? '✓ ' : ''}
          {item.nombre}
        </Text>
        <Body>
          {item.kind === 'panel' ? 'Panel' : 'Examen'} · {item.codigo}
        </Body>
      </Pressable>
      {onToggleFav ? (
        <Pressable onPress={onToggleFav} hitSlop={8}>
          <Text style={{ fontSize: 22 }}>{item.favorito ? '★' : '☆'}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

export default function NuevaOrdenLab() {
  const { user } = useSession();
  const contextosPermitidos = useMemo(() => {
    if (user?.contextos_lab?.length) return user.contextos_lab;
    if (user?.contextos_lab_permitidos?.length) {
      return CONTEXTOS_FALLBACK.filter((c) => user.contextos_lab_permitidos!.includes(c.id));
    }
    if (user?.ambito_atencion === 'AMBULATORIO') {
      return CONTEXTOS_FALLBACK.filter((c) => c.id === 'AMBULATORIO');
    }
    return CONTEXTOS_FALLBACK;
  }, [user]);
  const soloAmbulatorio = contextosPermitidos.length === 1 && contextosPermitidos[0].id === 'AMBULATORIO';

  const [step, setStep] = useState<Step>('paciente');
  const [q, setQ] = useState('');
  const [pacientes, setPacientes] = useState<PacienteLabMovil[]>([]);
  const [paciente, setPaciente] = useState<PacienteLabMovil | null>(null);
  const [contexto, setContexto] = useState<ContextoLab>('AMBULATORIO');
  const [catalogLoading, setCatalogLoading] = useState(false);
  const [favoritos, setFavoritos] = useState<LabCatalogItem[]>([]);
  const [paquetes, setPaquetes] = useState<PaqueteLabMovil[]>([]);
  const [paneles, setPaneles] = useState<LabCatalogItem[]>([]);
  const [examenes, setExamenes] = useState<LabCatalogItem[]>([]);
  const [searchCat, setSearchCat] = useState('');
  const [selected, setSelected] = useState<Record<SelectionKey, LabCatalogItem>>({});
  const [obs, setObs] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [restriccionesEnsayos, setRestriccionesEnsayos] = useState<
    Record<string, { bloqueado: boolean; mensaje: string | null }>
  >({});

  const selectedList = useMemo(() => Object.values(selected), [selected]);

  const totalPasos = soloAmbulatorio ? 3 : 4;
  const pasoActual =
    step === 'paciente' ? 1 : step === 'contexto' ? 2 : step === 'items' ? (soloAmbulatorio ? 2 : 3) : totalPasos;

  const mensajeBloqueoItem = (item: LabCatalogItem): string | null => {
    if (item.kind === 'examen') {
      const r = restriccionesEnsayos[item.codigo];
      return r?.bloqueado ? r.mensaje || 'Ensayo no permitido por obra social. Comuníquese con el Laboratorio.' : null;
    }
    return null;
  };

  const mensajeBloqueoPaquete = (paq: PaqueteLabMovil): string | null => {
    for (const e of paq.examenes) {
      const r = restriccionesEnsayos[e.codigo];
      if (r?.bloqueado) {
        return r.mensaje || 'Ensayo no permitido por obra social. Comuníquese con el Laboratorio.';
      }
    }
    return null;
  };

  const buscarPacientes = async () => {
    setBusy(true);
    setError('');
    try {
      const data = await api<{ results: PacienteLabMovil[] }>(
        `/lab/pacientes/?q=${encodeURIComponent(q.trim())}`
      );
      setPacientes(data.results || []);
      if (!(data.results || []).length) {
        setError('No se encontraron pacientes. Si es nuevo, dalo de alta en recepción.');
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo buscar.');
      setPacientes([]);
    } finally {
      setBusy(false);
    }
  };

  const loadCatalogo = useCallback(async (ctx: ContextoLab, query = '') => {
    setCatalogLoading(true);
    setError('');
    try {
      const qs = new URLSearchParams({ contexto: ctx });
      if (query.trim()) qs.set('q', query.trim());
      const data = await api<{
        favoritos: LabCatalogItem[];
        paquetes: PaqueteLabMovil[];
        paneles: LabCatalogItem[];
        examenes: LabCatalogItem[];
      }>(`/lab/catalogo/?${qs.toString()}`);
      setFavoritos(data.favoritos || []);
      setPaquetes(data.paquetes || []);
      setPaneles(data.paneles || []);
      setExamenes(data.examenes || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo cargar el catálogo.');
    } finally {
      setCatalogLoading(false);
    }
  }, []);

  useEffect(() => {
    if (step === 'items') void loadCatalogo(contexto, searchCat);
  }, [step, contexto, loadCatalogo]);

  const elegirPaciente = (p: PacienteLabMovil) => {
    setPaciente(p);
    const sugerido = p.contexto_sugerido || 'AMBULATORIO';
    const ids = new Set(contextosPermitidos.map((c) => c.id));
    const ctx = ids.has(sugerido) ? sugerido : contextosPermitidos[0]?.id || 'AMBULATORIO';
    setContexto(ctx);
    setStep(soloAmbulatorio ? 'items' : 'contexto');
    setError('');
    setSelected({});
    setRestriccionesEnsayos({});
    void api<Record<string, { bloqueado: boolean; mensaje: string | null }>>(
      `/lab/pacientes/${p.id}/restricciones-ensayos/`
    )
      .then((data) => setRestriccionesEnsayos(data || {}))
      .catch(() => setRestriccionesEnsayos({}));
  };

  const toggleItem = (item: LabCatalogItem) => {
    const k = keyOf(item);
    if (selected[k]) {
      setSelected((prev) => {
        const next = { ...prev };
        delete next[k];
        return next;
      });
      return;
    }
    const bloqueo = mensajeBloqueoItem(item);
    if (bloqueo) {
      Alert.alert('Ensayo no permitido', bloqueo);
      return;
    }
    setSelected((prev) => ({ ...prev, [k]: item }));
  };

  const aplicarPaquete = (paq: PaqueteLabMovil) => {
    const bloqueo = mensajeBloqueoPaquete(paq);
    if (bloqueo) {
      Alert.alert('Ensayo no permitido', bloqueo);
      return;
    }
    setSelected((prev) => {
      const next = { ...prev };
      for (const p of paq.paneles) next[keyOf(p)] = p;
      for (const e of paq.examenes) next[keyOf(e)] = e;
      return next;
    });
  };

  const persistFavoritos = async (items: LabCatalogItem[]) => {
    try {
      await api('/lab/favoritos/', 'PUT', {
        items: items.map((i) => ({ kind: i.kind, id: i.id })),
      });
      await loadCatalogo(contexto, searchCat);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudieron guardar favoritos.');
    }
  };

  const toggleFavorito = async (item: LabCatalogItem) => {
    const current = new Map(favoritos.map((f) => [keyOf(f), f]));
    if (current.has(keyOf(item))) current.delete(keyOf(item));
    else current.set(keyOf(item), { ...item, favorito: true });
    await persistFavoritos([...current.values()]);
  };

  const enviar = async () => {
    if (!paciente) return;
    if (!selectedList.length) {
      setError('Seleccioná al menos un panel o examen.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const examenes_ids = selectedList.filter((i) => i.kind === 'examen').map((i) => i.id);
      const paneles_ids = selectedList.filter((i) => i.kind === 'panel').map((i) => i.id);
      const data = await api<{ mensaje: string; orden: { numero?: string; id: number }; merged: boolean }>(
        '/lab/ordenes/',
        'POST',
        {
          paciente_id: paciente.id,
          contexto,
          examenes_ids,
          paneles_ids,
          observaciones: obs.trim(),
        }
      );
      Alert.alert(
        data.merged ? 'Orden actualizada' : 'Pedido enviado',
        `${data.mensaje}\n${data.orden?.numero || `Orden #${data.orden?.id}`}`,
        [
          { text: 'Otro pedido', onPress: () => router.replace('/lab/nueva') },
          { text: 'Listo', onPress: () => router.replace('/lab') },
        ]
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo enviar el pedido.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Page>
      <Title>Nuevo pedido</Title>
      <Body>
        {step === 'paciente' && `${pasoActual}/${totalPasos} · Buscá al paciente`}
        {step === 'contexto' && `${pasoActual}/${totalPasos} · Confirmá el contexto`}
        {step === 'items' && `${pasoActual}/${totalPasos} · Elegí paneles, paquetes o exámenes sueltos`}
        {step === 'confirmar' && `${pasoActual}/${totalPasos} · Revisá y enviá a laboratorio`}
      </Body>
      <ErrorText text={error} />

      {step === 'paciente' && (
        <>
          <Card>
            <Field
              label="DNI o apellido"
              value={q}
              onChangeText={setQ}
              autoCorrect={false}
              onSubmitEditing={() => void buscarPacientes()}
            />
            <Action title={busy ? 'Buscando…' : 'Buscar'} disabled={busy || q.trim().length < 2} onPress={() => void buscarPacientes()} />
          </Card>
          {pacientes.map((p) => (
            <Card key={p.id}>
              <Text style={{ fontWeight: '800', fontSize: 18, color: colors.ink }}>{p.nombre_completo}</Text>
              <Body>DNI {p.dni || '—'}</Body>
              {p.internacion_activa ? (
                <Body>Internado{p.sector_internacion ? ` · ${p.sector_internacion}` : ''}</Body>
              ) : null}
              <Action title="Seleccionar" onPress={() => elegirPaciente(p)} />
            </Card>
          ))}
        </>
      )}

      {step === 'contexto' && paciente && (
        <>
          <Card>
            <Text style={{ fontWeight: '800', fontSize: 20, color: colors.ink }}>{paciente.nombre_completo}</Text>
            <Body>DNI {paciente.dni || '—'}</Body>
          </Card>
          <Card>
            <Body>¿Dónde está el paciente ahora?</Body>
            <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
              {contextosPermitidos.map((c) => (
                <Chip
                  key={c.id}
                  label={c.label}
                  selected={contexto === c.id}
                  onPress={() => setContexto(c.id)}
                />
              ))}
            </View>
          </Card>
          <Action title="Continuar" onPress={() => setStep('items')} />
          <Action title="Cambiar paciente" secondary onPress={() => setStep('paciente')} />
        </>
      )}

      {step === 'items' && (
        <>
          <Card>
            <Body>
              Seleccionados: {selectedList.length}
              {selectedList.length ? ` · ${selectedList.map((i) => i.nombre).join(', ')}` : ''}
            </Body>
            <Action
              title="Revisar y enviar"
              disabled={!selectedList.length}
              onPress={() => setStep('confirmar')}
            />
          </Card>

          <Card>
            <Field
              label="Complementar: buscar examen o panel"
              placeholder="Ej. potasio, hemograma…"
              value={searchCat}
              onChangeText={setSearchCat}
              autoCorrect={false}
              onSubmitEditing={() => void loadCatalogo(contexto, searchCat)}
            />
            <Action
              title={catalogLoading ? 'Buscando…' : 'Buscar en catálogo'}
              secondary
              disabled={catalogLoading}
              onPress={() => void loadCatalogo(contexto, searchCat)}
            />
          </Card>

          {catalogLoading && <Loading />}

          {!!favoritos.length && (
            <Card>
              <Text style={{ fontWeight: '800', fontSize: 18, color: colors.ink }}>Favoritos</Text>
              {favoritos.map((item) => (
                <SelectRow
                  key={keyOf(item)}
                  item={item}
                  selected={Boolean(selected[keyOf(item)])}
                  onToggle={() => toggleItem(item)}
                  onToggleFav={() => void toggleFavorito(item)}
                />
              ))}
            </Card>
          )}

          {!!paquetes.length && (
            <Card>
              <Text style={{ fontWeight: '800', fontSize: 18, color: colors.ink }}>
                Paquetes ({contexto.toLowerCase()})
              </Text>
              {paquetes.map((paq) => (
                <View
                  key={paq.id}
                  style={{ borderTopWidth: 1, borderTopColor: colors.border, paddingTop: 10, gap: 8 }}
                >
                  <Text style={{ fontWeight: '700', color: colors.ink }}>{paq.nombre}</Text>
                  {paq.descripcion ? <Body>{paq.descripcion}</Body> : null}
                  <Action title="Agregar paquete" secondary onPress={() => aplicarPaquete(paq)} />
                </View>
              ))}
            </Card>
          )}

          {(!!paneles.length || !!examenes.length) && (
            <Card>
              <Text style={{ fontWeight: '800', fontSize: 18, color: colors.ink }}>
                {searchCat.trim() ? 'Resultados de búsqueda' : 'Catálogo (podés complementar)'}
              </Text>
              {paneles.map((item) => (
                <SelectRow
                  key={keyOf(item)}
                  item={item}
                  selected={Boolean(selected[keyOf(item)])}
                  onToggle={() => toggleItem(item)}
                  onToggleFav={() => void toggleFavorito(item)}
                />
              ))}
              {examenes.map((item) => (
                <SelectRow
                  key={keyOf(item)}
                  item={item}
                  selected={Boolean(selected[keyOf(item)])}
                  onToggle={() => toggleItem(item)}
                  onToggleFav={() => void toggleFavorito(item)}
                />
              ))}
            </Card>
          )}

          <Action
            title="Volver"
            secondary
            onPress={() => setStep(soloAmbulatorio ? 'paciente' : 'contexto')}
          />
        </>
      )}

      {step === 'confirmar' && paciente && (
        <>
          <Card>
            <Text style={{ fontWeight: '800', fontSize: 22, color: colors.ink }}>{paciente.nombre_completo}</Text>
            <Body>DNI {paciente.dni || '—'}</Body>
            <Body>
              Contexto:{' '}
              {contexto === 'GUARDIA' ? 'Guardia' : contexto === 'INTERNACION' ? 'Internado' : 'Ambulatorio'}
            </Body>
          </Card>
          <Card>
            <Text style={{ fontWeight: '800', fontSize: 18, color: colors.ink }}>Análisis</Text>
            {selectedList.map((i) => (
              <Body key={keyOf(i)}>
                · {i.nombre} ({i.kind === 'panel' ? 'panel' : 'examen'})
              </Body>
            ))}
          </Card>
          <Card>
            <Field
              label="Observación (opcional)"
              value={obs}
              onChangeText={setObs}
              multiline
              maxLength={500}
            />
          </Card>
          <Action title={busy ? 'Enviando…' : 'Enviar a laboratorio'} disabled={busy} onPress={() => void enviar()} />
          <Action title="Seguir editando" secondary disabled={busy} onPress={() => setStep('items')} />
        </>
      )}
    </Page>
  );
}
