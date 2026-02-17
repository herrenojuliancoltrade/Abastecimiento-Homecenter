# blueprint/auth.py
import os
import json
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    set_access_cookies, set_refresh_cookies,
    unset_jwt_cookies, jwt_required, get_jwt_identity, get_jwt
)

auth_bp = Blueprint('auth', __name__, url_prefix='/api')

# Blocklist en memoria (para logout)
_blocklist = set()

def _load_users():
    """
    Carga el archivo login.json desde una ruta relativa.
    Busca dentro de la carpeta 'conexiones' que está en la raíz del proyecto.
    Estructura esperada (ejemplo):
    [
      { "username": "juli", "email": "juli@ejemplo.com", "password_hash": "<hash>", "name": "Julian" },
      ...
    ]
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))  # /blueprint
    project_root = os.path.abspath(os.path.join(base_dir, '..'))  # sube al root del proyecto
    path = os.path.join(project_root, 'conexiones', 'login.json')

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

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Login que autentica contra login.json, crea access/refresh tokens y los guarda en cookies.
    Se acepta 'user' o 'email' o 'username' en el payload JSON.
    """
    data = request.get_json() or {}
    user_input = (data.get('user') or data.get('email') or data.get('username') or '').strip()
    password = data.get('password', '')

    if not user_input or not password:
        return jsonify({"msg": "usuario y contraseña requeridos"}), 400

    users = _load_users()

    # Buscar por email o username (case-insensitive para username)
    user = next(
        (u for u in users if (u.get('email') == user_input)
         or (u.get('username') and u.get('username').lower() == user_input.lower())),
        None
    )

    if not user:
        return jsonify({"msg": "credenciales inválidas"}), 401

    # Soporta password en texto o password_hash (werkzeug)
    from werkzeug.security import check_password_hash

    if user.get('password_hash'):
        try:
            if not check_password_hash(user.get('password_hash'), password):
                return jsonify({"msg": "credenciales inválidas"}), 401
        except Exception as ex:
            current_app.logger.error(f"Error verificando password_hash: {ex}")
            return jsonify({"msg": "error verificación de contraseña"}), 500
    elif user.get('password'):
        if user.get('password') != password:
            return jsonify({"msg": "credenciales inválidas"}), 401
    else:
        return jsonify({"msg": "usuario mal configurado"}), 500

    # IDENTIDAD: debe ser string (para evitar error "Subject must be a string")
    identity = user.get('username') or user.get('email')
    if not isinstance(identity, str):
        identity = str(identity)

    # Claims adicionales con información pública del usuario
    additional_user_claims = {
        "user": {
            "email": user.get('email'),
            "username": user.get('username'),
            "name": user.get('name')
        }
    }

    access_token = create_access_token(identity=identity, additional_claims=additional_user_claims)
    refresh_token = create_refresh_token(identity=identity, additional_claims=additional_user_claims)

    resp = jsonify({"msg": "login correcto", "user": additional_user_claims["user"]})
    set_access_cookies(resp, access_token)
    set_refresh_cookies(resp, refresh_token)
    return resp, 200

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh del access token usando el refresh token (en cookie).
    Devuelve nueva access cookie.
    """
    identity = get_jwt_identity()
    jwt_payload = get_jwt()
    user_claim = jwt_payload.get('user', {"username": identity})

    access_token = create_access_token(identity=identity, additional_claims={"user": user_claim})
    resp = jsonify({"msg": "access refreshed"})
    set_access_cookies(resp, access_token)
    return resp, 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout: agrega el jti del token actual al blocklist y borra cookies.
    """
    jti = get_jwt().get("jti")
    if jti:
        _blocklist.add(jti)
    resp = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(resp)
    return resp, 200

@auth_bp.route('/user', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Devuelve la información del usuario almacenada en los claims JWT
    (la clave 'user' la generas en login: additional_user_claims).
    Este endpoint es útil para el front (ej. /api/user).
    """
    try:
        jwt_payload = get_jwt()
        user_claim = jwt_payload.get('user') or {}
        user = {
            "name": user_claim.get('name'),
            "username": user_claim.get('username'),
            "email": user_claim.get('email')
        }
        return jsonify({"user": user}), 200
    except Exception as e:
        current_app.logger.error(f"Error obteniendo user desde JWT: {e}")
        return jsonify({"msg": "no se pudo obtener usuario"}), 500

# Inicializar el blocklist loader
from flask_jwt_extended import JWTManager

def init_blocklist(jwt: JWTManager):
    """
    Registra el token_in_blocklist_loader para verificar tokens revocados.
    Llamar desde app.py: init_blocklist(jwt)
    """
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        if not jti:
            return False
        return jti in _blocklist
