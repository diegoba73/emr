import React, { useState, useCallback } from 'react';
import { useData } from '../../contexts/DataContext';
import { TipoDieta } from '../../types';
import {
  getTiposDieta,
  createTipoDieta,
  updateTipoDieta,
  deleteTipoDieta,
} from '../../services/internacion';
import CatalogoBase from './CatalogoBase';
import { canAccessInternacion, canManageInternacionInfra } from '../../utils/permissions';

const TiposDieta: React.FC = () => {
  const { currentUser } = useData();
  const [items, setItems] = useState<TipoDieta[]>([]);
  const [loading, setLoading] = useState(true);

  const canView = canAccessInternacion(currentUser);
  const canEdit = canManageInternacionInfra(currentUser);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getTiposDieta(true);
      setItems(data);
    } catch (error) {
      console.error('Error loading tipos de dieta:', error);
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
    <CatalogoBase<TipoDieta>
      title="Tipos de dieta"
      items={items}
      loading={loading}
      onLoad={loadData}
      onCreate={createTipoDieta}
      onUpdate={updateTipoDieta}
      onDelete={deleteTipoDieta}
      readOnly={!canEdit}
      fields={[
        { key: 'nombre', label: 'Nombre', type: 'text', required: true },
        { key: 'descripcion', label: 'Descripción', type: 'textarea' },
        { key: 'activo', label: 'Activo' },
      ]}
    />
  );
};

export default TiposDieta;
