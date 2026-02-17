# blueprint/index.py
from flask import Blueprint, render_template

abastecimientos_bp = Blueprint('abastecimientos', __name__, url_prefix='/abastecimientos', template_folder='../templates')

@abastecimientos_bp.route('/')
def abastecimientos():
    return render_template('abastecimientos.html')
