# routes/utils/reniec.py
import os
import requests

def obtener_datos_dni(dni):
    if len(dni) != 8 or not dni.isdigit():
        return {'success': False, 'message': 'El DNI debe tener 8 dígitos numéricos'}

    token = os.getenv('APISPERU_TOKEN', '')
    url = f"https://dniruc.apisperu.com/api/v1/dni/{dni}?token={token}"

    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success', True):
                nombres_completos = f"{data.get('nombres', '')} {data.get('apellidoPaterno', '')} {data.get('apellidoMaterno', '')}".strip()
                return {
                    'success': True,
                    'dni': data.get('dni', dni),
                    'nombres': data.get('nombres', ''),
                    'apellidoPaterno': data.get('apellidoPaterno', ''),
                    'apellidoMaterno': data.get('apellidoMaterno', ''),
                    'nombres_completos': nombres_completos
                }
        return {'success': False, 'message': 'DNI no encontrado en RENIEC'}
    except Exception as e:
        return {'success': False, 'message': f'Error de conexión: {str(e)}'}