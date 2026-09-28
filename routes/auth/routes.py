from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import UsuarioModel

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Por favor completa todos los campos.', 'warning')
            return render_template('auth/login.html')

        usuario = UsuarioModel.get_by_email(email)

        # Validación 1: Verificar existencia
        if not usuario:
            flash('Las credenciales ingresadas son incorrectas.', 'danger')
            return render_template('auth/login.html')

        # Validación 2: Verificar si está activo
        if usuario['estado'] != 'Activo':
            flash('Su cuenta se encuentra inactiva. Contacte al administrador.', 'danger')
            return render_template('auth/login.html')

        # Validación 3: Contraseña
        if UsuarioModel.verificar_password(usuario['password'], password):
            session['user_id'] = usuario['id_usuario']
            session['user_nombre'] = usuario['nombre']
            session['user_email'] = usuario['email']
            session['id_sede'] = usuario['id_sede']
            session['nombre_sede'] = usuario.get('nombre_sede', 'Sin Sede')

            # Si la contraseña estaba en texto plano, la actualizamos a un hash seguro
            if not usuario['password'].startswith(('pbkdf2:', 'scrypt:')):
                UsuarioModel.actualizar_password_hash(usuario['id_usuario'], password)

            flash(f'¡Bienvenido(a), {usuario["nombre"]}!', 'success')
            return redirect(url_for('sedes.index'))
        else:
            flash('Las credenciales ingresadas son incorrectas.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))