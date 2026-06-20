import React, { useState, useCallback } from 'react';
import { useData } from '../../contexts/DataContext';
import { Medicamento } from '../../types';
import {
  getMedicamentos,
  createMedicamento,
  updateMedicamento,
  deleteMedicamento,
} from '../../services/apiService';
import CatalogoBase from './CatalogoBase';

const Medicamentos: React.FC = () => {
  const { currentUser } = useData();
  const [items, setItems] = useState<Medicamento[]>([]);
  const [loading, setLoading] = useState(true);

  // Verificar permisos - médicos y admin
  const canEdit = currentUser?.rol === 'MEDICO' || currentUser?.rol === 'ADMIN' || currentUser?.is_superuser;

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getMedicamentos();
      setItems(data);
    } catch (error) {
      console.error('Error loading medicamentos:', error);
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
    <CatalogoBase<Medicamento>
      title="Medicamentos"
      items={items}
      loading={loading}
      onLoad={loadData}
      onCreate={createMedicamento}
      onUpdate={updateMedicamento}
      onDelete={deleteMedicamento}
      searchFields={['nombre', 'codigo_atc', 'principio_activo', 'descripcion']}
      fields={[
        { key: 'nombre', label: 'Nombre', type: 'text', required: true },
        { key: 'principio_activo', label: 'Principio Activo', type: 'text' },
        { key: 'codigo_atc', label: 'Código ATC', type: 'text' },
        { key: 'descripcion', label: 'Descripción', type: 'textarea' },
        { key: 'presentacion', label: 'Presentación', type: 'text' },
        { key: 'concentracion', label: 'Concentración', type: 'text' },
        { key: 'via_administracion', label: 'Vía de Administración', type: 'text' },
        { key: 'activo', label: 'Activo' },
      ]}
    />
  );
};

export default Medicamentos;

