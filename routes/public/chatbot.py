# asistente/chatbot.py
from flask import Blueprint, jsonify, request

from asistente.publico import responder

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/chat')


@chatbot_bp.route('/preguntar', methods=['POST'])
def preguntar():
    ip = (request.headers.get('X-Forwarded-For', request.remote_addr) or '').split(',')[0].strip()
    datos = request.get_json(silent=True) or {}
    r = responder(datos.get('pregunta', ''), ip)
    return jsonify(r), (400 if 'error' in r else 200)