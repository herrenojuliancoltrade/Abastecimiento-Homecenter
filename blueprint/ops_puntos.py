# blueprint/ops_puntos.py
import json
from pathlib import Path
from threading import Lock
from flask import (
    Blueprint, render_template, jsonify, request, send_file
)
from io import BytesIO
import pandas as pd

opspuntos_bp = Blueprint(
    'opspuntos', __name__,
    url_prefix='/opspuntos',
    template_folder='../templates',
    static_folder='../static'
)

# Ruta relativa al archivo JSON (resuelta desde la ubicación de este archivo)
PROJECT_DIR = Path(__file__).resolve().parent.parent  # sube: blueprint -> Coltrade
JSON_REL_PATH = Path("conexiones") / "data_ops" / "puntos_venta_claro.json"
JSON_PATH = PROJECT_DIR / JSON_REL_PATH

_file_lock = Lock()

def _ensure_file():
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not JSON_PATH.exists():
        with JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def _normalize_centro(centro):
    """Normalize Centro Costos for comparison (strip + lower)"""
    if centro is None:
        return ""
    return str(centro).strip().lower()

def read_puntos():
    _ensure_file()
    with _file_lock:
        text = JSON_PATH.read_text(encoding="utf-8").strip()
        if not text:
            return []
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return [data]
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError:
            # intentar parseo línea por línea (newline-delimited JSON)
            res = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    res.append(obj)
                except Exception:
                    continue
            return res

def write_puntos(list_puntos):
    _ensure_file()
    with _file_lock:
        with JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump(list_puntos, f, ensure_ascii=False, indent=2)

def find_by_centro(centro, puntos=None):
    """Busca por Centro Costos normalizado (case-insensitive, trim)"""
    if puntos is None:
        puntos = read_puntos()
    target_norm = _normalize_centro(centro)
    for p in puntos:
        if _normalize_centro(p.get("Centro Costos")) == target_norm:
            return p
    return None

@opspuntos_bp.route('/')
def index():
    return render_template('opspuntos.html')

# API: listar
@opspuntos_bp.route('/api/puntos', methods=['GET'])
def api_list_puntos():
    puntos = read_puntos()
    return jsonify(puntos), 200

# API: crear
@opspuntos_bp.route('/api/puntos', methods=['POST'])
def api_create_punto():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error":"Cuerpo inválido"}), 400
    centro_raw = payload.get("Centro Costos", "")
    centro = str(centro_raw).strip()
    if not centro:
        return jsonify({"error":"El campo 'Centro Costos' es obligatorio"}), 400

    puntos = read_puntos()
    if find_by_centro(centro, puntos):
        return jsonify({"error":"Ya existe un punto con ese Centro Costos", "code":"duplicate"}), 409

    new_obj = {
        "Centro Costos": centro,
        "Punto de Venta": payload.get("Punto de Venta", "").strip(),
        "Canal o Regional": payload.get("Canal o Regional", "").strip(),
        "Tipo": payload.get("Tipo", "").strip()
    }
    puntos.append(new_obj)
    write_puntos(puntos)
    return jsonify(new_obj), 201

# API: actualizar (editar) por Centro Costos (clave)
@opspuntos_bp.route('/api/puntos/<centro>', methods=['PUT'])
def api_update_punto(centro):
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error":"Cuerpo inválido"}), 400
    centro = str(centro)
    puntos = read_puntos()
    target = find_by_centro(centro, puntos)
    if not target:
        return jsonify({"error":"Punto no encontrado"}), 404

    new_centro_raw = payload.get("Centro Costos", centro)
    new_centro = str(new_centro_raw).strip()
    if not new_centro:
        return jsonify({"error":"El campo 'Centro Costos' no puede quedar vacío"}), 400

    if _normalize_centro(new_centro) != _normalize_centro(centro):
        # si cambia, validar que no exista otro
        if find_by_centro(new_centro, puntos):
            return jsonify({"error":"No se puede cambiar Centro Costos, ya existe otro registro con ese número"}), 409

    target["Centro Costos"] = new_centro
    target["Punto de Venta"] = payload.get("Punto de Venta", target.get("Punto de Venta", "")).strip()
    target["Canal o Regional"] = payload.get("Canal o Regional", target.get("Canal o Regional", "")).strip()
    target["Tipo"] = payload.get("Tipo", target.get("Tipo", "")).strip()
    write_puntos(puntos)
    return jsonify(target), 200

# API: borrar uno
@opspuntos_bp.route('/api/puntos/<centro>', methods=['DELETE'])
def api_delete_punto(centro):
    centro = str(centro)
    puntos = read_puntos()
    new_list = [p for p in puntos if _normalize_centro(p.get("Centro Costos")) != _normalize_centro(centro)]
    if len(new_list) == len(puntos):
        return jsonify({"error":"Punto no encontrado"}), 404
    write_puntos(new_list)
    return jsonify({"ok":True}), 200

# API: borrar todo (requiere confirmar 3 veces en frontend)
@opspuntos_bp.route('/api/delete_all', methods=['POST'])
def api_delete_all():
    data = request.get_json(force=True) or {}
    confirmations = int(data.get("confirmaciones", 0))
    if confirmations < 3:
        return jsonify({"error":"Se requieren 3 confirmaciones para eliminar todos los datos", "confirmaciones_recibidas": confirmations}), 400
    write_puntos([])
    return jsonify({"ok":True, "deleted_all": True}), 200

