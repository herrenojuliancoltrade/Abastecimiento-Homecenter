import json
from pathlib import Path
from io import BytesIO
from flask import Blueprint, render_template, jsonify, request, send_file, current_app
import pandas as pd
from datetime import datetime

cruzar_bp = Blueprint('cruzar', __name__, url_prefix='/cruzar', template_folder='../templates', static_folder='../static')

# Rutas relativas desde la raíz del proyecto
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'conexiones' / 'data_ops'

FILES = {
    'data_claro': DATA_DIR / 'data_claro.json',
    'data_coltrade': DATA_DIR / 'data_coltrade.json',
    'productos_claro': DATA_DIR / 'productos_claro.json',
    'puntos_venta_claro': DATA_DIR / 'puntos_venta_claro.json',
    'ventas_claro': DATA_DIR / 'ventas_claro.json',
    'transitos': DATA_DIR / 'transitos.json',
    'inventario_claro': DATA_DIR / 'inventario_claro.json',
}


def safe_load_json(path: Path):
    """Carga JSON ya sea objeto único o lista; devuelve lista de dicts."""
    if not path.exists():
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            obj = json.load(f)
            if isinstance(obj, list):
                return obj
            if isinstance(obj, dict):
                return [obj]
            return []
    except Exception:
        try:
            text = path.read_text(encoding='utf-8').strip()
            if not text:
                return []
            return json.loads(f'[{text}]')
        except Exception:
            return []


def get_current_month_ventas():
    """Obtiene las ventas del mes actual desde ventas_claro.json"""
    ventas_data = safe_load_json(FILES['ventas_claro'])
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    ventas_mes_actual = {}
    
    for venta in ventas_data:
        fecha_venta = venta.get('Fecha Venta', '')
        if fecha_venta:
            try:
                # Parsear fecha en formato YYYY-MM-DD HH:MM:SS o YYYY-MM-DD
                fecha_str = fecha_venta.split()[0]  # Tomar solo la parte de fecha
                fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
                if fecha.month == current_month and fecha.year == current_year:
                    centro_costos = str(venta.get('Centro Costos', '')).strip()
                    material = str(venta.get('Material', '')).strip()
                    cantidad = float(venta.get('Cantidad', 0))
                    
                    if centro_costos and material:
                        key = f"{material}|{centro_costos}"
                        ventas_mes_actual[key] = ventas_mes_actual.get(key, 0) + cantidad
            except (ValueError, TypeError):
                continue
    
    return ventas_mes_actual


def get_transitos_data():
    """Obtiene todos los tránsitos desde transitos.json"""
    transitos_data = safe_load_json(FILES['transitos'])
    transitos_dict = {}
    
    for transito in transitos_data:
        centro_costos = str(transito.get('Centro Costos', '')).strip()
        material = str(transito.get('Material', '')).strip()
        cantidad = float(transito.get('Transitos', 0))
        
        if centro_costos and material:
            key = f"{material}|{centro_costos}"
            transitos_dict[key] = cantidad
    
    return transitos_dict


def get_inventario_data():
    """Obtiene todos los inventarios desde inventario_claro.json"""
    inventario_data = safe_load_json(FILES['inventario_claro'])
    inventario_dict = {}
    
    for inventario in inventario_data:
        centro_costos = str(inventario.get('Centro Costos', '')).strip()
        material = str(inventario.get('Material', '')).strip()
        cantidad = float(inventario.get('Inventario', 0))
        
        if centro_costos and material:
            key = f"{material}|{centro_costos}"
            inventario_dict[key] = cantidad
    
    return inventario_dict


