import React, { useState, useCallback } from 'react';
import { useData } from '../../contexts/DataContext';
import { Especialidad } from '../../types';
import {
  getEspecialidades,
  createEspecialidad,
  updateEspecialidad,
  deleteEspecialidad,
} from '../../services/apiService';
import CatalogoBase from './CatalogoBase';

const Especialidades: React.FC = () => {
  const { currentUser } = useData();
  const [items, setItems] = useState<Especialidad[]>([]);
  const [loading, setLoading] = useState(true);

  // Verificar permisos - médicos y admin
  const canEdit = currentUser?.rol === 'MEDICO' || currentUser?.rol === 'ADMIN' || currentUser?.is_superuser;

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getEspecialidades();
      setItems(data);
    } catch (error) {
      console.error('Error loading especialidades:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  if (!canEdit) {
    return (
      <div style={{ padding: '20px' }}>
        <p>No tiene permisos para acceder a esta sección.</p>
      </div>
    );
  }

  return (
    <CatalogoBase<Especialidad>
      title="Especialidades"
      items={items}
      loading={loading}
      onLoad={loadData}
      onCreate={createEspecialidad}
      onUpdate={updateEspecialidad}
      onDelete={deleteEspecialidad}
      fields={[
        { key: 'nombre', label: 'Nombre', type: 'text', required: true },
        { key: 'descripcion', label: 'Descripción', type: 'textarea' },
      ]}
    />
  );
};

export default Especialidades;

