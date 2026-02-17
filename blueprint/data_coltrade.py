# blueprint/data_coltrade.py
import json
import math
import uuid
from pathlib import Path
from threading import Lock
from flask import Blueprint, render_template, jsonify, request, send_file
from io import BytesIO
import pandas as pd

coltrade_bp = Blueprint(
    'coltrade', __name__,
    url_prefix='/coltrade',
    template_folder='../templates',
    static_folder='../static'
)

# Ruta relativa al proyecto (desde blueprint -> Coltrade)
PROJECT_DIR = Path(__file__).resolve().parent.parent
JSON_REL_PATH = Path("conexiones") / "data_ops" / "data_coltrade.json"
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
    Si no, devolver el valor tal cual (preserva tipos cuando es posible).
    """
    if v is None:
        return 0

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

        # Asegurar id único para compatibilidad con datos antiguos
        changed = False
        for it in items:
            if "id" not in it or not it.get("id"):
                it["id"] = str(uuid.uuid4())
                changed = True
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
@coltrade_bp.route('/')
def index():
    return render_template('coltrade.html')

# API: listar
@coltrade_bp.route('/api/items', methods=['GET'])
def api_list_items():
    items = read_items()
    return jsonify(items), 200

# API: crear (POST) - ahora asigna id único
@coltrade_bp.route('/api/items', methods=['POST'])
def api_create_item():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error":"Cuerpo inválido"}), 400

    material = str(payload.get("Material","")).strip()
    if not material:
        return jsonify({"error":"El campo 'Material' es obligatorio"}), 400

    new_obj = {
        "id": str(uuid.uuid4()),
        "Centro Costos": _clean_value(payload.get("Centro Costos","")),
        "Punto de Venta": _clean_value(payload.get("Punto de Venta","")),
        "Material": material,
        "Producto": _clean_value(payload.get("Producto","")),
        "Marca": _clean_value(payload.get("Marca","")),
        "Ventas Actuales": _clean_value(payload.get("Ventas Actuales","")),
        "Transitos": _clean_value(payload.get("Transitos","")),
        "Inventario": _clean_value(payload.get("Inventario","")),
        "Envío Inventario 3 meses": _clean_value(payload.get("Envío Inventario 3 meses","")),
        "Sugerido Coltrade": _clean_value(payload.get("Sugerido Coltrade",""))
    }

    items = read_items()
    items.append(new_obj)
    write_items(items)
    return jsonify(new_obj), 201

# API: actualizar (PUT) por ID -> actualiza solo el registro con ese id
@coltrade_bp.route('/api/items/<item_id>', methods=['PUT'])
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

    target["Centro Costos"] = _clean_value(payload.get("Centro Costos", target.get("Centro Costos","")))
    target["Punto de Venta"] = _clean_value(payload.get("Punto de Venta", target.get("Punto de Venta","")))
    target["Material"] = new_material
    target["Producto"] = _clean_value(payload.get("Producto", target.get("Producto","")))
    target["Marca"] = _clean_value(payload.get("Marca", target.get("Marca","")))
    for fld in ["Ventas Actuales","Transitos","Inventario","Envío Inventario 3 meses","Sugerido Coltrade"]:
        if fld in payload:
            target[fld] = _clean_value(payload.get(fld))
    items[idx] = target
    write_items(items)
    return jsonify(target), 200

# API: borrar por ID -> elimina solo ese registro
@coltrade_bp.route('/api/items/<item_id>', methods=['DELETE'])
def api_delete_item(item_id):
    items = read_items()
    idx = find_index_by_id(item_id, items)
    if idx is None:
        return jsonify({"error":"Item no encontrado"}), 404
    del items[idx]
    write_items(items)
    return jsonify({"ok":True}), 200

# API: borrar todo (requiere confirmaciones desde frontend)
@coltrade_bp.route('/api/delete_all', methods=['POST'])
def api_delete_all():
    data = request.get_json(force=True) or {}
    confirmations = int(data.get("confirmaciones", 0))
    if confirmations < 3:
        return jsonify({"error":"Se requieren 3 confirmaciones para eliminar todos los datos", "confirmaciones_recibidas": confirmations}), 400
    write_items([])
    return jsonify({"ok":True, "deleted_all": True}), 200

# API: exportar (Excel o JSON) - exporta todo (incluye id)
@coltrade_bp.route('/api/export', methods=['GET'])
def api_export():
    fmt = request.args.get("format", "excel").lower()
    items = read_items()

    df = pd.DataFrame(items)
    cols = [
        "id","Centro Costos","Punto de Venta","Material","Producto","Marca",
        "Ventas Actuales","Transitos","Inventario","Envío Inventario 3 meses","Sugerido Coltrade"
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = 0
    df = df[cols]
    df = df.fillna(0)

    if fmt in ("excel","xlsx"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="ColtradeData")
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="data_coltrade.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        mem = BytesIO()
        mem.write(json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"))
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name="data_coltrade.json", mimetype="application/json")

# API: importar (Excel o JSON) -> agrega registros con id nuevo
@coltrade_bp.route('/api/import', methods=['POST'])
def api_import():
    if 'file' not in request.files:
        return jsonify({"error":"No se encontró archivo en el formulario (campo 'file')"}), 400
    f = request.files['file']
    content = f.read()
    to_add = []

    try:
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

            col_centro = get_col(["Centro Costos","Centro_Costos","centro costos","centro_costos","centro"])
            col_punto = get_col(["Punto de Venta","Punto_de_Venta","punto de venta","punto_venta","Punto","punto"])
            col_material = get_col(["Material","material","Mat","mat"])
            col_producto = get_col(["Producto","producto","Prod","prod","Descripcion"])
            col_marca = get_col(["Marca","marca","Brand","brand"])
            col_vactual = get_col(["Ventas Actuales","Ventas_Actuales","ventas actuales","ventas_actuales"])
            col_transitos = get_col(["Transitos","Transitos Claro","Transito","transitos","Transito"])
            col_inventario = get_col(["Inventario","Inventario Claro","inventario"])
            col_envio3 = get_col(["Envío Inventario 3 meses","Envio Inventario 3 meses","Envío_Inventario_3_meses","envio 3 meses","envio_3_meses"])
            col_sugerido = get_col(["Sugerido Coltrade","Sugerido","sugerido","Sugerido_Coltrade"])

            if not col_material:
                return jsonify({"error":"El archivo Excel debe tener una columna 'Material' (o similar)"}), 400

            df[col_material] = df[col_material].astype(str).fillna("").str.strip()
            df[col_material] = df[col_material].str.replace(r'\.0+$', '', regex=True)

            for _, row in df.iterrows():
                material = str(row.get(col_material) or "").strip()
                if not material:
                    continue
                obj = {
                    "id": str(uuid.uuid4()),
                    "Centro Costos": _clean_value(row.get(col_centro) if col_centro else ""),
                    "Punto de Venta": _clean_value(row.get(col_punto) if col_punto else ""),
                    "Material": material,
                    "Producto": _clean_value(row.get(col_producto) if col_producto else ""),
                    "Marca": _clean_value(row.get(col_marca) if col_marca else ""),
                    "Ventas Actuales": _clean_value(row.get(col_vactual) if col_vactual else ""),
                    "Transitos": _clean_value(row.get(col_transitos) if col_transitos else ""),
                    "Inventario": _clean_value(row.get(col_inventario) if col_inventario else ""),
                    "Envío Inventario 3 meses": _clean_value(row.get(col_envio3) if col_envio3 else ""),
                    "Sugerido Coltrade": _clean_value(row.get(col_sugerido) if col_sugerido else "")
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
                    "Centro Costos": _clean_value(str(item.get("Centro Costos") or item.get("centro_costos") or item.get("centro") or "")),
                    "Punto de Venta": _clean_value(str(item.get("Punto de Venta") or item.get("punto_de_venta") or item.get("punto") or "")),
                    "Material": material,
                    "Producto": _clean_value(str(item.get("Producto") or item.get("producto") or "")),
                    "Marca": _clean_value(str(item.get("Marca") or item.get("marca") or "")),
                    "Ventas Actuales": _clean_value(item.get("Ventas Actuales") or item.get("ventas_actuales") or ""),
                    "Transitos": _clean_value(item.get("Transitos") or item.get("Transito") or ""),
                    "Inventario": _clean_value(item.get("Inventario") or ""),
                    "Envío Inventario 3 meses": _clean_value(item.get("Envío Inventario 3 meses") or item.get("Envio Inventario 3 meses") or ""),
                    "Sugerido Coltrade": _clean_value(item.get("Sugerido Coltrade") or item.get("Sugerido") or "")
                })
            to_add = norm

    except json.JSONDecodeError as jde:
        return jsonify({"error":"JSON inválido", "detail": str(jde)}), 400
    except Exception as e:
        return jsonify({"error":"No se pudo parsear el archivo", "detail": str(e)}), 400

    items = read_items()
    added = 0
    added_materials = []
    for it in to_add:
        material_val = str(it.get("Material") or "").strip()
        if not material_val:
            continue
        items.append({
            "id": it.get("id") or str(uuid.uuid4()),
            "Centro Costos": _clean_value(it.get("Centro Costos","")),
            "Punto de Venta": _clean_value(it.get("Punto de Venta","")),
            "Material": material_val,
            "Producto": _clean_value(it.get("Producto","")),
            "Marca": _clean_value(it.get("Marca","")),
            "Ventas Actuales": _clean_value(it.get("Ventas Actuales","")),
            "Transitos": _clean_value(it.get("Transitos","")),
            "Inventario": _clean_value(it.get("Inventario","")),
            "Envío Inventario 3 meses": _clean_value(it.get("Envío Inventario 3 meses","")),
            "Sugerido Coltrade": _clean_value(it.get("Sugerido Coltrade",""))
        })
        added += 1
        added_materials.append(material_val)

    write_items(items)
    return jsonify({"ok":True, "added": added, "added_materials": added_materials, "total_after": len(items)}), 200
