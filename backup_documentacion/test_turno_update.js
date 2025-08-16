const axios = require('axios');

// Simular la actualización de un turno como lo haría el frontend
async function testTurnoUpdate() {
  try {
    // Primero obtener el turno actual
    const turnoResponse = await axios.get('http://localhost:8001/api/turnos/2/');
    const turno = turnoResponse.data;
    
    console.log('Turno actual:', turno);
    
    // Simular los datos que enviaría el frontend
    const turnoData = {
      fecha_hora_inicio: "2025-08-07T16:00:00-03:00",
      motivo_consulta: "Pecho - Actualizado desde test",
      estado: "CONFIRMADO",
      paciente: 2,
      medico: 1,
      especialidad: 1
    };
    
    console.log('Datos a enviar:', turnoData);
    console.log('JSON a enviar:', JSON.stringify(turnoData, null, 2));
    
    // Intentar actualizar
    const updateResponse = await axios.put('http://localhost:8001/api/turnos/2/', turnoData, {
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    console.log('Respuesta exitosa:', updateResponse.data);
    
  } catch (error) {
    console.error('Error:', error.response?.data || error.message);
    console.error('Status:', error.response?.status);
  }
}

testTurnoUpdate();
