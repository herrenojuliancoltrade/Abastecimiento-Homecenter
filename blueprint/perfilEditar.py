import json
import os
from flask import Blueprint, jsonify, render_template, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.security import check_password_hash, generate_password_hash

perfilEditar_bp = Blueprint(
    'perfilEditar',
    __name__,
    url_prefix='/perfilEditar',
    template_folder='../templates'
)


def _login_json_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, '..'))
    return os.path.join(project_root, 'conexiones', 'login.json')


def _load_users():
    path = _login_json_path()
    with open(path, 'r', encoding='utf-8') as f:
        users = json.load(f)
    if not isinstance(users, list):
        raise ValueError("login.json debe contener una lista de usuarios.")
    return users


def _save_users(users):
    path = _login_json_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _find_user_by_identity(users, identity):
    for user in users:
        if (user.get('username') == identity) or (user.get('email') == identity):
            return user
    return None


def _verify_password(user, password):
    if user.get('password_hash'):
        try:
            return check_password_hash(user.get('password_hash'), password)
        except Exception:
            return False
    if user.get('password'):
        return user.get('password') == password
    return False


@perfilEditar_bp.route('/')
def perfil_home_view():
    return render_template('perfilEditar.html')


@perfilEditar_bp.route('/informacion')
def perfil_informacion_view():
    return render_template('perfilPersonal.html')


@perfilEditar_bp.route('/crear-usuario')
def crear_usuario_view():
    return render_template('crearUsuario.html')


@perfilEditar_bp.route('/estilo')
def estilo_view():
    return render_template('perfilEstilo.html')


def _current_user_from_token():
    identity = get_jwt_identity()
    users = _load_users()
    user = _find_user_by_identity(users, identity)
    return users, user


@perfilEditar_bp.route('/api/data', methods=['GET'])
@jwt_required()
def perfil_data():
    try:
        _, user = _current_user_from_token()
        if not user:
            return jsonify({"error": "Usuario no encontrado en login.json"}), 404

        first_name = (user.get('name') or '').strip()
        last_name = (user.get('last_name') or '').strip()
        if not last_name and first_name:
            parts = first_name.split()
            if len(parts) > 1:
                first_name = parts[0]
                last_name = " ".join(parts[1:])

        return jsonify({
            "user": {
                "email": user.get('email', ''),
                "username": user.get('username', ''),
                "name": first_name,
                "last_name": last_name,
                "rol": user.get('rol', ''),
                "theme": user.get('theme', 'light')
            }
        }), 200
    except Exception as err:
        return jsonify({"error": f"No se pudo cargar el perfil. Detalle: {err}"}), 500


@perfilEditar_bp.route('/api/update-profile', methods=['POST'])
@jwt_required()
def update_profile():
    data = request.get_json() or {}
    name = str(data.get('name', '')).strip()
    last_name = str(data.get('last_name', '')).strip()

    if not name:
        return jsonify({"error": "El nombre es obligatorio."}), 400
    if not last_name:
        return jsonify({"error": "El apellido es obligatorio."}), 400

    try:
        users, user = _current_user_from_token()
        if not user:
            return jsonify({"error": "Usuario no encontrado en login.json"}), 404

        user['name'] = name
        user['last_name'] = last_name
        _save_users(users)
        return jsonify({"msg": "Perfil actualizado correctamente."}), 200
    except Exception as err:
        return jsonify({"error": f"No se pudo actualizar el perfil. Detalle: {err}"}), 500


@perfilEditar_bp.route('/api/change-password', methods=['POST'])
@jwt_required()
def change_password():
    data = request.get_json() or {}
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not current_password or not new_password or not confirm_password:
        return jsonify({"error": "Completa todos los campos de contrasena."}), 400
    if new_password != confirm_password:
        return jsonify({"error": "La nueva contrasena y su confirmacion no coinciden."}), 400
    if len(new_password) < 6:
        return jsonify({"error": "La nueva contrasena debe tener al menos 6 caracteres."}), 400

    try:
        users, user = _current_user_from_token()
        if not user:
            return jsonify({"error": "Usuario no encontrado en login.json"}), 404

        if not _verify_password(user, current_password):
            return jsonify({"error": "La contrasena actual es incorrecta."}), 401

        user['password_hash'] = generate_password_hash(new_password)
        user.pop('password', None)
        _save_users(users)
        return jsonify({"msg": "Contrasena actualizada correctamente."}), 200
    except Exception as err:
        return jsonify({"error": f"No se pudo cambiar la contrasena. Detalle: {err}"}), 500


@perfilEditar_bp.route('/api/create-user', methods=['POST'])
@jwt_required()
def create_user():
    data = request.get_json() or {}
    email = str(data.get('email', '')).strip().lower()
    username = str(data.get('username', '')).strip()
    name = str(data.get('name', '')).strip()
    last_name = str(data.get('last_name', '')).strip()
    password = data.get('password', '')
    rol = str(data.get('rol', '')).strip().lower()

    allowed_roles = {'administrador', 'usuario'}
    if rol not in allowed_roles:
        return jsonify({"error": "Rol invalido. Solo permitido: administrador o usuario."}), 400
    if not email or not username or not name or not last_name or not password:
        return jsonify({"error": "Completa todos los campos obligatorios."}), 400
    if len(password) < 6:
        return jsonify({"error": "La contrasena debe tener al menos 6 caracteres."}), 400

    try:
        users, current_user = _current_user_from_token()
        if not current_user:
            return jsonify({"error": "Usuario actual no encontrado."}), 404
        if str(current_user.get('rol', '')).strip().lower() != 'administrador':
            return jsonify({"error": "Solo administradores pueden crear usuarios."}), 403

        for user in users:
            if str(user.get('email', '')).strip().lower() == email:
                return jsonify({"error": "Ya existe un usuario con ese correo."}), 400
            if str(user.get('username', '')).strip().lower() == username.lower():
                return jsonify({"error": "Ya existe un usuario con ese username."}), 400

        new_user = {
            "email": email,
            "username": username,
            "name": name,
            "last_name": last_name,
            "id_rol": "1" if rol == "administrador" else "2",
            "rol": rol,
            "id_area": "",
            "area": "",
            "theme": "light",
            "password_hash": generate_password_hash(password)
        }
        users.append(new_user)
        _save_users(users)
        return jsonify({"msg": "Usuario creado correctamente."}), 201
    except Exception as err:
        return jsonify({"error": f"No se pudo crear el usuario. Detalle: {err}"}), 500


@perfilEditar_bp.route('/api/update-theme', methods=['POST'])
@jwt_required()
def update_theme():
    data = request.get_json() or {}
    theme = str(data.get('theme', '')).strip().lower()
    if theme not in {'light', 'dark'}:
        return jsonify({"error": "Tema invalido. Usa light o dark."}), 400

    try:
        users, user = _current_user_from_token()
        if not user:
            return jsonify({"error": "Usuario no encontrado en login.json"}), 404
        user['theme'] = theme
        _save_users(users)
        return jsonify({"msg": "Tema actualizado correctamente.", "theme": theme}), 200
    except Exception as err:
        return jsonify({"error": f"No se pudo actualizar el tema. Detalle: {err}"}), 500
