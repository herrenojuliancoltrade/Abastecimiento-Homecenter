# blueprint/index.py
from flask import Blueprint, render_template

operaciones_bp = Blueprint('operaciones', __name__, url_prefix='/apps_operaciones', template_folder='../templates')

@operaciones_bp.route('/')
def operaciones():
    return render_template('operaciones.html')
