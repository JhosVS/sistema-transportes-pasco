# routes/admin/tareas.py
import hmac
import os

from flask import Blueprint, abort, jsonify, render_template, request

from asistente import orquestador as o
from asistente.registro import TODOS

tareas_bp = Blueprint('tareas', __name__)
TAREAS = {'sincronizar': o.sincronizar, 'rutina': o.rutina_diaria}


@tareas_bp.route('/admin/tareas')
def index():
    return render_template('admin/tareas.html', agentes=TODOS, registro=o.ultimos())


@tareas_bp.route('/admin/tareas/ejecutar/<tarea>', methods=['POST'])
def ejecutar(tarea):
    if tarea not in TAREAS:
        abort(404)
    return jsonify(TAREAS[tarea]())


@tareas_bp.route('/tareas/cron/<grupo>')
def cron(grupo):
    esperado = os.getenv('TAREAS_TOKEN', '')
    if not esperado or not hmac.compare_digest(request.args.get('token', ''), esperado):
        abort(403)
    tarea = {'frecuente': 'sincronizar', 'diaria': 'rutina'}.get(grupo)
    if not tarea:
        abort(404)
    return jsonify(TAREAS[tarea]())