import { Alert } from 'react-native';
import React, { useState } from 'react';
import { useSession } from '../lib/session';
import { api } from '../lib/api';
import { enableReminders } from '../lib/notifications';
import { Action, Body, Card, ErrorText, Page, Title } from '../components/ui';
export default function Settings() {
  const { user,logout,changeClinic } = useSession();const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');const [error,setError]=useState('');
  const run = async (fn:()=>Promise<void>, text:string) => { setBusy(true);setError('');setMessage('');try { await fn();setMessage(text); } catch(e) {setError(e instanceof Error?e.message:'No se pudo completar la operación.');}finally{setBusy(false);} };
  return <Page><Title>Mi cuenta</Title><Body>{user?.nombre}</Body><ErrorText text={error}/>{message && <Body>{message}</Body>}
    {user?.rol==='paciente' && <Card><Title>Recordatorios</Title><Body>Recibí un aviso aproximadamente 24 horas antes. Abrí el turno para confirmar tu asistencia, cancelar o reprogramar. La entrega depende de los permisos y la conexión del teléfono.</Body>
      <Action title="Activar recordatorios" disabled={busy} onPress={()=>run(enableReminders,'Recordatorios activados en este celular.')} />
      <Action title="Desactivar en este celular" secondary disabled={busy} onPress={()=>run(async()=>{await api('/push/','DELETE');},'Recordatorios desactivados.')} /></Card>}
    <Body>La configuración de horarios de atención corresponde a secretaría y administración, desde el EMR.</Body>
    <Action title="Cambiar clínica" secondary disabled={busy} onPress={()=>Alert.alert("Cambiar clínica","Se cerrará tu sesión. Deberás ingresar con el usuario de la otra institución.",[{text:"Volver",style:"cancel"},{text:"Continuar",onPress:()=>run(changeClinic,'')}])} />
    <Action title="Cerrar sesión" secondary disabled={busy} onPress={()=>run(logout,'')} />
  </Page>;
}
