import React, { useState } from 'react';
import { useSession } from '../lib/session';
import { Action, Body, Card, ErrorText, Field, Page, Title } from '../components/ui';
export default function Institution() {
  const {link} = useSession();
  const [code,setCode] = useState('');
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const submit = async()=>{
    if(busy)return;
    setBusy(true);setError('');
    try { await link(code); }
    catch(e){setError(e instanceof Error?e.message:'No se pudo vincular la clínica.');}
    finally{setBusy(false);}
  };
  return <Page><Title>SYNESIS movil</Title><Body>Vinculá tu clínica</Body>
    <Card><Body>Ingresá el código que te entregó tu institución. Luego podrás iniciar sesión con tu usuario de esa clínica.</Body>
      <Field label="Código de clínica" placeholder="Ejemplo: ICPL" value={code} onChangeText={setCode} autoCapitalize="characters" autoCorrect={false} maxLength={40} editable={!busy} onSubmitEditing={submit}/>
      <ErrorText text={error}/><Action title={busy?'Verificando…':'Vincular clínica'} disabled={busy||!code.trim()} onPress={submit}/>
    </Card></Page>;
}
