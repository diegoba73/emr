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
import { canAccessCatalogosClinicos, canEditCatalogosClinicos } from '../../utils/permissions';

const Procedimientos: React.FC = () => {
  const { currentUser } = useData();
  const [items, setItems] = useState<ProcedimientoCatalogo[]>([]);
  const [loading, setLoading] = useState(true);

  const canView = canAccessCatalogosClinicos(currentUser);
  const canEdit = canEditCatalogosClinicos(currentUser);

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

  if (!canView) {
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
      readOnly={!canEdit}
      fields={[
        { key: 'nombre', label: 'Nombre', type: 'text', required: true },
        { key: 'descripcion', label: 'Descripción', type: 'textarea' },
        { key: 'activo', label: 'Activo' },
      ]}
    />
  );
};

export default Procedimientos;

