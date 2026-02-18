# app.py
import os
import threading
import webbrowser
from datetime import timedelta
from dotenv import load_dotenv
from flask import Flask, redirect, request, jsonify
from flask_jwt_extended import JWTManager, verify_jwt_in_request
from flask_jwt_extended.exceptions import NoAuthorizationError

# Carga .env
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'static')

app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# Seguridad - desde .env en producción
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev-key-solo-para-desarrollo')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-dev-key-reemplaza-en-prod')

# JWT en cookies (HttpOnly)
app.config['JWT_TOKEN_LOCATION'] = ['cookies']
app.config['JWT_ACCESS_COOKIE_PATH'] = '/'
app.config['JWT_REFRESH_COOKIE_PATH'] = '/api/refresh'
app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # en prod: True
app.config['JWT_COOKIE_SECURE'] = False        # en prod: True (HTTPS)
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'

# ===================== CAMBIO IMPORTANTE =====================
# Querías que la sesión dure como máximo 2 horas y 30 minutos (2.5 h).
# Ajustamos BOTH: access token y refresh token a 2.5 horas (150 minutos).
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=2, minutes=30)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(hours=2, minutes=30)
# =============================================================

app.config['PROPAGATE_EXCEPTIONS'] = True

jwt = JWTManager(app)

# -------------------------
# Handlers JWT (manejo de errores)
# -------------------------
@jwt.unauthorized_loader
def custom_unauthorized_loader(reason):
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({"msg": reason}), 401
    return redirect('/inicio/')

@jwt.invalid_token_loader
def custom_invalid_token_loader(reason):
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({"msg": f"Invalid token: {reason}"}), 422
    return redirect('/inicio/')

@jwt.expired_token_loader
def custom_expired_token_loader(jwt_header, jwt_payload):
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({"msg": "Token expirado"}), 401
    return redirect('/inicio/')

@jwt.revoked_token_loader
def custom_revoked_token_loader(jwt_header, jwt_payload):
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({"msg": "Token revocado"}), 401
    return redirect('/inicio/')

@jwt.needs_fresh_token_loader
def custom_needs_fresh_token_loader(jwt_header, jwt_payload):
    if request.path.startswith('/api/') or request.is_json:
        return jsonify({"msg": "Se requiere un token fresco (fresh)"}), 401
    return redirect('/inicio/')

# -------------------------------------------------
# Importa tus blueprints (variables) aquí
# -------------------------------------------------
# Asegúrate que en cada archivo de blueprint definiste las variables
# por ejemplo: operaciones_bp = Blueprint('operaciones', __name__, ...)
from blueprint.index import index_bp
from blueprint.operaciones import operaciones_bp
from blueprint.ops_productos import opsproductos_bp
from blueprint.ops_puntos import opspuntos_bp
from blueprint.ops_ventasclaro import ventasclaro_bp
from blueprint.inventario_claro import inventario_bp
from blueprint.transitos import transitos_bp
from blueprint.metas import metas_bp
from blueprint.abastecimientos_claro import abastecimientos_bp
from blueprint.forecast_abastecimiento import forecast_bp
from blueprint.unirarchivos import unir_bp
from blueprint.cruzar import cruzar_bp
from blueprint.serializar_ventas  import serializarventas_bp
from blueprint.data_claro import claro_bp
from blueprint.data_coltrade import coltrade_bp
from blueprint.JustinTime import justinTime_bp
from blueprint.compras import compras_bp
from blueprint.auth import auth_bp, init_blocklist
# -------------------------------------------------

# -------------------------------------------------
# ### EDITAR AQUÍ: listas usando las VARIABLES de blueprint ###
# -------------------------------------------------
PROTECTED_BLUEPRINTS = {
    operaciones_bp,
    opsproductos_bp ,
    opspuntos_bp,
    ventasclaro_bp,
    inventario_bp,
    transitos_bp,
    metas_bp,
    abastecimientos_bp,
    unir_bp,
    cruzar_bp,
    serializarventas_bp,
    claro_bp,
    coltrade_bp,
    justinTime_bp,
    compras_bp
}

EXEMPT_BLUEPRINTS = {
    index_bp,
    auth_bp
}
# -------------------------------------------------

PROTECTED_PATH_PREFIXES = {
    '/admin',
    '/private'
}