# API: exportar (Excel o JSON)
@opspuntos_bp.route('/api/export', methods=['GET'])
def api_export():
    fmt = request.args.get("format", "excel").lower()
    puntos = read_puntos()

    # Normalizar estructura a DataFrame
    df = pd.DataFrame(puntos)
    # asegurar columnas
    for c in ["Centro Costos","Punto de Venta","Canal o Regional","Tipo"]:
        if c not in df.columns:
            df[c] = ""

    df = df[["Centro Costos","Punto de Venta","Canal o Regional","Tipo"]]

    if fmt in ("excel","xlsx"):
        output = BytesIO()
        # Exportar a Excel sin índice
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="PuntosVenta")
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="puntos_venta_claro.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        # exportar JSON por compatibilidad
        mem = BytesIO()
        mem.write(json.dumps(puntos, ensure_ascii=False, indent=2).encode("utf-8"))
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name="puntos_venta_claro.json", mimetype="application/json")

# API: importar (subir EXCEL o JSON)
@opspuntos_bp.route('/api/import', methods=['POST'])
def api_import():
    """
    Espera multipart/form-data con archivo en campo 'file'.
    Si es Excel (.xlsx/.xls), intentará leerlo con pandas.
    Si es JSON, espera una lista de objetos o un único objeto.
    Se importan y se ignoran duplicados por 'Centro Costos' (no se sobrescriben).
    Devuelve resumen.
    """
    if 'file' not in request.files:
        return jsonify({"error":"No se encontró archivo en el formulario (campo 'file')"}), 400
    f = request.files['file']
    filename = (f.filename or "").lower()
    content = f.read()
    to_add = []

    try:
        # Intentar leer como Excel primero (más robusto que basarse sólo en extensión)
        read_as_excel = False
        try:
            # si pandas puede leer, esto devolverá un DataFrame o lanzará excepción
            df = pd.read_excel(BytesIO(content), dtype=str)
            read_as_excel = True
        except Exception:
            read_as_excel = False

        if read_as_excel:
            df.columns = [str(c).strip() for c in df.columns]
            lower_map = {c.lower(): c for c in df.columns}
            def get_col(possible):
                for opt in possible:
                    lo = opt.lower()
                    if lo in lower_map:
                        return lower_map[lo]
                return None

            col_centro = get_col(["Centro Costos","Centro_Costos","centro costos","centro_costos","centro"])
            col_punto = get_col(["Punto de Venta","Punto_de_Venta","punto de venta","punto_venta","Punto","punto"])
            col_canal = get_col(["Canal o Regional","Canal","Regional","canal o regional","canal_o_regional"])
            col_tipo = get_col(["Tipo","tipo"])

            if not col_centro:
                return jsonify({"error":"El archivo Excel debe tener una columna 'Centro Costos' (o similar)"}), 400

            # asegurar strings
            df[col_centro] = df[col_centro].astype(str).fillna("").str.strip()
            df[col_centro] = df[col_centro].str.replace(r'\.0+$', '', regex=True)

            for _, row in df.iterrows():
                centro = str(row.get(col_centro) or "").strip()
                if not centro:
                    continue
                punto = str(row.get(col_punto) or "").strip() if col_punto else ""
                canal = str(row.get(col_canal) or "").strip() if col_canal else ""
                tipo = str(row.get(col_tipo) or "").strip() if col_tipo else ""
                to_add.append({
                    "Centro Costos": centro,
                    "Punto de Venta": punto,
                    "Canal o Regional": canal,
                    "Tipo": tipo
                })
        else:
            # intentar JSON
            s = content.decode("utf-8", errors="replace").strip()
            parsed = json.loads(s)
            if isinstance(parsed, dict):
                to_add = [parsed]
            elif isinstance(parsed, list):
                to_add = parsed
            else:
                return jsonify({"error":"Formato JSON inválido"}), 400

            norm = []
            for item in to_add:
                if not isinstance(item, dict):
                    continue
                centro = str(item.get("Centro Costos") or item.get("centro_costos") or item.get("centro") or "").strip()
                if not centro:
                    continue
                norm.append({
                    "Centro Costos": centro,
                    "Punto de Venta": (item.get("Punto de Venta") or item.get("punto_de_venta") or item.get("punto") or "").strip(),
                    "Canal o Regional": (item.get("Canal o Regional") or item.get("canal") or item.get("regional") or "").strip(),
                    "Tipo": (item.get("Tipo") or item.get("tipo") or "").strip()
                })
            to_add = norm

    except json.JSONDecodeError as jde:
        return jsonify({"error":"JSON inválido", "detail": str(jde)}), 400
    except Exception as e:
        return jsonify({"error":"No se pudo parsear el archivo", "detail": str(e)}), 400

    # merge y evitar duplicados por 'Centro Costos' (normalizado)
    puntos = read_puntos()
    existing_centros = { _normalize_centro(p.get("Centro Costos")) for p in puntos }
    added = 0
    for item in to_add:
        item_centro_norm = _normalize_centro(item.get("Centro Costos"))
        if item_centro_norm in existing_centros or item_centro_norm == "":
            continue
        # normalizar valores antes de guardar
        puntos.append({
            "Centro Costos": str(item.get("Centro Costos")).strip(),
            "Punto de Venta": str(item.get("Punto de Venta") or "").strip(),
            "Canal o Regional": str(item.get("Canal o Regional") or "").strip(),
            "Tipo": str(item.get("Tipo") or "").strip()
        })
        existing_centros.add(item_centro_norm)
        added += 1
    write_puntos(puntos)
    return jsonify({"ok":True, "added": added, "total_after": len(puntos)}), 200
