const axios = require('axios');

// Probar la actualización de turnos después de arreglar el problema
async function testFixedUpdate() {
  try {
    console.log('=== PROBANDO ACTUALIZACIÓN ARREGLADA ===');
    
    // Obtener el turno 3 (que tenía estado PENDIENTE)
    const turnoResponse = await axios.get('http://localhost:8001/api/turnos/3/');
    const turno = turnoResponse.data;
    
    console.log('Turno actual:', {
      id: turno.id,
      estado: turno.estado,
      motivo_consulta: turno.motivo_consulta,
      fecha_hora_inicio: turno.fecha_hora_inicio
    });
    
    // Simular actualización desde el frontend
    const formData = {
      paciente: '1',
      medico: '1', 
      especialidad: '1',
      fecha_hora: '2025-08-07T20:00',  // Formato del input datetime-local
      motivo_consulta: 'Ansiedad - Actualizado desde frontend',
      estado: 'CONFIRMADO'
    };
    
    console.log('Form Data del frontend:', formData);
    
    // Procesar fecha como lo hace el frontend
    let fechaHoraInicio = formData.fecha_hora;
    
    if (formData.fecha_hora) {
      try {
        const fecha = new Date(formData.fecha_hora);
        fechaHoraInicio = fecha.toISOString();
        console.log('Fecha procesada:', fechaHoraInicio);
      } catch (error) {
        console.error('Error formateando fecha:', error);
        fechaHoraInicio = turno.fecha_hora_inicio;
      }
    }
    
    // Validar que tengamos una fecha válida
    if (!fechaHoraInicio) {
      console.error('La fecha y hora de inicio es requerida');
      return;
    }
    
    const turnoData = {
      fecha_hora_inicio: fechaHoraInicio,
      motivo_consulta: formData.motivo_consulta || '',
      estado: formData.estado
    };
    
    // Solo agregar campos si tienen valores válidos
    if (formData.paciente) {
      turnoData.paciente = parseInt(formData.paciente);
    }
    if (formData.medico) {
      turnoData.medico = parseInt(formData.medico);
    }
    if (formData.especialidad) {
      turnoData.especialidad = parseInt(formData.especialidad);
    }
    
    console.log('Turno Data a enviar:', turnoData);
    
    // Intentar actualizar
    const updateResponse = await axios.put('http://localhost:8001/api/turnos/3/', turnoData, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    console.log('✅ Actualización exitosa!');
    console.log('Turno actualizado:', {
      id: updateResponse.data.id,
      estado: updateResponse.data.estado,
      motivo_consulta: updateResponse.data.motivo_consulta,
      fecha_hora_inicio: updateResponse.data.fecha_hora_inicio
    });
    
  } catch (error) {
    console.error('❌ Error en la actualización:');
    console.error('Error:', error.message);
    console.error('Response data:', error.response?.data);
    console.error('Response status:', error.response?.status);
  }
}

testFixedUpdate();
