# blueprint/data_claro.py
import json
import math
import uuid
from pathlib import Path
from threading import Lock
from flask import Blueprint, render_template, jsonify, request, send_file
from io import BytesIO
import pandas as pd

claro_bp = Blueprint(
    'claro', __name__,
    url_prefix='/claro',
    template_folder='../templates',
    static_folder='../static'
)

# Ruta relativa al proyecto: sube desde blueprint -> Coltrade
PROJECT_DIR = Path(__file__).resolve().parent.parent
JSON_REL_PATH = Path("conexiones") / "data_ops" / "data_claro.json"
JSON_PATH = PROJECT_DIR / JSON_REL_PATH

_file_lock = Lock()

def _ensure_file():
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not JSON_PATH.exists():
        with JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def _normalize_key(val):
    if val is None:
        return ""
    return str(val).strip().lower()

def _clean_value(v):
    """
    Si v es None / cadena vacía / 'nan' / NaN => devolver 0.
    Si no, devolver el valor tal cual (preserva números y cadenas).
    """
    if v is None:
        return 0

    # valores numéricos NaN
    try:
        if isinstance(v, float) and math.isnan(v):
            return 0
        try:
            fv = float(v)
            if math.isnan(fv):
                return 0
        except Exception:
            pass
    except Exception:
        pass

    s = str(v).strip()
    if s == "" or s.lower() in ("nan", "none", "null"):
        return 0

    return v

def read_items():
    _ensure_file()
    with _file_lock:
        text = JSON_PATH.read_text(encoding="utf-8").strip()
        if not text:
            return []
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                items = [data]
            elif isinstance(data, list):
                items = data
            else:
                items = []
        except json.JSONDecodeError:
            # intentar parseo línea por línea (ndjson)
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
            items = res

        # Asegurar que cada item tenga un id único (compatibilidad con datos antiguos)
        changed = False
        for it in items:
            if "id" not in it or not it.get("id"):
                it["id"] = str(uuid.uuid4())
                changed = True
        # si agregamos ids a items existentes, reescribimos para persistirlos
        if changed:
            with JSON_PATH.open("w", encoding="utf-8") as f:
                json.dump(items, f, ensure_ascii=False, indent=2)
        return items

def write_items(list_items):
    _ensure_file()
    with _file_lock:
        with JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump(list_items, f, ensure_ascii=False, indent=2)

def find_by_material(material, items=None):
    if items is None:
        items = read_items()
    target = _normalize_key(material)
    for it in items:
        if _normalize_key(it.get("Material")) == target:
            return it
    return None

def find_index_by_id(item_id, items=None):
    if items is None:
        items = read_items()
    for idx, it in enumerate(items):
        if str(it.get("id")) == str(item_id):
            return idx
    return None

# Página principal
@claro_bp.route('/')
def index():
    return render_template('claro.html')

# API: listar
@claro_bp.route('/api/items', methods=['GET'])
def api_list_items():
    items = read_items()
    return jsonify(items), 200

# API: crear (ahora asigna id único y sigue rellenando 0 cuando falten valores)
@claro_bp.route('/api/items', methods=['POST'])
def api_create_item():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error":"Cuerpo inválido"}), 400

    material = str(payload.get("Material","")).strip()
    if not material:
        return jsonify({"error":"El campo 'Material' es obligatorio"}), 400

    new_obj = {
        "id": str(uuid.uuid4()),
        "Material": material,
        "Producto": _clean_value(payload.get("Producto","")),
        "Centro Costos": _clean_value(payload.get("Centro Costos","")),
        "Nombre del Punto": _clean_value(payload.get("Nombre del Punto","")),
        "Inventario Claro": _clean_value(payload.get("Inventario Claro","")),
        "Transito Claro": _clean_value(payload.get("Transito Claro","")),
        "Ventas Pasadas Claro": _clean_value(payload.get("Ventas Pasadas Claro","")),
        "Ventas Actuales Claro": _clean_value(payload.get("Ventas Actuales Claro","")),
        "Sugerido Claro": _clean_value(payload.get("Sugerido Claro",""))
    }
    items = read_items()
    items.append(new_obj)
    write_items(items)
    return jsonify(new_obj), 201

