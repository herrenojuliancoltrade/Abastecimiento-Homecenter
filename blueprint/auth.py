# blueprint/auth.py
import os
import json
import smtplib
import random
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies, jwt_required, get_jwt_identity, get_jwt
)
from werkzeug.security import check_password_hash, generate_password_hash


auth_bp = Blueprint('auth', __name__, url_prefix='/api')

# Blocklist en memoria (para logout)
_blocklist = set()

# Codigos de recuperacion en memoria: {email: {code: '123456', expires_at: datetime_utc}}
_password_reset_codes = {}


def _login_json_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(base_dir, '..'))
    return os.path.join(project_root, 'conexiones', 'login.json')


def _load_users():
    path = _login_json_path()

    try:
        with open(path, 'r', encoding='utf-8') as f:
            users = json.load(f)
        return users
    except FileNotFoundError:
        current_app.logger.error(f"login.json no encontrado en {path}")
        return []
    except Exception as e:
        current_app.logger.error(f"Error leyendo login.json: {e}")
        return []


def _save_users(users):
    path = _login_json_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def _find_user(users, user_input):
    value = (user_input or '').strip()
    if not value:
        return None

    return next(
        (u for u in users if (u.get('email') == value)
         or (u.get('username') and u.get('username').lower() == value.lower())),
        None
    )


def _send_reset_code_email(to_email, username, code):
    smtp_host = os.getenv('SMTP_HOST', '').strip()
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '').strip()
    smtp_password = os.getenv('SMTP_PASS', '').strip()
    from_email = os.getenv('SMTP_FROM', smtp_user).strip()
    use_tls = os.getenv('SMTP_USE_TLS', 'true').strip().lower() in ('1', 'true', 'yes', 'y')

    if not smtp_host or not smtp_user or not smtp_password or not from_email:
        raise RuntimeError('Configura SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS y SMTP_FROM en .env')

    subject = 'Codigo para recuperar contrasena'
    body = (
        f"Hola {username or 'usuario'},\n\n"
        f"Tu codigo de recuperacion es: {code}\n\n"
        'Este codigo expira en 10 minutos.\n'
        'Si no solicitaste este cambio, ignora este correo.'
    )

    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        if use_tls:
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(from_email, [to_email], msg.as_string())


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    user_input = (data.get('user') or data.get('email') or data.get('username') or '').strip()
    password = data.get('password', '')

    if not user_input or not password:
        return jsonify({'msg': 'usuario y contrasena requeridos'}), 400

    users = _load_users()
    user = _find_user(users, user_input)

    if not user:
        return jsonify({'msg': 'credenciales invalidas'}), 401

    if user.get('password_hash'):
        try:
            if not check_password_hash(user.get('password_hash'), password):
                return jsonify({'msg': 'credenciales invalidas'}), 401
        except Exception as ex:
            current_app.logger.error(f"Error verificando password_hash: {ex}")
            return jsonify({'msg': 'error verificacion de contrasena'}), 500
    elif user.get('password'):
        if user.get('password') != password:
            return jsonify({'msg': 'credenciales invalidas'}), 401
    else:
        return jsonify({'msg': 'usuario mal configurado'}), 500

    identity = user.get('username') or user.get('email')
    if not isinstance(identity, str):
        identity = str(identity)

    additional_user_claims = {
        'user': {
            'email': user.get('email'),
            'username': user.get('username'),
            'name': user.get('name'),
            'rol': user.get('rol'),
            'theme': user.get('theme', 'light')
        }
    }

    access_token = create_access_token(identity=identity, additional_claims=additional_user_claims)
    refresh_token = create_refresh_token(identity=identity, additional_claims=additional_user_claims)

    resp = jsonify({'msg': 'login correcto', 'user': additional_user_claims['user']})
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp, 200