def _get_current_blueprint_obj():
    bp_name = request.blueprint
    if not bp_name:
        return None
    return app.blueprints.get(bp_name)

def _is_protected_by_blueprint_obj():
    current_bp_obj = _get_current_blueprint_obj()
    if not current_bp_obj:
        return False
    if current_bp_obj in EXEMPT_BLUEPRINTS:
        return False
    if current_bp_obj in PROTECTED_BLUEPRINTS:
        return True
    return False

def _is_protected_by_path_prefix():
    for prefix in PROTECTED_PATH_PREFIXES:
        if request.path.startswith(prefix):
            return True
    return False

@app.before_request
def require_login_for_protected_routes():
    # permitir archivos estáticos
    if request.path.startswith('/static/'):
        return None

    # rutas públicas globales (login + endpoints de auth)
    EXEMPT_PATHS = {
        '/inicio/',       # página de login
        '/api/login',     # endpoint login
        '/api/refresh',   # refresh token
        '/api/logout'     # logout
    }
    if request.path in EXEMPT_PATHS:
        return None

    # decidir si la ruta actual es protegida por blueprint (objeto) o por prefijo
    protected = _is_protected_by_blueprint_obj() or _is_protected_by_path_prefix()

    # si no está protegida, permitir
    if not protected:
        return None

    # si está protegida -> verificar token (cookie)
    try:
        verify_jwt_in_request()
        return None  # token válido, dejar pasar
    except NoAuthorizationError as e:
        # falta token o no autorizado
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({"msg": str(e)}), 401
        return redirect('/inicio/')
    except Exception as e:
        # token inválido, expirado, revocado, etc.
        if request.path.startswith('/api/') or request.is_json:
            return jsonify({"msg": "Token inválido o expirado", "detail": str(e)}), 401
        return redirect('/inicio/')

# --- Registrar blueprints (orden no importa para el control) ---
app.register_blueprint(index_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(operaciones_bp)
app.register_blueprint(opsproductos_bp)
app.register_blueprint(opspuntos_bp)
app.register_blueprint(ventasclaro_bp)
app.register_blueprint(inventario_bp)
app.register_blueprint(transitos_bp)
app.register_blueprint(metas_bp)
app.register_blueprint(abastecimientos_bp)
app.register_blueprint(forecast_bp)
app.register_blueprint(unir_bp)
app.register_blueprint(cruzar_bp)
app.register_blueprint(serializarventas_bp)
app.register_blueprint(claro_bp)
app.register_blueprint(coltrade_bp)
app.register_blueprint(justinTime_bp)
app.register_blueprint(compras_bp)

# Inicializar blocklist checker (desde blueprint/auth.py)
init_blocklist(jwt)

# Ruta de debug para ver blueprints registrados (útil en dev)
@app.route('/debug/blueprints')
def debug_blueprints():
    # Borra o protege esta ruta en producción
    return jsonify({"blueprints_registered": list(app.blueprints.keys())})

@app.route('/')
def root():
    return redirect('/inicio/')

# -------------------------------------------------------
# Control opcional para abrir navegador AUTOMÁTICAMENTE
# -------------------------------------------------------
# Por defecto NO se abrirá el navegador. Si quieres habilitarlo,
# crea/edita tu .env y añade: AUTO_OPEN_BROWSER=true
def abrir_navegador():
    try:
        webbrowser.open_new("http://localhost:3000/inicio/")
    except Exception:
        pass

def should_auto_open_browser():
    # Solo permitir auto abrir en entornos NO production y si la variable está activada
    if os.environ.get("FLASK_ENV") == "production":
        return False
    val = os.environ.get("AUTO_OPEN_BROWSER", "false").strip().lower()
    return val in ("1", "true", "yes", "y")

if __name__ == '__main__':
    # Si la variable AUTO_OPEN_BROWSER está activada y no estamos en la segunda
    # instancia del reloader, programamos la apertura del navegador.
    if should_auto_open_browser() and not os.environ.get("WERKZEUG_RUN_MAIN"):
        # pequeña demora para que el servidor arranque antes de abrir el navegador
        threading.Timer(1.25, abrir_navegador).start()

    app.run(
        host='0.0.0.0',
        port=3000,
        debug=os.environ.get("FLASK_ENV") == "development",
        threaded=True
    )
