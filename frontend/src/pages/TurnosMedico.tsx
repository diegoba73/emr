import React, { useState, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Turno } from '../types';
import { apiService } from '../services/api';
import { useData } from '../contexts/DataContext';
import AtencionDetailDrawer from '../modules/atenciones/components/AtencionDetailDrawer';
import './TurnosMedico.css';

/** Pantalla legacy: no está enrutada en App.tsx (agenda médica usa /turnos + TurnoModal). */

const TurnosMedico: React.FC = () => {
  const { turnos, loading: dataLoading, currentUser, setTurnos, refreshAll, refreshTurnos } = useData();
  const queryClient = useQueryClient();
  
  // Función para recargar turnos cuando se guarda una intervención
  const handleIntervencionSaved = useCallback(async () => {
    // Recargar turnos para actualizar la información de atención
    await refreshTurnos();
  }, [refreshTurnos]);

  const [filterEstado, setFilterEstado] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [selectedAtencionId, setSelectedAtencionId] = useState<number | null>(null);

  // Filtrar solo los turnos del médico logueado
  const misTurnos = turnos.filter(turno => 
    turno.medico?.id === currentUser?.medico?.id
  );

  const filteredTurnos = misTurnos.filter(turno => 
    !filterEstado || turno.estado === filterEstado
  );

  const handleConfirmarTurno = async (turno: Turno) => {
    if (!window.confirm('¿Confirmar este turno?')) return;
    
    setLoading(true);
    try {
      await apiService.confirmarTurno(turno.id);
      
      // Actualizar estado local
      setTurnos(prevTurnos => 
        prevTurnos.map(t => 
          t.id === turno.id ? { ...t, estado: 'CONFIRMADO' } : t
        )
      );
      
      alert('Turno confirmado exitosamente');
    } catch (error: any) {
      console.error('Error confirmando turno:', error);
      alert(`Error: ${error.response?.data?.error || error.message}`);
    } finally {
      setLoading(false);
    }
  };





  const getEstadoColor = (estado: string) => {
    const colors = {
      'RESERVADO': '#F59E0B',
      'CONFIRMADO': '#3B82F6',
      'REALIZADO': '#8B5CF6',
      'CANCELADO': '#EF4444',
    };
    return colors[estado as keyof typeof colors] || '#6B7280';
  };

  const canConfirmar = (turno: Turno) => {
    return turno.estado === 'RESERVADO';
  };

  // Función helper para verificar si un turno tiene un registro de intervención
  const tieneRegistroIntervencion = (turno: Turno): boolean => {
    const tipoRecurso = turno.recurso?.tipo_recurso;
    const atencion = turno.atencion;
    
    if (!atencion) return false;
    
    // Verificar si existe el registro (puede venir como objeto completo o como { id: number })
    const hasConsulta = atencion.consulta_ambulatoria && (
      (typeof atencion.consulta_ambulatoria === 'object' && 'id' in atencion.consulta_ambulatoria && atencion.consulta_ambulatoria.id) ||
      (atencion.consulta_ambulatoria as any)?.id
    );
    
    const hasProcedimiento = atencion.registro_procedimiento && (
      (typeof atencion.registro_procedimiento === 'object' && 'id' in atencion.registro_procedimiento && atencion.registro_procedimiento.id) ||
      (atencion.registro_procedimiento as any)?.id
    );
    
    const hasQuirurgico = atencion.registro_quirurgico && (
      (typeof atencion.registro_quirurgico === 'object' && 'id' in atencion.registro_quirurgico && atencion.registro_quirurgico.id) ||
      (atencion.registro_quirurgico as any)?.id
    );
    
    switch (tipoRecurso) {
      case 'CONSULTORIO':
        return Boolean(hasConsulta);
      case 'SALA_PROCEDIMIENTO':
      case 'SALA_HEMODINAMIA':
        return Boolean(hasProcedimiento);
      case 'QUIROFANO':
        return Boolean(hasQuirurgico);
      default:
        return false;
    }
  };

  // Función helper para obtener el texto del botón según el tipo de recurso y si existe registro
  const getButtonText = (turno: Turno) => {
    const tipoRecurso = turno.recurso?.tipo_recurso;
    const tieneRegistro = tieneRegistroIntervencion(turno);
    
    // Si ya existe un registro, mostrar "Ver/Editar"
    if (tieneRegistro || turno.estado === 'REALIZADO') {
      switch (tipoRecurso) {
        case 'CONSULTORIO':
          return '📋 Ver/Editar Consulta';
        case 'SALA_PROCEDIMIENTO':
          return '📊 Ver/Editar Estudio';
        case 'SALA_HEMODINAMIA':
          return '🔬 Ver/Editar Procedimiento';
        case 'QUIROFANO':
          return '⚕️ Ver/Editar Cirugía';
        default:
          return '📋 Ver/Editar Registro';
      }
    } else {
      // Si no existe registro, mostrar "Crear"
      switch (tipoRecurso) {
        case 'CONSULTORIO':
          return '📋 Crear Consulta';
        case 'SALA_PROCEDIMIENTO':
          return '📊 Crear Estudio';
        case 'SALA_HEMODINAMIA':
          return '🔬 Crear Procedimiento';
        case 'QUIROFANO':
          return '⚕️ Crear Cirugía';
        default:
          return '📋 Crear Registro';
      }
    }
  };

  // Función para abrir la atención desde un turno
  const handleOpenAtencion = async (turno: Turno) => {
    try {
      // Validaciones básicas
      if (!turno.paciente || !turno.medico || !turno.recurso) {
        alert('El turno debe tener paciente, médico y recurso asignados para crear un registro clínico.');
        return;
      }

      // Si el turno ya tiene una atención, abrirla directamente
      if (turno.atencion?.id) {
        setSelectedAtencionId(turno.atencion.id);
        return;
      }

      // Si el turno está CONFIRMADO o REALIZADO pero no tiene atención, crear una
      if (turno.estado === 'CONFIRMADO' || turno.estado === 'REALIZADO') {
        try {
          // Primero buscar si ya existe una atención para este turno
          const atenciones = await apiService.getAtenciones({ turno: turno.id });
          const atencionExistente = atenciones.results?.[0];
          
          if (atencionExistente) {
            setSelectedAtencionId(atencionExistente.id);
            return;
          }
          
          const result = await apiService.iniciarAtencionTurno(turno.id);
          const atencion = result.atencion;

          queryClient.setQueryData(['atencion', atencion.id], atencion);
          queryClient.invalidateQueries({ queryKey: ['atenciones'] });
          queryClient.invalidateQueries({ queryKey: ['turnos'] });

          setSelectedAtencionId(atencion.id);
          
          // Refrescar datos globales en background (sin await para evitar race conditions)
          refreshAll().catch((err: any) => {
            console.warn('Error en refreshAll:', err);
          });
        } catch (error: any) {
          console.error('Error obteniendo/creando atención:', error);
          const errorMessage = error.message || 'Error al crear la atención. Verifica que el turno esté confirmado o realizado.';
          alert(errorMessage);
        }
      } else {
        alert('El turno debe estar CONFIRMADO o REALIZADO para crear un registro clínico.');
      }
    } catch (error: any) {
      console.error('Error abriendo atención:', error);
      alert(error.message || 'Error al abrir la atención. Por favor, intenta nuevamente.');
    }
  };



  if (dataLoading.turnos) {
    return (
      <div className="turnos-medico-container">
        <div className="loading">🔄 Cargando mis turnos...</div>
      </div>
    );
  }

  return (
    <div className="dashboard fade-in">
      <div className="container">
        {/* Header */}
        <div className="turnos-medico-header">
        <h1>👨‍⚕️ Mis Turnos</h1>
        <div className="turnos-medico-actions">
          <select 
            value={filterEstado} 
            onChange={(e) => setFilterEstado(e.target.value)}
            className="filter-select"
          >
            <option value="">Todos los estados</option>
            <option value="RESERVADO">Reservado</option>
            <option value="CONFIRMADO">Confirmado</option>
            <option value="REALIZADO">Realizado</option>
            <option value="CANCELADO">Cancelado</option>
          </select>
        </div>
      </div>

      {/* Estadísticas */}
      <div className="turnos-stats">
        <div className="stat-card">
          <div className="stat-number">{misTurnos.filter(t => t.estado === 'RESERVADO').length}</div>
          <div className="stat-label">Pendientes</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{misTurnos.filter(t => t.estado === 'CONFIRMADO').length}</div>
          <div className="stat-label">Confirmados</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{misTurnos.filter(t => t.estado === 'REALIZADO').length}</div>
          <div className="stat-label">Realizados</div>
        </div>
      </div>

      {/* Turnos List */}
      <div className="turnos-medico-list">
        {filteredTurnos.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📅</div>
            <h3>No tienes turnos programados</h3>
            <p>Los turnos aparecerán aquí cuando sean asignados</p>
          </div>
        ) : (
          filteredTurnos.map(turno => (
            <div key={turno.id} className="turno-medico-card">
              <div className="turno-medico-header">
                <div className="turno-medico-time">
                  <span className="time">
                    {new Date(turno.fecha_hora_inicio).toLocaleTimeString('es-ES', {
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                  <span className="date">
                    {new Date(turno.fecha_hora_inicio).toLocaleDateString('es-ES', {
                      weekday: 'short',
                      day: 'numeric',
                      month: 'short'
                    })}
                  </span>
                </div>
                <div 
                  className="estado-badge"
                  style={{ backgroundColor: getEstadoColor(turno.estado) }}
                >
                  {turno.estado}
                </div>
              </div>
              
              <div className="turno-medico-content">
                <div className="turno-medico-info">
                  <div className="info-row">
                    <span className="label">👤 Paciente:</span>
                    <span className="value">
                      {turno.paciente ? `${turno.paciente.nombre} ${turno.paciente.apellido}` : 'Sin paciente asignado'}
                    </span>
                  </div>
                  <div className="info-row">
                    <span className="label">🏥 Recurso:</span>
                    <span className="value">
                      {turno.recurso?.nombre || 'Sin especificar'}
                      {turno.recurso?.tipo_recurso_display && ` (${turno.recurso.tipo_recurso_display})`}
                    </span>
                  </div>
                  {turno.motivo_consulta && (
                    <div className="info-row">
                      <span className="label">📝 Motivo:</span>
                      <span className="value">{turno.motivo_consulta}</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="turno-medico-actions">
                {canConfirmar(turno) && (
                  <button 
                    onClick={() => handleConfirmarTurno(turno)}
                    className="btn-confirm"
                    disabled={loading}
                  >
                    ✅ Confirmar
                  </button>
                )}
                
                {(turno.estado === 'CONFIRMADO' || turno.estado === 'REALIZADO') && (
                  <button 
                    onClick={() => handleOpenAtencion(turno)}
                    className="btn-primary"
                    style={{ backgroundColor: '#3B82F6', marginLeft: '8px' }}
                    disabled={loading}
                  >
                    {getButtonText(turno)}
                  </button>
                )}
                
                {/* No mostrar botón Editar Turno si ya tiene registro de intervención */}
              </div>
            </div>
          ))
        )}
      </div>
      </div>

      {/* Drawer de Atención */}
      <AtencionDetailDrawer
        atencionId={selectedAtencionId}
        open={Boolean(selectedAtencionId)}
        onClose={async () => {
          setSelectedAtencionId(null);
          // Recargar turnos para actualizar la información de atención
          await refreshTurnos();
        }}
        currentUserRole={currentUser?.rol}
        onIntervencionSaved={handleIntervencionSaved}
      />
    </div>
  );
};

export default TurnosMedico;


