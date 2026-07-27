import React, { useState, useCallback } from 'react';
import { Alert, Box } from '@mui/material';
import { useData } from '../contexts/DataContext';
import { Recurso } from '../types';
import {
  getRecursos,
  createRecurso,
  updateRecurso,
  deleteRecurso,
} from '../services/apiService';
import CatalogoBase from './catalogos/CatalogoBase';
import { normalizeRol } from '../utils/permissions';

const UBICACION_OPTIONS = [
  { value: 'CEHTA', label: 'CEHTA' },
  { value: 'ICPL', label: 'ICPL' },
];

const TIPO_RECURSO_OPTIONS = [
  { value: 'CONSULTORIO', label: 'Consultorio Ambulatorio' },
  { value: 'GUARDIA', label: 'Guardia' },
  { value: 'SALA_PROCEDIMIENTO', label: 'Sala de Procedimiento/Estudio' },
  { value: 'SALA_HEMODINAMIA', label: 'Sala de Hemodinamia' },
  { value: 'QUIROFANO', label: 'Quirófano' },
];

const Recursos: React.FC = () => {
  const { currentUser, loadRecursos } = useData();
  const [items, setItems] = useState<Recurso[]>([]);
  const [loading, setLoading] = useState(true);

  const isAdmin =
    normalizeRol(currentUser) === 'admin' || Boolean(currentUser?.is_superuser);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getRecursos();
      setItems(data);
      // Mantener sincronizado el contexto usado por agenda/turnos.
      void loadRecursos();
    } catch (error) {
      console.error('Error loading recursos:', error);
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [loadRecursos]);

  if (!isAdmin) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">
          No tiene permisos para acceder a esta sección. Solo los administradores
          pueden gestionar consultorios, salas y quirófanos.
        </Alert>
      </Box>
    );
  }

  return (
    <CatalogoBase<Recurso>
      title="Recursos físicos"
      items={items}
      loading={loading}
      onLoad={loadData}
      onCreate={createRecurso}
      onUpdate={updateRecurso}
      onDelete={deleteRecurso}
      searchFields={['nombre', 'ubicacion', 'tipo_recurso', 'tipo_recurso_display']}
      fields={[
        { key: 'nombre', label: 'Nombre', type: 'text', required: true },
        {
          key: 'ubicacion',
          label: 'Ubicación',
          type: 'select',
          required: true,
          options: UBICACION_OPTIONS,
        },
        {
          key: 'tipo_recurso',
          label: 'Tipo de recurso',
          type: 'select',
          required: true,
          options: TIPO_RECURSO_OPTIONS,
        },
      ]}
    />
  );
};

export default Recursos;
