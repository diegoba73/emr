import React, { useState } from 'react';
import { useData } from '../contexts/DataContext';
import SearchAndFilters from '../components/SearchAndFilters';
// Material-UI imports removidos - ya no se necesita el formulario
import './Solicitudes.css';

const Solicitudes: React.FC = () => {
  const { solicitudes, pacientes, medicos, loading, loadSolicitudes, loadPacientes, loadMedicos, currentUser } = useData();
  
  // Variables de formulario eliminadas - ya no se crean solicitudes desde EMR
  const [filterEstado, setFilterEstado] = useState<string>('');

  const [searchTerm, setSearchTerm] = useState('');

  // Eliminado: efecto que recargaba continuamente cuando las listas estaban vacías

  // Catálogo LIMS eliminado - ya no se seleccionan exámenes desde EMR

  // Funciones de formulario eliminadas - ya no se crean solicitudes desde EMR

  const filteredSolicitudes = solicitudes.filter(solicitud => {
    const matchesEstado = !filterEstado || solicitud.estado === filterEstado;
    
    const paciente = pacientes.find(p => p.id === solicitud.paciente);
    const medico = medicos.find(m => m.id === solicitud.medico_solicitante);
    
    const matchesSearch = !searchTerm || 
      (paciente && (paciente.nombre.toLowerCase().includes(searchTerm.toLowerCase()) || 
                   paciente.apellido.toLowerCase().includes(searchTerm.toLowerCase()))) ||
      (medico && (medico.nombre.toLowerCase().includes(searchTerm.toLowerCase()) || 
                 medico.apellido.toLowerCase().includes(searchTerm.toLowerCase()))) ||
      solicitud.descripcion?.toLowerCase().includes(searchTerm.toLowerCase());

    return matchesEstado && matchesSearch;
  });

  const getEstadoColor = (estado: string) => {
    switch (estado) {
      case 'PENDIENTE': return '#ff9800';
      case 'EN_PROCESO': return '#2196f3';
      case 'COMPLETADA': return '#4caf50';
      case 'CANCELADA': return '#f44336';
      case 'ERROR': return '#9c27b0';
      default: return '#757575';
    }
  };

  // Prioridad removida

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('es-ES');
  };

  if (loading.solicitudes) {
    return (
      <div className="solicitudes-container">
        <div className="loading">Cargando solicitudes...</div>
      </div>
    );
  }

  return (
    <div className="solicitudes-container fade-in">
      {!currentUser ? (
        <div className="auth-message">
          <h2>🔐 Autenticación Requerida</h2>
          <p>Debes iniciar sesión para acceder a la gestión de solicitudes.</p>
        </div>
      ) : (
        <>
          <div className="solicitudes-header">
            <h1>📋 Consulta de Solicitudes y Resultados</h1>
            <p className="header-description">
              Las solicitudes se crean desde el LIMS. Aquí puedes consultar el estado y resultados.
            </p>
        
        <button 
          className="btn-secondary" 
          onClick={() => {
            loadSolicitudes();
            loadPacientes();
            loadMedicos();
          }}
          style={{ marginLeft: '10px' }}
        >
          🔄 Recargar Datos
        </button>
      </div>



      {/* Search and Filters */}
      <SearchAndFilters
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        searchPlaceholder="Buscar por paciente, médico o descripción..."
        filters={{
          estado: {
            value: filterEstado,
            label: 'Estado',
            options: [
              { value: 'PENDIENTE', label: 'Pendiente' },
              { value: 'EN_PROCESO', label: 'En Proceso' },
              { value: 'COMPLETADA', label: 'Completada' },
              { value: 'CANCELADA', label: 'Cancelada' },
              { value: 'ERROR', label: 'Error' },
            ],
            onChange: setFilterEstado,
          },
        }}
        onRefresh={() => {
          loadSolicitudes();
          loadPacientes();
          loadMedicos();
        }}
        onAdd={undefined}
        addButtonText=""
        totalItems={solicitudes.length}
        filteredItems={filteredSolicitudes.length}
      />

      {/* Formulario eliminado - Las solicitudes se crean desde el LIMS */}

      {/* Tabla de Solicitudes */}

      {/* Tabla de Solicitudes */}
      <div className="table-container">
        <table className="solicitudes-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Paciente</th>
              <th>Médico</th>
              <th>Tipo</th>
              <th>Estado</th>
              {/* Prioridad removida */}
              <th>Fecha Solicitud</th>
              <th>Fecha Límite</th>
              <th>Días Pendiente</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {filteredSolicitudes.map(solicitud => {
              const paciente = pacientes.find(p => p.id === solicitud.paciente);
              const medico = medicos.find(m => m.id === solicitud.medico_solicitante);
              
              return (
                <tr key={solicitud.id} className={solicitud.esta_vencida ? 'vencida' : ''}>
                  <td>{solicitud.id}</td>
                  <td>
                    {paciente ? `${paciente.nombre} ${paciente.apellido}` : 'N/A'}
                    <br />
                    <small>{paciente?.dni}</small>
                  </td>
                  <td>
                    {medico ? `${medico.nombre} ${medico.apellido}` : 'N/A'}
                    <br />
                                         <small>{typeof medico?.especialidad === 'string' ? medico.especialidad : medico?.especialidad?.nombre}</small>
                  </td>
                  <td>{solicitud.tipo_solicitud.replace('_', ' ')}</td>
                  <td>
                    <span 
                      className="estado-badge"
                      style={{ backgroundColor: getEstadoColor(solicitud.estado) }}
                    >
                      {solicitud.estado}
                    </span>
                  </td>
                  {/* Prioridad removida */}
                  <td>{formatDate(solicitud.fecha_solicitud)}</td>
                  <td>
                    {solicitud.fecha_limite ? formatDate(solicitud.fecha_limite) : 'N/A'}
                    {solicitud.esta_vencida && <span className="vencida-indicator">⚠️</span>}
                  </td>
                  <td>
                    {solicitud.dias_pendiente !== undefined ? (
                      <span className={solicitud.dias_pendiente > 7 ? 'dias-alto' : ''}>
                        {solicitud.dias_pendiente} días
                      </span>
                    ) : 'N/A'}
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button 
                        className="btn-view"
                        onClick={() => {
                          alert('Los detalles de la solicitud están disponibles en la tabla.');
                        }}
                        title="Ver detalles"
                      >
                        👁️
                      </button>
                      
                      {solicitud.estado === 'COMPLETADA' && (
                        <button 
                          className="btn-success"
                          onClick={() => {
                            alert('Los resultados se consultan desde el LIMS.');
                          }}
                          title="Ver resultados"
                        >
                          📊
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        
        {filteredSolicitudes.length === 0 && (
          <div className="no-data">
            <p>No se encontraron solicitudes con los filtros aplicados.</p>
          </div>
        )}
      </div>

      {/* Estadísticas */}
      <div className="stats-section">
        <div className="stat-card">
          <h3>Total</h3>
          <span className="stat-number">{solicitudes.length}</span>
        </div>
        <div className="stat-card">
          <h3>Pendientes</h3>
          <span className="stat-number">{solicitudes.filter(s => s.estado === 'PENDIENTE').length}</span>
        </div>
        <div className="stat-card">
          <h3>En Proceso</h3>
          <span className="stat-number">{solicitudes.filter(s => s.estado === 'EN_PROCESO').length}</span>
        </div>
        <div className="stat-card">
          <h3>Completadas</h3>
          <span className="stat-number">{solicitudes.filter(s => s.estado === 'COMPLETADA').length}</span>
        </div>
        <div className="stat-card">
          <h3>Vencidas</h3>
          <span className="stat-number">{solicitudes.filter(s => s.esta_vencida).length}</span>
        </div>
      </div>
        </>
      )}
    </div>
  );
};

export default Solicitudes;
