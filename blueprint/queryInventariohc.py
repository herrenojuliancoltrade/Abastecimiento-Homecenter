import io
import os
import re
from flask import Blueprint, jsonify, render_template, request, send_file
import pandas as pd
from werkzeug.utils import secure_filename

queryInventarioHc_bp = Blueprint(
    'queryInventarioHc',
    __name__,
    url_prefix='/queryInventarioHc',
    template_folder='../templates'
)

TARGET_COLUMNS = [
    "CodBar",
    "Loc",
    "CANTIDAD",
]

OUTPUT_COLUMNS = [
    "Centro Costos",
    "Material",
    "Inventario",
]

COLUMN_RENAME_MAP = {
    "CodBar": "Material",
    "Loc": "Centro Costos",
    "CANTIDAD": "Inventario",
}


def _normalize_column_name(column_name):
    return re.sub(r"\s+", " ", str(column_name or "")).strip()


def _read_and_filter_excel(file_storage):
    dataframe = pd.read_excel(file_storage, sheet_name='INVENTARIO')
    dataframe.columns = [_normalize_column_name(col) for col in dataframe.columns]

    normalized_to_real = {col: col for col in dataframe.columns}
    missing_columns = [
        required
        for required in TARGET_COLUMNS
        if _normalize_column_name(required) not in normalized_to_real
    ]
    if missing_columns:
        raise ValueError(
            "El archivo no contiene estas columnas requeridas: "
            + ", ".join(missing_columns)
        )

    selected_columns = [
        normalized_to_real[_normalize_column_name(required)]
        for required in TARGET_COLUMNS
    ]
    filtered = dataframe[selected_columns].copy()
    filtered.columns = TARGET_COLUMNS
    filtered = filtered.rename(columns=COLUMN_RENAME_MAP)
    filtered = filtered[OUTPUT_COLUMNS]
    filtered = filtered.dropna(how='all')
    return filtered


@queryInventarioHc_bp.route('/')
def query_inventario_hc():
    return render_template('queryInventarioHc.html')


@queryInventarioHc_bp.route('/preview', methods=['POST'])
def preview():
    if 'file' not in request.files:
        return jsonify({"error": "Debes adjuntar un archivo Excel."}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({"error": "No se encontró archivo para procesar."}), 400

    try:
        filtered = _read_and_filter_excel(file)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except Exception as err:
        return jsonify({"error": f"No se pudo leer la hoja INVENTARIO. Detalle: {err}"}), 400

    preview_rows = (
        filtered.head(20)
        .fillna("")
        .astype(str)
        .to_dict(orient='records')
    )
    return jsonify({
        "columns": OUTPUT_COLUMNS,
        "rows": preview_rows,
        "total_rows": int(len(filtered)),
    })


@queryInventarioHc_bp.route('/procesar', methods=['POST'])
def procesar():
    if 'file' not in request.files:
        return jsonify({"error": "Debes adjuntar un archivo Excel."}), 400

    file = request.files['file']
    if not file or not file.filename:
        return jsonify({"error": "No se encontró archivo para procesar."}), 400

    filename = secure_filename(file.filename)
    _, ext = os.path.splitext(filename.lower())
    if ext not in {'.xlsx', '.xlsm', '.xls'}:
        return jsonify({"error": "Formato inválido. Usa un archivo Excel (.xlsx, .xlsm, .xls)."}), 400

    try:
        filtered = _read_and_filter_excel(file)
    except ValueError as err:
        return jsonify({"error": str(err)}), 400
    except Exception as err:
        return jsonify({"error": f"No se pudo leer la hoja INVENTARIO. Detalle: {err}"}), 400

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        filtered.to_excel(writer, index=False, sheet_name='INVENTARIO_FILTRADO')
    output.seek(0)

    output_filename = f"{os.path.splitext(filename)[0]}_inventario_filtrado.xlsx"
    return send_file(
        output,
        as_attachment=True,
        download_name=output_filename,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
