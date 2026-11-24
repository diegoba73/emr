import React, { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, View, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { api } from '../lib/api';
import { Action, Body, Card, colors, ErrorText, Field, Page, Title } from '../components/ui';

type ObraSocial = { id: number; codigo: string; nombre: string };

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [nombre, setNombre] = useState('');
  const [apellido, setApellido] = useState('');
  const [dni, setDni] = useState('');
  const [telefono, setTelefono] = useState('');
  const [fechaNacimiento, setFechaNacimiento] = useState('');
  const [obraSocial, setObraSocial] = useState('PARTICULAR');
  const [numeroAfiliado, setNumeroAfiliado] = useState('');
  const [plan, setPlan] = useState('');
  const [obras, setObras] = useState<ObraSocial[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [ok, setOk] = useState(false);

  const esParticular = obraSocial === 'PARTICULAR';

  useEffect(() => {
    void api<ObraSocial[]>('/obras-sociales/')
      .then((rows) => setObras(Array.isArray(rows) ? rows : []))
      .catch(() => setObras([{ id: 0, codigo: 'PARTICULAR', nombre: 'Particular' }]));
  }, []);

  const submit = async () => {
    if (busy) return;
    setBusy(true);
    setError('');
    try {
      const body: Record<string, string> = {
        email: email.trim(),
        password,
        nombre: nombre.trim(),
        apellido: apellido.trim(),
        dni: dni.trim(),
        telefono: telefono.trim(),
        fecha_nacimiento: fechaNacimiento.trim(),
        obra_social: obraSocial,
      };
      if (!esParticular) {
        body.numero_afiliado = numeroAfiliado.trim();
        body.plan = plan.trim();
      }
      await api('/auth/register/', 'POST', body);
      setOk(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo completar el registro.');
    } finally {
      setBusy(false);
    }
  };

  if (ok) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }}>
        <Page>
          <Title>Cuenta creada</Title>
          <Body>Ya podés ingresar con tu DNI y contraseña.</Body>
          <Action title="Ir a ingresar" onPress={() => router.replace('/login')} />
        </Page>
      </SafeAreaView>
    );
  }

  const coberturaOk = esParticular || (Boolean(numeroAfiliado.trim()) && Boolean(plan.trim()));

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        style={{ flex: 1 }}
      >
        <ScrollView keyboardShouldPersistTaps="handled">
          <Page>
            <View style={{ paddingTop: 24, paddingBottom: 12, gap: 8 }}>
              <Text style={{ fontWeight: '900', fontSize: 17, color: colors.primary, letterSpacing: 3 }}>
                SYNESIS
              </Text>
              <Title>Crear cuenta paciente</Title>
              <Body>Completá todos los campos. Si no tenés cobertura, elegí Particular.</Body>
            </View>
            <Card>
              <Field label="Email" value={email} onChangeText={setEmail} autoCapitalize="none" editable={!busy} />
              <Field
                label="Contraseña"
                value={password}
                onChangeText={setPassword}
                secureTextEntry
                editable={!busy}
              />
              <Field label="Nombre" value={nombre} onChangeText={setNombre} editable={!busy} />
              <Field label="Apellido" value={apellido} onChangeText={setApellido} editable={!busy} />
              <Field label="DNI" value={dni} onChangeText={setDni} autoCapitalize="none" editable={!busy} />
              <Field label="Teléfono" value={telefono} onChangeText={setTelefono} editable={!busy} />
              <Field
                label="Fecha nacimiento (AAAA-MM-DD)"
                value={fechaNacimiento}
                onChangeText={setFechaNacimiento}
                autoCapitalize="none"
                editable={!busy}
              />
              <Body>Obra social (código)</Body>
              {obras.map((o) => (
                <Action
                  key={o.codigo}
                  secondary={obraSocial !== o.codigo}
                  title={
                    o.codigo === 'PARTICULAR'
                      ? `${o.nombre} (sin cobertura)`
                      : o.nombre
                  }
                  disabled={busy}
                  onPress={() => {
                    setObraSocial(o.codigo);
                    if (o.codigo === 'PARTICULAR') {
                      setNumeroAfiliado('');
                      setPlan('');
                    }
                  }}
                />
              ))}
              {!esParticular && (
                <>
                  <Field
                    label="Número de afiliado"
                    value={numeroAfiliado}
                    onChangeText={setNumeroAfiliado}
                    editable={!busy}
                  />
                  <Field label="Plan" value={plan} onChangeText={setPlan} editable={!busy} />
                </>
              )}
              <ErrorText text={error} />
              <Action
                title={busy ? 'Registrando…' : 'Crear cuenta'}
                disabled={
                  busy ||
                  !email.trim() ||
                  !password ||
                  !nombre.trim() ||
                  !apellido.trim() ||
                  !dni.trim() ||
                  !telefono.trim() ||
                  !fechaNacimiento.trim() ||
                  !obraSocial ||
                  !coberturaOk
                }
                onPress={submit}
              />
            </Card>
            <Action secondary title="Volver al ingreso" disabled={busy} onPress={() => router.back()} />
          </Page>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}
