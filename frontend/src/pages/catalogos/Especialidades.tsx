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
import { canAccessCatalogosClinicos, canEditCatalogosClinicos } from '../../utils/permissions';

const Especialidades: React.FC = () => {
  const { currentUser } = useData();
  const [items, setItems] = useState<Especialidad[]>([]);
  const [loading, setLoading] = useState(true);

  const canView = canAccessCatalogosClinicos(currentUser);
  const canEdit = canEditCatalogosClinicos(currentUser);

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

  if (!canView) {
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
      readOnly={!canEdit}
      fields={[
        { key: 'nombre', label: 'Nombre', type: 'text', required: true },
        { key: 'descripcion', label: 'Descripción', type: 'textarea' },
      ]}
    />
  );
};

export default Especialidades;

