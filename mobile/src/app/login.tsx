import React, { useState } from 'react';
import { KeyboardAvoidingView, Platform, View, Text } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useSession } from '../lib/session';
import { Action, Body, Card, colors, ErrorText, Field, Page, Title } from '../components/ui';
export default function Login() {
  const { login,changeClinic } = useSession();
  const [username,setUsername] = useState(''); const [password,setPassword] = useState('');
  const [busy,setBusy] = useState(false); const [error,setError] = useState('');
  const submit = async () => {
    if(busy) return; setBusy(true);setError('');
    try { await login(username,password); setPassword(''); }
    catch(e) { setError(e instanceof Error ? e.message : 'No se pudo iniciar sesión.'); }
    finally { setBusy(false); }
  };
  return <SafeAreaView style={{flex:1,backgroundColor:colors.bg}}><KeyboardAvoidingView behavior={Platform.OS==='ios'?'padding':undefined} style={{flex:1}}><Page>
    <View style={{paddingTop:46,paddingBottom:24,gap:12}}><Text style={{fontWeight:'900',fontSize:17,color:colors.primary,letterSpacing:3}}>SYNESIS</Text><Title>Tu clínica, a mano.</Title><Body>Turnos e informes según tu rol en la institución.</Body></View>
    <Card><Field label="Usuario" value={username} onChangeText={setUsername} autoCapitalize="none" autoCorrect={false} autoComplete="username" editable={!busy} />
      <Field label="Contraseña" value={password} onChangeText={setPassword} secureTextEntry autoComplete="current-password" editable={!busy} onSubmitEditing={submit} />
      <ErrorText text={error} /><Action title={busy?'Ingresando…':'Ingresar'} disabled={busy || !username.trim() || !password} onPress={submit} />
    </Card><Action secondary title="Cambiar clínica" disabled={busy} onPress={()=>{void changeClinic().catch(e=>setError(e.message));}}/><Body>Pacientes, médicos, secretaría, laboratorio y bioquímicos pueden ingresar con su usuario del EMR.</Body>
  </Page></KeyboardAvoidingView></SafeAreaView>;
}