def build_dataframe():
    """Construye el DataFrame combinado usando Material + Centro Costos como claves únicas."""
    
    # Cargar todos los archivos JSON
    data_claro = safe_load_json(FILES['data_claro'])
    data_coltrade = safe_load_json(FILES['data_coltrade'])
    productos = safe_load_json(FILES['productos_claro'])
    puntos = safe_load_json(FILES['puntos_venta_claro'])
    
    # Cargar datos adicionales
    ventas_mes_actual = get_current_month_ventas()
    transitos_dict = get_transitos_data()
    inventario_dict = get_inventario_data()
    
    # Crear diccionarios de lookup por Material
    productos_dict = {}
    for prod in productos:
        mat = str(prod.get('Material', '')).strip()
        if mat:
            productos_dict[mat] = {
                'Producto': prod.get('Producto', ''),
                'Marca': prod.get('Marca', '')
            }
    
    # Crear diccionarios de lookup por Centro Costos
    puntos_dict = {}
    for punto in puntos:
        cc = str(punto.get('Centro Costos', '')).strip()
        if cc:
            puntos_dict[cc] = {
                'Punto de Venta': punto.get('Punto de Venta', '')
            }
    
    # Diccionario final para almacenar todos los registros únicos
    registros = {}
    
    # Procesar data_claro
    for item in data_claro:
        material = str(item.get('Material', '')).strip()
        centro_costos = str(item.get('Centro Costos', '')).strip()
        
        if not material or not centro_costos:
            continue
            
        key = f"{material}|{centro_costos}"
        
        if key not in registros:
            registros[key] = {
                'Material': material,
                'Centro Costos': centro_costos,
                'Producto': '',
                'Marca': '',
                'Punto de Venta': '',
                'Sugerido Claro': 0,
                'Inventario': 0,
                'Transitos': 0,
                'Ventas Actuales': 0,
                'Envío Inventario 3 meses': 0,
                'Sugerido Coltrade': 0,
                'Promedio 3 Meses': 0,
                'Sugerido Final': 0
            }
        
        # Actualizar con datos de Claro
        registros[key]['Sugerido Claro'] = float(item.get('Sugerido Claro', 0) or 0)
    
    # Procesar data_coltrade
    for item in data_coltrade:
        material = str(item.get('Material', '')).strip()
        centro_costos = str(item.get('Centro Costos', '')).strip()
        
        if not material or not centro_costos:
            continue
            
        key = f"{material}|{centro_costos}"
        
        if key not in registros:
            registros[key] = {
                'Material': material,
                'Centro Costos': centro_costos,
                'Producto': '',
                'Marca': '',
                'Punto de Venta': '',
                'Sugerido Claro': 0,
                'Inventario': 0,
                'Transitos': 0,
                'Ventas Actuales': 0,
                'Envío Inventario 3 meses': 0,
                'Sugerido Coltrade': 0,
                'Promedio 3 Meses': 0,
                'Sugerido Final': 0
            }
        
        # Actualizar con datos de Coltrade
        registros[key]['Sugerido Coltrade'] = float(item.get('Sugerido Coltrade', 0) or 0)
        registros[key]['Promedio 3 Meses'] = float(item.get('Promedio 3 Meses', 0) or 0)
    
    # Ahora completar cada registro con la información de lookup
    for key, registro in registros.items():
        material = registro['Material']
        centro_costos = registro['Centro Costos']
        
        # Agregar Producto y Marca desde productos_claro.json
        if material in productos_dict:
            registro['Producto'] = productos_dict[material]['Producto']
            registro['Marca'] = productos_dict[material]['Marca']
        
        # Agregar Punto de Venta desde puntos_venta_claro.json
        if centro_costos in puntos_dict:
            registro['Punto de Venta'] = puntos_dict[centro_costos]['Punto de Venta']
        
        # Agregar Inventario desde inventario_claro.json
        if key in inventario_dict:
            registro['Inventario'] = inventario_dict[key]
        
        # Agregar Transitos desde transitos.json
        if key in transitos_dict:
            registro['Transitos'] = transitos_dict[key]
        
        # Agregar Ventas Actuales desde ventas_claro.json (mes actual)
        if key in ventas_mes_actual:
            registro['Ventas Actuales'] = ventas_mes_actual[key]
        
        # Envío Inventario 3 meses siempre es 0 según requerimiento
        registro['Envío Inventario 3 meses'] = 0
    
    # Convertir a DataFrame
    df = pd.DataFrame(list(registros.values()))
    
    # Orden de columnas final
    output_cols = [
        'Material', 'Producto', 'Marca', 'Centro Costos', 'Punto de Venta',
        'Sugerido Claro', 'Inventario', 'Transitos', 'Ventas Actuales',
        'Envío Inventario 3 meses', 'Sugerido Coltrade', 'Promedio 3 Meses', 'Sugerido Final'
    ]
    
    df = df[output_cols]
    
    # Convertir valores numéricos
    numeric_cols = ['Sugerido Claro', 'Inventario', 'Transitos', 'Ventas Actuales', 
                    'Envío Inventario 3 meses', 'Sugerido Coltrade', 'Promedio 3 Meses', 'Sugerido Final']
    
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Rellenar valores vacíos
    df = df.fillna('')
    
    return df


@cruzar_bp.route('/')
def cruzar():
    return render_template('cruzar.html')


@cruzar_bp.route('/api/data')
def api_data():
    try:
        df = build_dataframe()
        data = df.to_dict(orient='records')
        return jsonify({'status': 'ok', 'data': data})
    except Exception as e:
        current_app.logger.exception("Error building dataframe")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@cruzar_bp.route('/api/export')
def api_export():
    """Exporta el excel con el orden y nombres solicitados."""
    try:
        df = build_dataframe()
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cruzado')
        output.seek(0)
        filename = 'cruzado_export.xlsx'
        return send_file(output,
                         as_attachment=True,
                         download_name=filename,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    except Exception as e:
        current_app.logger.exception("Error exporting excel")
        return jsonify({'status': 'error', 'message': str(e)}), 500