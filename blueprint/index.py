# blueprint/index.py
from flask import Blueprint, render_template

index_bp = Blueprint('inicio', __name__, url_prefix='/inicio', template_folder='../templates')

@index_bp.route('/')
def index():
    return render_template('index.html')


@index_bp.route('/recuperar-password')
def forgot_password():
    return render_template('forgotPassword.html')