# API: actualizar por ID -> actualiza solo el item con ese id
@claro_bp.route('/api/items/<item_id>', methods=['PUT'])
def api_update_item(item_id):
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error":"Cuerpo inválido"}), 400

    items = read_items()
    idx = find_index_by_id(item_id, items)
    if idx is None:
        return jsonify({"error":"Item no encontrado"}), 404

    target = items[idx]

    new_material = str(payload.get("Material", target.get("Material"))).strip()
    if not new_material:
        return jsonify({"error":"El campo 'Material' no puede quedar vacío"}), 400

    # Actualizar campos (si vienen nulos -> almacenar 0)
    target["Material"] = new_material
    target["Producto"] = _clean_value(payload.get("Producto", target.get("Producto","")))
    target["Centro Costos"] = _clean_value(payload.get("Centro Costos", target.get("Centro Costos","")))
    target["Nombre del Punto"] = _clean_value(payload.get("Nombre del Punto", target.get("Nombre del Punto","")))
    for fld in ["Inventario Claro","Transito Claro","Ventas Pasadas Claro","Ventas Actuales Claro","Sugerido Claro"]:
        if fld in payload:
            target[fld] = _clean_value(payload.get(fld))
    items[idx] = target
    write_items(items)
    return jsonify(target), 200

# API: borrar uno por ID -> borra solo esa fila (la primera coincidencia por id)
@claro_bp.route('/api/items/<item_id>', methods=['DELETE'])
def api_delete_item(item_id):
    items = read_items()
    idx = find_index_by_id(item_id, items)
    if idx is None:
        return jsonify({"error":"Item no encontrado"}), 404
    # eliminar solo ese índice
    del items[idx]
    write_items(items)
    return jsonify({"ok":True}), 200

# API: borrar todo (confirmación triple desde frontend)
@claro_bp.route('/api/delete_all', methods=['POST'])
def api_delete_all():
    data = request.get_json(force=True) or {}
    confirmations = int(data.get("confirmaciones", 0))
    if confirmations < 3:
        return jsonify({"error":"Se requieren 3 confirmaciones para eliminar todos los datos", "confirmaciones_recibidas": confirmations}), 400
    write_items([])
    return jsonify({"ok":True, "deleted_all": True}), 200

