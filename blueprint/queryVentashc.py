# blueprint/index.py
from flask import Blueprint, render_template

queryVentasHc_bp = Blueprint('queryVentasHc', __name__, url_prefix='/queryVentasHc', template_folder='../templates')

@queryVentasHc_bp.route('/')
def queryVentasHc():
    return render_template('queryVentasHc.html')
