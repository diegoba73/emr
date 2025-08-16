
// Script para probar en la consola del navegador
console.log('🧪 Probando autenticación en el navegador...');

// 1. Hacer login
fetch('http://127.0.0.1:8000/api/auth/login/', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
        username: 'secretaria1',
        password: 'changeme123'
    })
})
.then(response => response.json())
.then(data => {
    console.log('✅ Login exitoso:', data);
    
    // 2. Verificar usuario actual
    return fetch('http://127.0.0.1:8000/api/auth/current-user/', {
        credentials: 'include'
    });
})
.then(response => response.json())
.then(user => {
    console.log('✅ Usuario actual:', user);
    
    // 3. Probar endpoints
    const endpoints = ['pacientes', 'turnos', 'medicos', 'especialidades'];
    
    endpoints.forEach(endpoint => {
        fetch(`http://127.0.0.1:8000/api/${endpoint}/`, {
            credentials: 'include'
        })
        .then(response => response.json())
        .then(data => {
            console.log(`✅ ${endpoint}:`, data.results?.length || 0, 'registros');
        })
        .catch(error => {
            console.error(`❌ ${endpoint}:`, error);
        });
    });
})
.catch(error => {
    console.error('❌ Error:', error);
});