# API: exportar (excel o json) - exporta todo y rellena NaN con 0
@claro_bp.route('/api/export', methods=['GET'])
def api_export():
    fmt = request.args.get("format", "excel").lower()
    items = read_items()

    df = pd.DataFrame(items)
    # Aseguramos columnas (incluimos id)
    cols = [
        "id","Material","Producto","Centro Costos","Nombre del Punto",
        "Inventario Claro","Transito Claro","Ventas Pasadas Claro",
        "Ventas Actuales Claro","Sugerido Claro"
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = 0
    df = df[cols]

    # rellenar NaN por 0 antes de exportar
    df = df.fillna(0)

    if fmt in ("excel","xlsx"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="ClaroData")
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="data_claro.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        mem = BytesIO()
        mem.write(json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"))
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name="data_claro.json", mimetype="application/json")

# API: importar (excel o json) -- IMPORTA TODO: no evita duplicados, agrega siempre los registros válidos
@claro_bp.route('/api/import', methods=['POST'])
def api_import():
    if 'file' not in request.files:
        return jsonify({"error":"No se encontró archivo en el formulario (campo 'file')"}), 400
    f = request.files['file']
    content = f.read()
    to_add = []

    try:
        # Intentar leer como Excel primero
        read_as_excel = False
        try:
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

            col_material = get_col(["Material","material","Mat","mat"])
            if not col_material:
                return jsonify({"error":"El archivo Excel debe tener una columna 'Material' (o similar)"}), 400

            col_producto = get_col(["Producto","producto","Prod","prod","Descripcion"])
            col_centro = get_col(["Centro Costos","Centro_Costos","centro costos","centro_costos","centro"])
            col_nombre = get_col(["Nombre del Punto","Nombre_del_Punto","Nombre","Punto","punto"])
            col_inv = get_col(["Inventario Claro","Inventario","Inventario_Claro","inventario claro"])
            col_transito = get_col(["Transito Claro","Transito","Transito_Claro","transito claro"])
            col_vpast = get_col(["Ventas Pasadas Claro","Ventas Pasadas","Ventas_Pasadas","ventas pasadas"])
            col_vactual = get_col(["Ventas Actuales Claro","Ventas Actuales","Ventas_Actuales","ventas actual"])
            col_sugerido = get_col(["Sugerido Claro","Sugerido","sugerido"])

            df[col_material] = df[col_material].astype(str).fillna("").str.strip()
            df[col_material] = df[col_material].str.replace(r'\.0+$', '', regex=True)

            for _, row in df.iterrows():
                material = str(row.get(col_material) or "").strip()
                if not material:
                    continue
                obj = {
                    "id": str(uuid.uuid4()),
                    "Material": material,
                    "Producto": _clean_value(row.get(col_producto) if col_producto else ""),
                    "Centro Costos": _clean_value(row.get(col_centro) if col_centro else ""),
                    "Nombre del Punto": _clean_value(row.get(col_nombre) if col_nombre else ""),
                    "Inventario Claro": _clean_value(row.get(col_inv) if col_inv else ""),
                    "Transito Claro": _clean_value(row.get(col_transito) if col_transito else ""),
                    "Ventas Pasadas Claro": _clean_value(row.get(col_vpast) if col_vpast else ""),
                    "Ventas Actuales Claro": _clean_value(row.get(col_vactual) if col_vactual else ""),
                    "Sugerido Claro": _clean_value(row.get(col_sugerido) if col_sugerido else "")
                }
                to_add.append(obj)
        else:
            s = content.decode("utf-8", errors="replace").strip()
            parsed = json.loads(s)
            if isinstance(parsed, dict):
                parsed_list = [parsed]
            elif isinstance(parsed, list):
                parsed_list = parsed
            else:
                return jsonify({"error":"Formato JSON inválido"}), 400

            norm = []
            for item in parsed_list:
                if not isinstance(item, dict):
                    continue
                material = str(item.get("Material") or item.get("material") or "").strip()
                if not material:
                    continue
                norm.append({
                    "id": str(uuid.uuid4()),
                    "Material": material,
                    "Producto": _clean_value((item.get("Producto") or item.get("producto") or "")),
                    "Centro Costos": _clean_value((item.get("Centro Costos") or item.get("centro_costos") or item.get("centro") or "")),
                    "Nombre del Punto": _clean_value((item.get("Nombre del Punto") or item.get("nombre_del_punto") or item.get("Nombre") or "")),
                    "Inventario Claro": _clean_value(item.get("Inventario Claro") or item.get("Inventario") or ""),
                    "Transito Claro": _clean_value(item.get("Transito Claro") or item.get("Transito") or ""),
                    "Ventas Pasadas Claro": _clean_value(item.get("Ventas Pasadas Claro") or item.get("Ventas_Pasadas") or ""),
                    "Ventas Actuales Claro": _clean_value(item.get("Ventas Actuales Claro") or item.get("Ventas_Actuales") or ""),
                    "Sugerido Claro": _clean_value(item.get("Sugerido Claro") or item.get("Sugerido") or "")
                })
            to_add = norm

    except json.JSONDecodeError as jde:
        return jsonify({"error":"JSON inválido", "detail": str(jde)}), 400
    except Exception as e:
        return jsonify({"error":"No se pudo parsear el archivo", "detail": str(e)}), 400

    # Agregamos todo lo válido
    items = read_items()
    added = 0
    added_materials = []
    for it in to_add:
        material_val = str(it.get("Material") or "").strip()
        if not material_val:
            continue
        items.append({
            "id": it.get("id") or str(uuid.uuid4()),
            "Material": material_val,
            "Producto": _clean_value(it.get("Producto","")),
            "Centro Costos": _clean_value(it.get("Centro Costos","")),
            "Nombre del Punto": _clean_value(it.get("Nombre del Punto","")),
            "Inventario Claro": _clean_value(it.get("Inventario Claro","")),
            "Transito Claro": _clean_value(it.get("Transito Claro","")),
            "Ventas Pasadas Claro": _clean_value(it.get("Ventas Pasadas Claro","")),
            "Ventas Actuales Claro": _clean_value(it.get("Ventas Actuales Claro","")),
            "Sugerido Claro": _clean_value(it.get("Sugerido Claro",""))
        })
        added += 1
        added_materials.append(material_val)

    write_items(items)
    return jsonify({"ok":True, "added": added, "added_materials": added_materials, "total_after": len(items)}), 200
