import requests
import json

LIMS_API_BASE_URL = "http://localhost:8001/api/laboratorio/"

def enviar_solicitud_a_lims(solicitud_data):
    """Envía una solicitud de examen al LIMS."""
    try:
        # Usar endpoint de ingesta que acepta payload mínimo desde EMR
        url = f"{LIMS_API_BASE_URL}solicitudes/ingesta/"
        headers = {
            "Content-Type": "application/json"
        }
        response = requests.post(url, headers=headers, data=json.dumps(solicitud_data))
        response.raise_for_status() # Lanza un error si la respuesta no es 2xx
        return response.json()
    except requests.exceptions.RequestException as e:
        # Manejo de errores de conexión o de la API
        print(f"Error al enviar la solicitud al LIMS: {e}")
        return None