@auth_bp.route('/forgot-password/request-code', methods=['POST'])
def forgot_password_request_code():
    data = request.get_json() or {}
    user_input = (data.get('user') or data.get('email') or data.get('username') or '').strip()

    if not user_input:
        return jsonify({'msg': 'usuario o correo requerido'}), 400

    users = _load_users()
    user = _find_user(users, user_input)

    # Respuesta neutra para evitar enumeracion de usuarios.
    generic_ok = {'msg': 'Si el usuario existe, enviamos un codigo al correo registrado.'}

    if not user or not user.get('email'):
        return jsonify(generic_ok), 200

    code = f"{random.randint(0, 999999):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    _password_reset_codes[user.get('email')] = {
        'code': code,
        'expires_at': expires_at
    }

    try:
        _send_reset_code_email(user.get('email'), user.get('username'), code)
        return jsonify(generic_ok), 200
    except Exception as err:
        current_app.logger.error(f"No se pudo enviar correo de recuperacion: {err}")
        return jsonify({'msg': 'No se pudo enviar el codigo por correo. Revisa configuracion SMTP.'}), 500


@auth_bp.route('/forgot-password/reset', methods=['POST'])
def forgot_password_reset():
    data = request.get_json() or {}
    user_input = (data.get('user') or data.get('email') or data.get('username') or '').strip()
    code = (data.get('code') or '').strip()
    new_password = data.get('new_password', '')
    confirm_password = data.get('confirm_password', '')

    if not user_input or not code or not new_password or not confirm_password:
        return jsonify({'msg': 'completa todos los campos'}), 400
    if new_password != confirm_password:
        return jsonify({'msg': 'las contrasenas no coinciden'}), 400
    if len(new_password) < 6:
        return jsonify({'msg': 'la nueva contrasena debe tener al menos 6 caracteres'}), 400

    users = _load_users()
    user = _find_user(users, user_input)
    if not user or not user.get('email'):
        return jsonify({'msg': 'codigo invalido o expirado'}), 400

    saved = _password_reset_codes.get(user.get('email'))
    now_utc = datetime.now(timezone.utc)
    if (not saved) or (saved.get('code') != code) or (now_utc > saved.get('expires_at')):
        return jsonify({'msg': 'codigo invalido o expirado'}), 400

    user['password_hash'] = generate_password_hash(new_password)
    user.pop('password', None)

    try:
        _save_users(users)
        _password_reset_codes.pop(user.get('email'), None)
        return jsonify({'msg': 'contrasena actualizada correctamente'}), 200
    except Exception as err:
        current_app.logger.error(f"Error guardando nueva contrasena: {err}")
        return jsonify({'msg': 'no se pudo actualizar la contrasena'}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    jwt_payload = get_jwt()
    user_claim = jwt_payload.get('user', {'username': identity})

    access_token = create_access_token(identity=identity, additional_claims={'user': user_claim})
    resp = jsonify({'msg': 'access refreshed'})
    set_access_cookies(resp, access_token)
    return resp, 200


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    jti = get_jwt().get('jti')
    if jti:
        _blocklist.add(jti)
    resp = jsonify({'msg': 'logout successful'})
    unset_jwt_cookies(resp)
    return resp, 200


@auth_bp.route('/user', methods=['GET'])
@jwt_required()
def get_current_user():
    try:
        jwt_payload = get_jwt()
        user_claim = jwt_payload.get('user') or {}
        user = {
            'name': user_claim.get('name'),
            'username': user_claim.get('username'),
            'email': user_claim.get('email'),
            'rol': user_claim.get('rol'),
            'theme': user_claim.get('theme', 'light')
        }
        return jsonify({'user': user}), 200
    except Exception as e:
        current_app.logger.error(f"Error obteniendo user desde JWT: {e}")
        return jsonify({'msg': 'no se pudo obtener usuario'}), 500


from flask_jwt_extended import JWTManager


def init_blocklist(jwt: JWTManager):
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get('jti')
        if not jti:
            return False
        return jti in _blocklist
