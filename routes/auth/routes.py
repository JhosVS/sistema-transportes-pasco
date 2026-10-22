# routes/auth/routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, Usuario

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

        usuario = Usuario.query.filter_by(email=email).first()

        # Validación 1: Verificar existencia
        if not usuario:
            flash('Las credenciales ingresadas son incorrectas.', 'danger')
            return render_template('auth/login.html')

        # Validación 2: Verificar si está activo
        if usuario.estado != 'Activo':
            flash('Su cuenta se encuentra inactiva. Contacte al administrador.', 'danger')
            return render_template('auth/login.html')

        # Validación 3: Verificar contraseña usando el modelo actualizado
        if usuario.check_password(password):
            # Si el hash era Bcrypt o texto plano, se migra al formato nativo de Werkzeug
            if not usuario.password_hash.startswith(('pbkdf2:', 'scrypt:')):
                usuario.set_password(password)
                db.session.commit()

            session['user_id'] = usuario.id_usuario
            session['user_nombre'] = usuario.nombres
            session['user_rol'] = usuario.rol.codigo
            session['user_email'] = usuario.email
            session['id_sede'] = usuario.id_sede
            session['nombre_sede'] = usuario.sede.nombre_sede if usuario.sede else 'Sin Sede'

            flash(f'¡Bienvenido(a), {usuario.nombres}!', 'success')
            return redirect(url_for('sedes.index'))
        else:
            flash('Las credenciales ingresadas son incorrectas.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))