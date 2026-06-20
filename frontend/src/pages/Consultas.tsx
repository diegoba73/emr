import React, { useState, useEffect } from 'react';
import { Consulta } from '../types';
import { useData } from '../contexts/DataContext';
import SearchAndFilters from '../components/SearchAndFilters';
import './Consultas.css';

const Consultas: React.FC = () => {
  const { currentUser, consultas, loadConsultas, loading } = useData();
  const [selectedConsulta, setSelectedConsulta] = useState<Consulta | null>(null);
  const [showConsultaModal, setShowConsultaModal] = useState(false);
  const [filterPaciente, setFilterPaciente] = useState<string>('');
  const [filterMedico, setFilterMedico] = useState<string>('');

  useEffect(() => {
    loadConsultas();
  }, [loadConsultas]);

  const handleConsultaClick = (consulta: Consulta) => {
    setSelectedConsulta(consulta);
    setShowConsultaModal(true);
  };

  const handleCloseModal = () => {
    setShowConsultaModal(false);
    setSelectedConsulta(null);
  };

  // Normalizar consultas a array
  const consultasArray = React.useMemo(() => {
    return Array.isArray(consultas) ? consultas : [];
  }, [consultas]);

  // Filtrar consultas según búsqueda
  const filteredConsultas = React.useMemo(() => {
    return consultasArray.filter(consulta => {
      // Usar campos optimizados del serializer si están disponibles
      const pacienteNombre = consulta.paciente_nombre || consulta.historia_clinica?.paciente?.nombre || '';
      const pacienteApellido = consulta.paciente_apellido || consulta.historia_clinica?.paciente?.apellido || '';
      
      const pacienteMatch = !filterPaciente || 
        `${pacienteNombre} ${pacienteApellido}`
          .toLowerCase()
          .includes(filterPaciente.toLowerCase());
      
      const medicoMatch = !filterMedico || 
        `${consulta.medico?.apellido} ${consulta.medico?.nombre}`
          .toLowerCase()
          .includes(filterMedico.toLowerCase());
      
      return pacienteMatch && medicoMatch;
    });
  }, [consultasArray, filterPaciente, filterMedico]);

  const getPageTitle = () => {
    if (currentUser?.rol?.toUpperCase() === 'MEDICO') {
      return '📋 Mis Consultas';
    } else if (currentUser?.rol?.toUpperCase() === 'ADMIN') {
      return '📋 Todas las Consultas';
    } else {
      return '📋 Consultas del Sistema';
    }
  };

  // Verificar si el usuario tiene acceso a las consultas
  const hasAccess = () => {
    const rol = currentUser?.rol?.toUpperCase();
    return rol === 'MEDICO' || 
           rol === 'ADMIN' || 
           rol === 'SECRETARIA' ||
           currentUser?.is_superuser;
  };

  if (loading.consultas) {
    return (
      <div className="turnos-container">
        <div className="loading">🔄 Cargando consultas...</div>
      </div>
    );
  }

  // Si el usuario no tiene acceso, mostrar mensaje de acceso denegado
  if (!hasAccess()) {
    return (
      <div className="turnos-container">
        <div className="access-denied">
          <div className="access-denied-icon">🚫</div>
          <h1>Acceso Denegado</h1>
          <p>No tienes permisos para acceder a las consultas médicas.</p>
          <p>Solo los médicos y administradores pueden ver esta información.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="container">
        {/* Header */}
        <div className="turnos-header">
        <h1>{getPageTitle()}</h1>
      </div>

      {/* Search and Filters */}
      <SearchAndFilters
        searchTerm={filterPaciente}
        onSearchChange={setFilterPaciente}
        searchPlaceholder="Buscar por paciente..."
        filters={currentUser?.rol?.toUpperCase() !== 'MEDICO' ? {
          medico: {
            value: filterMedico,
            label: 'Médico',
            options: [], // Se puede expandir con lista de médicos si es necesario
            onChange: setFilterMedico,
          },
        } : {}}
        onRefresh={loadConsultas}
        totalItems={consultasArray.length}
        filteredItems={filteredConsultas.length}
      />



      {/* Lista de Consultas */}
      <div className="turnos-list">
        {filteredConsultas.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <h3>No hay consultas registradas</h3>
            <p>Las consultas aparecerán aquí cuando los médicos las creen desde el calendario</p>
          </div>
        ) : (
          filteredConsultas.map((consulta, index) => (
            <div 
              key={consulta.id} 
              className="turno-card"
              onClick={() => handleConsultaClick(consulta)}
            >
              <div className="turno-header">
                <div className="turno-time">
                  <span className="time">
                    {new Date(consulta.fecha_hora_consulta).toLocaleTimeString('es-ES', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                  <span className="date">
                    {new Date(consulta.fecha_hora_consulta).toLocaleDateString('es-ES', {
                      weekday: 'short',
                      day: 'numeric',
                      month: 'short'
                    })}
                  </span>
                </div>
                <div 
                  className="estado-badge"
                  style={{ backgroundColor: '#8B5CF6' }}
                >
                  CONSULTA
                </div>
              </div>
              
              <div className="turno-content">
                <div className="turno-info">
                  <div className="info-row">
                    <span className="label">👤 Paciente:</span>
                    <span className="value">
                      <span className="patient-name">{consulta.historia_clinica?.paciente?.apellido}, {consulta.historia_clinica?.paciente?.nombre}</span>
                    </span>
                  </div>
                  {currentUser?.rol?.toUpperCase() !== 'MEDICO' && (
                    <div className="info-row">
                      <span className="label">👨‍⚕️ Médico:</span>
                      <span className="value">
                        <span className="doctor-name">Dr. {consulta.medico?.apellido}, {consulta.medico?.nombre}</span>
                      </span>
                    </div>
                  )}
                  <div className="info-row">
                    <span className="label">📝 Motivo:</span>
                    <span className="value">
                      {consulta.motivo_consulta_detalle || 'Sin motivo especificado'}
                    </span>
                  </div>
                  {consulta.diagnostico_presuntivo && (
                    <div className="info-row">
                      <span className="label">🏥 Diagnóstico:</span>
                      <span className="value">
                        {typeof consulta.diagnostico_presuntivo === 'string'
                          ? (consulta.diagnostico_presuntivo.length > 100 
                              ? consulta.diagnostico_presuntivo.substring(0, 100) + '...' 
                              : consulta.diagnostico_presuntivo)
                          : String(consulta.diagnostico_presuntivo)}
                      </span>
                    </div>
                  )}
                  {consulta.plan_manejo && (
                    <div className="info-row">
                      <span className="label">💊 Plan:</span>
                      <span className="value">
                        {typeof consulta.plan_manejo === 'string'
                          ? (consulta.plan_manejo.length > 100 
                              ? consulta.plan_manejo.substring(0, 100) + '...' 
                              : consulta.plan_manejo)
                          : String(consulta.plan_manejo)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal de Detalle de Consulta */}
      {showConsultaModal && selectedConsulta && (
        <div className="modal-overlay" onClick={handleCloseModal}>
          <div className="modal consulta-detail-modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📋 Detalle de Consulta</h2>
              <button className="modal-close" onClick={handleCloseModal}>✕</button>
            </div>
            
            <div className="consulta-detail-content">
              <div className="consulta-info-section">
                <h3>Información del Paciente</h3>
                <div className="info-grid">
                  <div className="info-item">
                    <span className="label">👤 Paciente:</span>
                    <span className="value">
                      {selectedConsulta.paciente_apellido || selectedConsulta.historia_clinica?.paciente?.apellido}, {selectedConsulta.paciente_nombre || selectedConsulta.historia_clinica?.paciente?.nombre}
                    </span>
                  </div>
                  {currentUser?.rol?.toUpperCase() !== 'MEDICO' && (
                    <div className="info-item">
                      <span className="label">👨‍⚕️ Médico:</span>
                      <span className="value">
                        Dr. {selectedConsulta.medico?.apellido}, {selectedConsulta.medico?.nombre}
                      </span>
                    </div>
                  )}
                  <div className="info-item">
                    <span className="label">📅 Fecha:</span>
                    <span className="value">
                      {new Date(selectedConsulta.fecha_hora_consulta).toLocaleDateString('es-ES', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric'
                      })}
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="label">🕐 Hora:</span>
                    <span className="value">
                      {new Date(selectedConsulta.fecha_hora_consulta).toLocaleTimeString('es-ES', {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>
                  <div className="info-item">
                    <span className="label">📝 Motivo:</span>
                    <span className="value">{selectedConsulta.motivo_consulta_detalle}</span>
                  </div>
                </div>
              </div>

              <div className="consulta-content-section">
                <div className="content-item">
                  <h4>📝 Anamnesis (Interrogatorio)</h4>
                  <div className="content-text">
                    {selectedConsulta.anamnesis || 'No especificado'}
                  </div>
                </div>

                <div className="content-item">
                  <h4>🔍 Examen Físico</h4>
                  <div className="content-text">
                    {selectedConsulta.examen_fisico || 'No especificado'}
                  </div>
                </div>

                <div className="content-item">
                  <h4>🏥 Diagnóstico Presuntivo</h4>
                  <div className="content-text">
                    {selectedConsulta.diagnostico_presuntivo || 'No especificado'}
                  </div>
                </div>

                <div className="content-item">
                  <h4>💊 Plan de Manejo / Conducta</h4>
                  <div className="content-text">
                    {selectedConsulta.plan_manejo || 'No especificado'}
                  </div>
                </div>

                {selectedConsulta.notas_medicas && (
                  <div className="content-item">
                    <h4>📋 Notas Médicas Adicionales</h4>
                    <div className="content-text">
                      {selectedConsulta.notas_medicas}
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            <div className="modal-actions">
              <button className="btn-secondary" onClick={handleCloseModal}>
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
};

export default Consultas;
