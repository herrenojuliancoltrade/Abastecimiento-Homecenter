
import io
from flask import Blueprint, render_template, request, jsonify, send_file
import pandas as pd

# Blueprint
unir_bp = Blueprint('unir', __name__, url_prefix='/unir', template_folder='../templates')

# Columnas que quieres conservar y en ese orden exacto
DESIRED_COLS = [
    "Centro Costos",
    "Punto de Venta",
    "Material",
    "Producto",
    "Marca",
    "Ventas Actuales",
    "Transitos",
    "Inventario",
    "Envío Inventario 3 meses",
    "Sugerido"
]

@unir_bp.route('/')
def index():
    return render_template('unir.html')

def read_and_concat(uploaded_files):
    """
    Lee cada archivo Excel enviado (primer sheet por defecto), concatena y
    devuelve un DataFrame con solo las columnas deseadas (creando columnas vacías si faltan).
    """
    dfs = []
    for f in uploaded_files:
        # Flask file-like object: f is a FileStorage
        try:
            # Intenta leer la primera hoja
            df = pd.read_excel(f, sheet_name=0)
        except Exception as e:
            # Si falla, propaga el error para informar al usuario
            raise RuntimeError(f"No se pudo leer {getattr(f, 'filename', 'archivo')}: {str(e)}")
        dfs.append(df)

    if not dfs:
        return pd.DataFrame(columns=DESIRED_COLS)

    concatenated = pd.concat(dfs, ignore_index=True, sort=False)

    # Asegurar existencia de todas las columnas solicitadas
    for col in DESIRED_COLS:
        if col not in concatenated.columns:
            concatenated[col] = pd.NA

    # Reordenar y devolver solo las columnas solicitadas
    result = concatenated.loc[:, DESIRED_COLS].copy()
    return result

@unir_bp.route('/preview', methods=['POST'])
def preview():
    """
    Endpoint para previsualizar la concatenación (devuelve JSON con columnas y filas).
    """
    files = request.files.getlist('files[]') or request.files.getlist('files')
    if not files:
        return jsonify({"error": "No se subieron archivos"}), 400
    try:
        df = read_and_concat(files)
        # Convertir a tipos básicos y vacíos por NaN para el frontend
        preview_df = df.head(200).fillna('')
        rows = preview_df.values.tolist()
        return jsonify({
            "columns": list(preview_df.columns),
            "rows": rows
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@unir_bp.route('/merge', methods=['POST'])
def merge_and_download():
    """
    Endpoint que concatena y devuelve un archivo Excel para descargar.
    """
    files = request.files.getlist('files[]') or request.files.getlist('files')
    if not files:
        return jsonify({"error": "No se subieron archivos"}), 400
    try:
        df = read_and_concat(files)

        output = io.BytesIO()
        # Escribir excel en memoria
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Unido')
        output.seek(0)

        # Enviar archivo como descarga
        return send_file(
            output,
            as_attachment=True,
            download_name='unido.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
