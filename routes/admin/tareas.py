# routes/admin/tareas.py
import hmac
import os

from flask import Blueprint, abort, jsonify, render_template, request

from asistente import orquestador as o
from asistente.registro import TAREAS, TODOS

tareas_bp = Blueprint('tareas', __name__)


@tareas_bp.route('/admin/tareas')
def index():
    return render_template('admin/tareas.html', agentes=TODOS, con_tarea={a.clave for a in TAREAS},
                           registro=o.ultimos())


@tareas_bp.route('/admin/tareas/ejecutar/<clave>', methods=['POST'])
def ejecutar(clave):
    if clave not in {a.clave for a in TAREAS}:
        abort(404)
    return jsonify(o.ejecutar_tarea(clave))


@tareas_bp.route('/tareas/cron/<grupo>')
def cron(grupo):
    esperado = os.getenv('TAREAS_TOKEN', '')
    if not esperado or not hmac.compare_digest(request.args.get('token', ''), esperado):
        abort(403)
    if grupo not in ('frecuente', 'diaria'):
        abort(404)
    return jsonify(o.ejecutar_grupo(grupo))