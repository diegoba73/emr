import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';
import { TipoExamen, ApiResponse } from '../../types';
import './ListaExamenesTest.css';

const ListaExamenesTest: React.FC = () => {
  const [examenes, setExamenes] = useState<TipoExamen[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [totalCount, setTotalCount] = useState<number>(0);

  // Helper function para formatear el precio
  const formatPrecio = (precio: string | number | undefined): string => {
    if (precio === undefined || precio === null) return '0.00';
    const numPrecio = typeof precio === 'number' ? precio : parseFloat(String(precio));
    return isNaN(numPrecio) ? '0.00' : numPrecio.toFixed(2);
  };

  useEffect(() => {
    loadExamenes();
  }, [searchTerm]);

  const loadExamenes = async () => {
    try {
      setLoading(true);
      setError(null);
      const response: ApiResponse<TipoExamen> = await apiService.getTiposExamen(
        searchTerm || undefined
      );
      setExamenes(response.results || []);
      setTotalCount(response.count || 0);
    } catch (err: any) {
      console.error('Error cargando exámenes:', err);
      setError(
        err.response?.data?.detail ||
        err.message ||
        'Error al cargar los exámenes. Por favor, intenta nuevamente.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value);
  };

  if (loading && examenes.length === 0) {
    return (
      <div className="lista-examenes-container">
        <div className="loading-container">
          <p>Cargando exámenes...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="lista-examenes-container">
      <div className="lista-examenes-header">
        <h1>Catálogo de Exámenes de Laboratorio</h1>
        <p className="subtitle">Total de exámenes: {totalCount}</p>
      </div>

      <div className="search-container">
        <input
          type="text"
          placeholder="Buscar por nombre o código..."
          value={searchTerm}
          onChange={handleSearchChange}
          className="search-input"
        />
      </div>

      {error && (
        <div className="error-container">
          <p className="error-message">⚠️ {error}</p>
          <button onClick={loadExamenes} className="retry-button">
            Reintentar
          </button>
        </div>
      )}

      {!error && examenes.length === 0 && !loading && (
        <div className="empty-container">
          <p>No se encontraron exámenes.</p>
        </div>
      )}

      {!error && examenes.length > 0 && (
        <div className="table-container">
          <table className="examenes-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Código</th>
                <th>Nombre</th>
                <th>Abreviatura</th>
                <th>Tipo de Muestra</th>
                <th>Precio</th>
                <th>Rango de Referencia</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {examenes.map((examen) => (
                <tr key={examen.id}>
                  <td>{examen.id}</td>
                  <td>{examen.codigo}</td>
                  <td>{examen.nombre}</td>
                  <td>{examen.abreviatura || '-'}</td>
                  <td>
                    {examen.tipo_muestra_nombre || examen.tipo_muestra_codigo || '-'}
                  </td>
                  <td>${formatPrecio(examen.precio)}</td>
                  <td>{examen.rango_referencia_texto || '-'}</td>
                  <td>
                    <span className={`status-badge ${examen.activo ? 'activo' : 'inactivo'}`}>
                      {examen.activo ? 'Activo' : 'Inactivo'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {loading && examenes.length > 0 && (
        <div className="loading-overlay">
          <p>Actualizando...</p>
        </div>
      )}
    </div>
  );
};

export default ListaExamenesTest;

