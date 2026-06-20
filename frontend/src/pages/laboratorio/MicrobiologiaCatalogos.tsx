import React, { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Paper,
  Tab,
  Tabs,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useData } from '../../contexts/DataContext';
import type { Antibiotico, MedioCultivo, Microorganismo } from '../../types/lims';
import {
  createAntibiotico,
  createMedioCultivo,
  createMicroorganismo,
  formatDrfError,
  listAntibioticos,
  listMediosCultivo,
  listMicroorganismos,
} from '../../services/limsApi';
import { canAccessMicrobiologia, canEditMicroCatalogos } from '../../utils/limsAccess';

const MicrobiologiaCatalogos: React.FC = () => {
  const navigate = useNavigate();
  const { currentUser } = useData();
  const [tab, setTab] = useState(0);
  const [medios, setMedios] = useState<MedioCultivo[]>([]);
  const [micros, setMicros] = useState<Microorganismo[]>([]);
  const [abs, setAbs] = useState<Antibiotico[]>([]);
  const [codigo, setCodigo] = useState('');
  const [nombre, setNombre] = useState('');

  const allowed = canAccessMicrobiologia(currentUser);
  const canEdit = canEditMicroCatalogos(currentUser);

  const load = async () => {
    try {
      const [m, mi, a] = await Promise.all([listMediosCultivo(), listMicroorganismos(), listAntibioticos()]);
      setMedios(m);
      setMicros(mi);
      setAbs(a);
    } catch (e) {
      toast.error(formatDrfError(e));
    }
  };

  useEffect(() => {
    if (allowed) load();
  }, [allowed]);

  const crear = async () => {
    if (!codigo.trim() || !nombre.trim()) {
      toast.error('Código y nombre obligatorios');
      return;
    }
    try {
      if (tab === 0) await createMedioCultivo({ codigo, nombre, activo: true });
      else if (tab === 1) await createMicroorganismo({ codigo, nombre, activo: true });
      else await createAntibiotico({ codigo, nombre, activo: true });
      toast.success('Catálogo actualizado');
      setCodigo('');
      setNombre('');
      load();
    } catch (e) {
      toast.error(formatDrfError(e));
    }
  };

  if (!allowed) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>Sin acceso.</Typography>
      </Box>
    );
  }

  const rows = tab === 0 ? medios : tab === 1 ? micros : abs;

  return (
    <Box sx={{ p: 2 }}>
      <Button size="small" onClick={() => navigate('/laboratorio/microbiologia/estudios')} sx={{ mb: 1 }}>
        ← Estudios
      </Button>
      <Typography variant="h5" gutterBottom>
        Catálogos microbiología
      </Typography>
      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 2 }}>
        <Tab label="Medios" />
        <Tab label="Microorganismos" />
        <Tab label="Antibióticos" />
      </Tabs>
      <TableContainer component={Paper} sx={{ mb: 2 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Código</TableCell>
              <TableCell>Nombre</TableCell>
              <TableCell>Activo</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.id}>
                <TableCell>{r.codigo}</TableCell>
                <TableCell>{r.nombre}</TableCell>
                <TableCell>{r.activo === false ? 'No' : 'Sí'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {canEdit && (
        <Paper sx={{ p: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Alta (solo admin)
          </Typography>
          <TextField size="small" label="Código" value={codigo} onChange={(e) => setCodigo(e.target.value)} sx={{ mr: 1 }} />
          <TextField size="small" label="Nombre" value={nombre} onChange={(e) => setNombre(e.target.value)} sx={{ mr: 1 }} />
          <Button variant="contained" onClick={crear}>
            Crear
          </Button>
        </Paper>
      )}
      {!canEdit && (
        <Typography variant="caption" color="text.secondary">
          Solo lectura: la edición de catálogos requiere rol administrador.
        </Typography>
      )}
    </Box>
  );
};

export default MicrobiologiaCatalogos;
