# blueprint/serializar_ventas.py
from flask import Blueprint, render_template, request, send_file, jsonify
import pandas as pd
import io
from datetime import datetime
import re

serializarventas_bp = Blueprint(
    'serializarventas', __name__, url_prefix='/serializarventas', template_folder='../templates'
)

MARCAS_ESPECIFICAS = [
    'Aiwa', 'Amazon', 'Belkin', 'Pmp', 'Haxly', 'Sylvania',
    'Roku', 'Nintendo', 'Redragon', 'Spigen', 'Motorola',
    'Logitech', 'Zte', 'Cubitt'
]

def increment_serial(serial):
    """Incrementa un serial alfanumérico, buscando el último número para incrementarlo"""
    if pd.isna(serial) or serial == '':
        return ''
    serial_str = str(serial)
    matches = list(re.finditer(r'(\d+)', serial_str))
    if not matches:
        return serial_str + '1'
    last_match = matches[-1]
    start, end = last_match.span()
    num = int(last_match.group())
    incremented_num = num + 1
    new_serial = serial_str[:start] + str(incremented_num) + serial_str[end:]
    return new_serial

@serializarventas_bp.route('/', methods=['GET'])
def index():
    # Renderiza la plantilla y pasa la lista de marcas específicas para generar inputs
    return render_template('serializarventas.html', marcas_especificas=MARCAS_ESPECIFICAS, marcas_importadas=None)

@serializarventas_bp.route('/preview', methods=['POST'])
def preview_marcas():
    """Recibe el archivo Excel (form-data file) y devuelve las marcas detectadas en JSON"""
    file = request.files.get('file')
    if not file:
        return jsonify({'error': 'No se envió archivo'}), 400
    try:
        df = pd.read_excel(file)
    except Exception as e:
        return jsonify({'error': f'Error al leer el archivo: {e}'}), 400

    # Filtrar Sugerido Final y obtener marcas únicas
    if 'Sugerido Final' in df.columns:
        df = df.dropna(subset=['Sugerido Final'])
        df = df[df['Sugerido Final'] != 0]

    marcas = []
    if 'Marca' in df.columns:
        marcas = list(pd.Series(df['Marca'].astype(str).str.strip().unique()))

    return jsonify({'marcas': marcas})

@serializarventas_bp.route('/process', methods=['POST'])
def procesar_y_descargar():
    file = request.files.get('file')
    if not file:
        return "No se ha proporcionado un archivo", 400

    try:
        df = pd.read_excel(file)
    except Exception as e:
        return f"Error al leer el archivo: {str(e)}", 400

    required_columns = ['Material', 'Producto', 'Marca', 'Centro Costos',
                        'Punto de Venta', 'Sugerido Final']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        return f"Faltan columnas requeridas: {', '.join(missing_cols)}", 400

    # Filtrar registros donde Sugerido Final es null o 0
    df = df.dropna(subset=['Sugerido Final'])
    df = df[df['Sugerido Final'] != 0]

    final_df = pd.DataFrame(columns=[
        'No', 'Centro Costos', 'Punto de Venta', 'Material',
        'Producto', 'Marca', 'Fecha Actual', 'Serial', 'Sugerido Final'
    ])

    # Obtener seriales iniciales del formulario
    seriales_iniciales = {}
    for marca in MARCAS_ESPECIFICAS:
        key = marca.lower()
        serial_val = request.form.get(f'serial_{key}', '').strip()
        if key == 'haxly' and serial_val == '250':
            serial_val = '201'
        seriales_iniciales[key] = serial_val

    otros_serial = request.form.get('otros_serial', '').strip()
    ultimos_seriales = {}

    groups = df.groupby(['Centro Costos', 'Punto de Venta', 'Material', 'Producto', 'Marca', 'Sugerido Final'])

    for (centro, punto, material, producto, marca, sugerido), group_df in groups:
        num_registros = int(sugerido)
        grupo_df = pd.DataFrame({
            'Centro Costos': [centro] * num_registros,
            'Punto de Venta': [punto] * num_registros,
            'Material': [material] * num_registros,
            'Producto': [producto] * num_registros,
            'Marca': [marca] * num_registros,
            'Fecha Actual': [datetime.today().strftime('%Y-%m-%d')] * num_registros,
            'Serial': [''] * num_registros,
            'Sugerido Final': [sugerido] * num_registros
        })

        grupo_df['No'] = range(1, num_registros + 1)

        marca_key = marca.lower()
        serial_asignado = None

        for marca_esp in MARCAS_ESPECIFICAS:
            if marca_esp.lower() in marca_key:
                marca_key = marca_esp.lower()
                if seriales_iniciales.get(marca_key):
                    serial_asignado = seriales_iniciales[marca_key]
                break
        else:
            if otros_serial:
                marca_key = 'otros'
                serial_asignado = otros_serial

        if serial_asignado:
            current_serial = serial_asignado
            for i in range(num_registros):
                grupo_df.at[i, 'Serial'] = current_serial
                ultimos_seriales[marca] = current_serial
                current_serial = increment_serial(current_serial)

            if marca_key in seriales_iniciales:
                seriales_iniciales[marca_key] = current_serial
            elif marca_key == 'otros':
                otros_serial = current_serial

        final_df = pd.concat([final_df, grupo_df], ignore_index=True)

        # Agregar fila de recuento
        recuento_row = pd.DataFrame([{
            'No': '',
            'Centro Costos': '',
            'Punto de Venta': 'Recuento de Unidades',
            'Material': num_registros,
            'Producto': '',
            'Marca': '',
            'Fecha Actual': '',
            'Serial': '',
            'Sugerido Final': ''
        }])
        final_df = pd.concat([final_df, recuento_row], ignore_index=True)

    # Preparar hoja resumen de marcas
    if ultimos_seriales:
        registros_resumen = []
        for marca, serial in ultimos_seriales.items():
            registro = 'No'
            for marca_esp in MARCAS_ESPECIFICAS:
                if marca_esp.lower() in marca.lower():
                    registro = 'Si'
                    break
            registros_resumen.append({
                'Marca': marca,
                'Ultimo Serial': serial,
                '¿Registro?': registro
            })
        resumen_df = pd.DataFrame(registros_resumen)
        resumen_df = resumen_df.sort_values('Marca').reset_index(drop=True)
    else:
        resumen_df = pd.DataFrame(columns=['Marca', 'Ultimo Serial', '¿Registro?'])

    # Escribir Excel en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        final_df.to_excel(writer, index=False, sheet_name='Serializado')
        resumen_df.to_excel(writer, index=False, sheet_name='Resumen Seriales')

        workbook = writer.book
        worksheet = writer.sheets['Serializado']
        bold_format = workbook.add_format({'bold': True})

        for i, row in final_df.iterrows():
            if row['Punto de Venta'] == 'Recuento de Unidades':
                worksheet.set_row(i + 1, None, bold_format)
                worksheet.write(i + 1, 3, row['Material'], bold_format)

    output.seek(0)
    return send_file(output, download_name='archivo_serializado.xlsx', as_attachment=True)
