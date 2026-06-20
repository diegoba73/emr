import React, { useState, useEffect } from 'react';
import { Turno, Consulta } from '../types';
import { apiService } from '../services/api';
import { useData } from '../contexts/DataContext';
import './MisConsultas.css';

const MisConsultas: React.FC = () => {
  const { currentUser } = useData();
  const [consultas, setConsultas] = useState<Consulta[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedConsulta, setSelectedConsulta] = useState<Consulta | null>(null);
  const [showConsultaModal, setShowConsultaModal] = useState(false);
  const [filterPaciente, setFilterPaciente] = useState<string>('');
  const [filterFecha, setFilterFecha] = useState<string>('');
  
  const isMedico = currentUser?.rol?.toUpperCase() === 'MEDICO';
  const isPaciente = currentUser?.rol?.toUpperCase() === 'PACIENTE';

  useEffect(() => {
    loadConsultas();
  }, []);

  const loadConsultas = async () => {
    try {
      setLoading(true);
      // El backend ya filtra por rol (médico solo ve sus consultas, paciente solo las suyas)
      // y ordena por fecha descendente
      const response = await apiService.getConsultas();
      
      // El backend ya devuelve las consultas filtradas y ordenadas
      setConsultas(response.results || []);
    } catch (error) {
      console.error('Error cargando consultas:', error);
      setConsultas([]);
    } finally {
      setLoading(false);
    }
  };

  const handleConsultaClick = (consulta: Consulta) => {
    setSelectedConsulta(consulta);
    setShowConsultaModal(true);
  };

  const handleCloseModal = () => {
    setShowConsultaModal(false);
    setSelectedConsulta(null);
  };

  const filteredConsultas = consultas.filter(consulta => {
    // Filtro por nombre de paciente (solo para médicos, pacientes no necesitan filtrar)
    if (isMedico && filterPaciente) {
      const pacienteNombre = consulta.paciente_nombre || consulta.historia_clinica?.paciente?.nombre || '';
      const pacienteApellido = consulta.paciente_apellido || consulta.historia_clinica?.paciente?.apellido || '';
      const nombreCompleto = `${pacienteNombre} ${pacienteApellido}`.toLowerCase();
      if (!nombreCompleto.includes(filterPaciente.toLowerCase())) {
        return false;
      }
    }
    
    // Filtro por fecha (solo para médicos)
    if (isMedico && filterFecha) {
      const consultaFecha = new Date(consulta.fecha_hora_consulta).toISOString().split('T')[0];
      if (consultaFecha !== filterFecha) {
        return false;
      }
    }
    
    return true;
  });

  if (loading) {
    return (
      <div className="mis-consultas-container">
        <div className="loading">🔄 Cargando mis consultas...</div>
      </div>
    );
  }

  return (
    <div className="dashboard fade-in">
      <div className="container">
        {/* Header */}
        <div className="mis-consultas-header">
        <h1>📋 Mis Consultas</h1>
        <div className="mis-consultas-actions">
          {isMedico && (
            <>
              <input
                type="text"
                placeholder="🔍 Buscar por paciente..."
                value={filterPaciente}
                onChange={(e) => setFilterPaciente(e.target.value)}
                className="search-input"
              />
              <input
                type="date"
                value={filterFecha}
                onChange={(e) => setFilterFecha(e.target.value)}
                className="search-input"
                style={{ width: '180px' }}
              />
            </>
          )}
          <button 
            onClick={loadConsultas}
            className="refresh-button"
          >
            🔄 Actualizar
          </button>
        </div>
      </div>

      {/* Estadísticas */}
      <div className="consultas-stats">
        <div className="stat-card">
          <div className="stat-number">{consultas.length}</div>
          <div className="stat-label">Total Consultas</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">
            {consultas.filter(c => new Date(c.fecha_hora_consulta).toDateString() === new Date().toDateString()).length}
          </div>
          <div className="stat-label">Consultas Hoy</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">
            {consultas.filter(c => new Date(c.fecha_hora_consulta) >= new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)).length}
          </div>
          <div className="stat-label">Esta Semana</div>
        </div>
      </div>

      {/* Lista de Consultas */}
      <div className="consultas-list">
        {filteredConsultas.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📋</div>
            <h3>No tienes consultas registradas</h3>
            <p>Las consultas aparecerán aquí cuando las crees desde el calendario</p>
          </div>
        ) : (
          filteredConsultas.map(consulta => (
            <div 
              key={consulta.id} 
              className="consulta-card"
              onClick={() => handleConsultaClick(consulta)}
            >
              <div className="consulta-header">
                <div className="consulta-paciente">
                  <span className="patient-icon">👤</span>
                  <span className="patient-name">
                    {consulta.paciente_apellido || consulta.historia_clinica?.paciente?.apellido}, {consulta.paciente_nombre || consulta.historia_clinica?.paciente?.nombre}
                  </span>
                </div>
                <div className="consulta-date">
                  {new Date(consulta.fecha_hora_consulta).toLocaleDateString('es-ES', {
                    weekday: 'short',
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                  })}
                </div>
              </div>
              
              <div className="consulta-details">
                <div className="consulta-time">
                  🕐 {new Date(consulta.fecha_hora_consulta).toLocaleTimeString('es-ES', {
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </div>
                <div className="consulta-motivo">
                  📝 {consulta.motivo_consulta_detalle || 'Sin motivo especificado'}
                </div>
              </div>
              
              <div className="consulta-preview">
                {consulta.diagnostico_presuntivo && (
                  <div className="diagnostico-preview">
                    <strong>🏥 Diagnóstico:</strong> {
                      typeof consulta.diagnostico_presuntivo === 'string'
                        ? (consulta.diagnostico_presuntivo.length > 100 
                            ? consulta.diagnostico_presuntivo.substring(0, 100) + '...' 
                            : consulta.diagnostico_presuntivo)
                        : String(consulta.diagnostico_presuntivo)
                    }
                  </div>
                )}
                {consulta.plan_manejo && (
                  <div className="plan-preview">
                    <strong>💊 Plan:</strong> {
                      typeof consulta.plan_manejo === 'string'
                        ? (consulta.plan_manejo.length > 100 
                            ? consulta.plan_manejo.substring(0, 100) + '...' 
                            : consulta.plan_manejo)
                        : String(consulta.plan_manejo)
                    }
                  </div>
                )}
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

export default MisConsultas;
