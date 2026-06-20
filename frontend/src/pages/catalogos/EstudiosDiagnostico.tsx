import React, { useState, useCallback } from 'react';
import { useData } from '../../contexts/DataContext';
import { EstudioDiagnostico } from '../../types';
import {
  getEstudiosDiagnostico,
  createEstudioDiagnostico,
  updateEstudioDiagnostico,
  deleteEstudioDiagnostico,
} from '../../services/apiService';
import CatalogoBase from './CatalogoBase';

const EstudiosDiagnostico: React.FC = () => {
  const { currentUser } = useData();
  const [items, setItems] = useState<EstudioDiagnostico[]>([]);
  const [loading, setLoading] = useState(true);

  // Verificar permisos - médicos y admin
  const canEdit = currentUser?.rol === 'MEDICO' || currentUser?.rol === 'ADMIN' || currentUser?.is_superuser;

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getEstudiosDiagnostico();
      setItems(data);
    } catch (error) {
      console.error('Error loading estudios diagnostico:', error);
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
    <CatalogoBase<EstudioDiagnostico>
      title="Estudios Diagnósticos"
      items={items}
      loading={loading}
      onLoad={loadData}
      onCreate={createEstudioDiagnostico}
      onUpdate={updateEstudioDiagnostico}
      onDelete={deleteEstudioDiagnostico}
      fields={[
        { key: 'nombre', label: 'Nombre', type: 'text', required: true },
        { key: 'descripcion', label: 'Descripción', type: 'textarea' },
        { key: 'activo', label: 'Activo' },
      ]}
    />
  );
};

export default EstudiosDiagnostico;

