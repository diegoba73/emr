import React, { useState, useCallback } from 'react';
import { useData } from '../../contexts/DataContext';
import { ProcedimientoCatalogo } from '../../types';
import {
  getProcedimientosCatalogo,
  createProcedimientoCatalogo,
  updateProcedimientoCatalogo,
  deleteProcedimientoCatalogo,
} from '../../services/apiService';
import CatalogoBase from './CatalogoBase';

const Procedimientos: React.FC = () => {
  const { currentUser } = useData();
  const [items, setItems] = useState<ProcedimientoCatalogo[]>([]);
  const [loading, setLoading] = useState(true);

  // Verificar permisos - médicos y admin
  const canEdit = currentUser?.rol === 'MEDICO' || currentUser?.rol === 'ADMIN' || currentUser?.is_superuser;

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getProcedimientosCatalogo();
      setItems(data);
    } catch (error) {
      console.error('Error loading procedimientos:', error);
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
    <CatalogoBase<ProcedimientoCatalogo>
      title="Procedimientos"
      items={items}
      loading={loading}
      onLoad={loadData}
      onCreate={createProcedimientoCatalogo}
      onUpdate={updateProcedimientoCatalogo}
      onDelete={deleteProcedimientoCatalogo}
      fields={[
        { key: 'nombre', label: 'Nombre', type: 'text', required: true },
        { key: 'descripcion', label: 'Descripción', type: 'textarea' },
        { key: 'activo', label: 'Activo' },
      ]}
    />
  );
};

export default Procedimientos;

