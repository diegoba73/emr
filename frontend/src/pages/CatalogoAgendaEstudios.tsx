import React, { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useData } from '../contexts/DataContext';
import { canAsignarTurnoEstudio } from '../modules/estudios/permissions';
import { listTiposEstudioComplementario } from '../services/estudiosComplementariosApi';
import {
  createMedicoTipo,
  createTipoSala,
  deleteMedicoTipo,
  deleteTipoSala,
  listMedicoTipos,
  listTipoSalas,
  type MedicoTipoEstudioRow,
  type TipoEstudioSalaRow,
} from '../services/pedidosEstudioApi';
import { getSafeClinicalActionMessage } from '../utils/apiError';
import type { TipoEstudioComplementario } from '../types/estudios';

const CatalogoAgendaEstudios: React.FC = () => {
  const { currentUser, medicos, loadMedicos, recursos, loadRecursos } = useData();
  const puede = canAsignarTurnoEstudio(currentUser);
  const [tipos, setTipos] = useState<TipoEstudioComplementario[]>([]);
  const [medicoTipos, setMedicoTipos] = useState<MedicoTipoEstudioRow[]>([]);
  const [tipoSalas, setTipoSalas] = useState<TipoEstudioSalaRow[]>([]);
  const [medicoId, setMedicoId] = useState<number | ''>('');
  const [tipoParaMedico, setTipoParaMedico] = useState<number | ''>('');
  const [tipoParaSala, setTipoParaSala] = useState<number | ''>('');
  const [salaId, setSalaId] = useState<number | ''>('');
  const [error, setError] = useState('');
  const [ok, setOk] = useState('');

  const salas = (recursos || []).filter(
    (r) =>
      r.activo !== false &&
      (r.tipo_recurso === 'SALA_PROCEDIMIENTO' || r.tipo_recurso === 'SALA_HEMODINAMIA')
  );

  const reload = useCallback(async () => {
    setError('');
    try {
      const [t, mt, ts] = await Promise.all([
        listTiposEstudioComplementario(),
        listMedicoTipos(),
        listTipoSalas(),
      ]);
      setTipos(t);
      setMedicoTipos(mt);
      setTipoSalas(ts);
      await Promise.all([loadMedicos?.(), loadRecursos?.()]);
    } catch (e) {
      setError(getSafeClinicalActionMessage(e, 'No se pudo cargar el catálogo.'));
    }
  }, [loadMedicos, loadRecursos]);

  useEffect(() => {
    void reload();
  }, [reload]);

  if (!puede) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>No tenés permiso para editar este catálogo.</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, maxWidth: 900 }}>
      <Typography variant="h5" gutterBottom>
        Catálogo agenda de estudios
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Asociá qué estudios realiza cada médico y en qué salas se hacen. La bandeja de pedidos y el
        alta de estudios usan este catálogo.
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}
      {ok && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setOk('')}>
          {ok}
        </Alert>
      )}

      <Typography variant="h6" sx={{ mt: 2 }}>
        Médico → tipos de estudio
      </Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ my: 1 }}>
        <TextField
          select
          label="Médico"
          value={medicoId}
          onChange={(e) => setMedicoId(e.target.value ? Number(e.target.value) : '')}
          sx={{ minWidth: 220 }}
        >
          {(medicos || []).map((m) => (
            <MenuItem key={m.id} value={m.id}>
              {m.apellido}, {m.nombre}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Tipo"
          value={tipoParaMedico}
          onChange={(e) => setTipoParaMedico(e.target.value ? Number(e.target.value) : '')}
          sx={{ minWidth: 220 }}
        >
          {tipos.map((t) => (
            <MenuItem key={t.id} value={t.id}>
              {t.nombre}
            </MenuItem>
          ))}
        </TextField>
        <Button
          variant="contained"
          disabled={!medicoId || !tipoParaMedico}
          onClick={async () => {
            try {
              await createMedicoTipo(Number(medicoId), Number(tipoParaMedico));
              setOk('Vínculo médico–tipo guardado.');
              await reload();
            } catch (e) {
              setError(getSafeClinicalActionMessage(e, 'No se pudo guardar.'));
            }
          }}
        >
          Agregar
        </Button>
      </Stack>
      <Stack spacing={0.5} sx={{ mb: 3 }}>
        {medicoTipos.map((r) => (
          <Box key={r.id} sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
            <Typography variant="body2">
              {r.medico_nombre} → {r.tipo_estudio_nombre}
            </Typography>
            <Button
              size="small"
              color="error"
              onClick={async () => {
                await deleteMedicoTipo(r.id);
                await reload();
              }}
            >
              Quitar
            </Button>
          </Box>
        ))}
      </Stack>

      <Typography variant="h6">Tipo de estudio → salas</Typography>
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ my: 1 }}>
        <TextField
          select
          label="Tipo"
          value={tipoParaSala}
          onChange={(e) => setTipoParaSala(e.target.value ? Number(e.target.value) : '')}
          sx={{ minWidth: 220 }}
        >
          {tipos.map((t) => (
            <MenuItem key={t.id} value={t.id}>
              {t.nombre}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Sala"
          value={salaId}
          onChange={(e) => setSalaId(e.target.value ? Number(e.target.value) : '')}
          sx={{ minWidth: 220 }}
        >
          {salas.map((r) => (
            <MenuItem key={r.id} value={r.id}>
              {r.nombre}
            </MenuItem>
          ))}
        </TextField>
        <Button
          variant="contained"
          disabled={!tipoParaSala || !salaId}
          onClick={async () => {
            try {
              await createTipoSala(Number(tipoParaSala), Number(salaId));
              setOk('Vínculo tipo–sala guardado.');
              await reload();
            } catch (e) {
              setError(getSafeClinicalActionMessage(e, 'No se pudo guardar.'));
            }
          }}
        >
          Agregar
        </Button>
      </Stack>
      <Stack spacing={0.5}>
        {tipoSalas.map((r) => (
          <Box key={r.id} sx={{ display: 'flex', justifyContent: 'space-between', gap: 1 }}>
            <Typography variant="body2">
              {r.tipo_estudio_nombre} → {r.recurso_nombre}
            </Typography>
            <Button
              size="small"
              color="error"
              onClick={async () => {
                await deleteTipoSala(r.id);
                await reload();
              }}
            >
              Quitar
            </Button>
          </Box>
        ))}
      </Stack>
    </Box>
  );
};

export default CatalogoAgendaEstudios;
