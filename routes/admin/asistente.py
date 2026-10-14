# routes/admin/asistente.py
from flask import Blueprint, jsonify, render_template, request, session

from asistente.agentes import LIMITE_USUARIO_DIA, MAX_PREGUNTA, responder

asistente_bp = Blueprint('asistente', __name__, url_prefix='/admin/asistente')


@asistente_bp.route('/')
def index():
    return render_template('admin/asistente.html', max_pregunta=MAX_PREGUNTA, limite=LIMITE_USUARIO_DIA)


@asistente_bp.route('/preguntar', methods=['POST'])
def preguntar():
    datos = request.get_json(silent=True) or {}
    r = responder(datos.get('pregunta', ''), session.get('user_id'))
    return jsonify(r), (400 if 'error' in r else 200)