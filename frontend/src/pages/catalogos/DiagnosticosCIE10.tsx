import React, { useState, useCallback } from 'react';
import { useData } from '../../contexts/DataContext';
import { DiagnosticoCIE10 } from '../../types';
import {
  getDiagnosticosCIE10,
  createDiagnosticoCIE10,
  updateDiagnosticoCIE10,
  deleteDiagnosticoCIE10,
} from '../../services/apiService';
import CatalogoBase from './CatalogoBase';
import { canAccessCatalogosClinicos, canEditCatalogosClinicos } from '../../utils/permissions';

const DiagnosticosCIE10: React.FC = () => {
  const { currentUser } = useData();
  const [items, setItems] = useState<DiagnosticoCIE10[]>([]);
  const [loading, setLoading] = useState(true);

  const canView = canAccessCatalogosClinicos(currentUser);
  const canEdit = canEditCatalogosClinicos(currentUser);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getDiagnosticosCIE10();
      setItems(data);
    } catch (error) {
      console.error('Error loading diagnosticos CIE-10:', error);
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
    <CatalogoBase<DiagnosticoCIE10>
      title="Diagnósticos CIE-10"
      items={items}
      loading={loading}
      onLoad={loadData}
      onCreate={createDiagnosticoCIE10}
      onUpdate={updateDiagnosticoCIE10}
      onDelete={deleteDiagnosticoCIE10}
      readOnly={!canEdit}
      searchFields={['codigo', 'descripcion', 'enfermedad', 'capitulo']}
      fields={[
        { key: 'codigo', label: 'Código', type: 'text', required: true },
        { key: 'descripcion', label: 'Descripción', type: 'textarea', required: true },
        { key: 'categoria', label: 'Categoría', type: 'text' },
        { key: 'capitulo', label: 'Capítulo', type: 'text' },
        { key: 'enfermedad', label: 'Enfermedad', type: 'text' },
        { key: 'tipo_enfermedad', label: 'Tipo de Enfermedad', type: 'text' },
        { key: 'activo', label: 'Activo' },
      ]}
    />
  );
};

export default DiagnosticosCIE10;

