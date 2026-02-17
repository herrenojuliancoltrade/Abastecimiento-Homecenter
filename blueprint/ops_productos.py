# blueprint/ops_productos.py
import json
from pathlib import Path
from threading import Lock
from flask import (
    Blueprint, render_template, jsonify, request, send_file,
    make_response
)
from io import BytesIO
import pandas as pd

opsproductos_bp = Blueprint(
    'opsproductos', __name__,
    url_prefix='/opsproductos',
    template_folder='../templates',
    static_folder='../static'
)

# Ruta relativa al archivo JSON (resuelta desde la ubicación de este archivo)
PROJECT_DIR = Path(__file__).resolve().parent.parent  # sube: blueprint -> Coltrade
JSON_REL_PATH = Path("conexiones") / "data_ops" / "productos_claro.json"
JSON_PATH = PROJECT_DIR / JSON_REL_PATH

_file_lock = Lock()

def _ensure_file():
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not JSON_PATH.exists():
        with JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def read_products():
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

def write_products(list_products):
    _ensure_file()
    with _file_lock:
        with JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump(list_products, f, ensure_ascii=False, indent=2)

def find_by_material(material, products=None):
    if products is None:
        products = read_products()
    for p in products:
        if str(p.get("Material")) == str(material):
            return p
    return None

@opsproductos_bp.route('/')
def index():
    return render_template('opsproductos.html')

# API: listar
@opsproductos_bp.route('/api/products', methods=['GET'])
def api_list_products():
    products = read_products()
    return jsonify(products), 200

# API: crear
@opsproductos_bp.route('/api/products', methods=['POST'])
def api_create_product():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error":"Cuerpo inválido"}), 400
    material = str(payload.get("Material", "")).strip()
    if not material:
        return jsonify({"error":"El campo 'Material' es obligatorio"}), 400

    products = read_products()
    if find_by_material(material, products):
        return jsonify({"error":"Ya existe un producto con ese Material", "code":"duplicate"}), 409

    new_obj = {
        "Material": material,
        "Producto": payload.get("Producto", ""),
        "Marca": payload.get("Marca", "")
    }
    products.append(new_obj)
    write_products(products)
    return jsonify(new_obj), 201

# API: actualizar (editar) por material (clave)
@opsproductos_bp.route('/api/products/<material>', methods=['PUT'])
def api_update_product(material):
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error":"Cuerpo inválido"}), 400
    material = str(material)
    products = read_products()
    target = find_by_material(material, products)
    if not target:
        return jsonify({"error":"Producto no encontrado"}), 404

    new_material = str(payload.get("Material", material)).strip()
    if new_material != material:
        if find_by_material(new_material, products):
            return jsonify({"error":"No se puede cambiar Material, ya existe otro registro con ese número"}), 409

    target["Material"] = new_material
    target["Producto"] = payload.get("Producto", target.get("Producto", ""))
    target["Marca"] = payload.get("Marca", target.get("Marca", ""))
    write_products(products)
    return jsonify(target), 200

# API: borrar uno
@opsproductos_bp.route('/api/products/<material>', methods=['DELETE'])
def api_delete_product(material):
    material = str(material)
    products = read_products()
    new_list = [p for p in products if str(p.get("Material")) != material]
    if len(new_list) == len(products):
        return jsonify({"error":"Producto no encontrado"}), 404
    write_products(new_list)
    return jsonify({"ok":True}), 200

# API: borrar todo (requiere confirmar 3 veces en frontend)
@opsproductos_bp.route('/api/delete_all', methods=['POST'])
def api_delete_all():
    data = request.get_json(force=True) or {}
    confirmations = int(data.get("confirmaciones", 0))
    if confirmations < 3:
        return jsonify({"error":"Se requieren 3 confirmaciones para eliminar todos los datos", "confirmaciones_recibidas": confirmations}), 400
    write_products([])
    return jsonify({"ok":True, "deleted_all": True}), 200

# API: exportar (Excel o JSON)
@opsproductos_bp.route('/api/export', methods=['GET'])
def api_export():
    fmt = request.args.get("format", "excel").lower()
    products = read_products()

    # Normalizar estructura a DataFrame
    df = pd.DataFrame(products)
    # asegurar columnas
    for c in ["Material","Producto","Marca"]:
        if c not in df.columns:
            df[c] = ""

    df = df[["Material","Producto","Marca"]]

    if fmt in ("excel","xlsx"):
        output = BytesIO()
        # Exportar a Excel sin índice
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Productos")
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="productos_claro.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        # exportar JSON por compatibilidad
        mem = BytesIO()
        mem.write(json.dumps(products, ensure_ascii=False, indent=2).encode("utf-8"))
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name="productos_claro.json", mimetype="application/json")

# API: importar (subir EXCEL o JSON)
@opsproductos_bp.route('/api/import', methods=['POST'])
def api_import():
    """
    Espera multipart/form-data con archivo en campo 'file'.
    Si es Excel (.xlsx/.xls), se buscan columnas Material,Producto,Marca.
    Si es JSON, espera una lista de objetos o un único objeto.
    Se importan y se ignoran duplicados por 'Material' (no se sobrescriben).
    Devuelve resumen.
    """
    if 'file' not in request.files:
        return jsonify({"error":"No se encontró archivo en el formulario (campo 'file')"}), 400
    f = request.files['file']
    filename = (f.filename or "").lower()
    content = f.read()
    to_add = []

    try:
        # Excel
        if filename.endswith(('.xls','.xlsx')) or content[:4] == b'PK\x03\x04':
            # pandas read excel
            try:
                # intentar detectar con pandas
                df = pd.read_excel(BytesIO(content), dtype=str)
            except Exception as e:
                return jsonify({"error":"No se pudo leer el archivo Excel", "detail": str(e)}), 400

            # normalizar nombres de columnas (lower)
            df.columns = [str(c).strip() for c in df.columns]
            lower_map = {c.lower(): c for c in df.columns}
            # buscar las columnas por nombre similar
            def get_col(possible):
                for opt in possible:
                    lo = opt.lower()
                    if lo in lower_map:
                        return lower_map[lo]
                return None

            col_material = get_col(["Material","material","MATERIAL"])
            col_producto = get_col(["Producto","producto","PRODUCTO","Descripcion","descripcion"])
            col_marca = get_col(["Marca","marca","MARCA","Brand","brand"])

            if not col_material:
                return jsonify({"error":"El archivo Excel debe tener una columna 'Material'"}), 400

            # asegurar strings y limpiar Material de .0 si pandas lo convierte
            df[col_material] = df[col_material].astype(str).fillna("").str.strip()
            df[col_material] = df[col_material].str.replace(r'\.0+$', '', regex=True)

            for _, row in df.iterrows():
                material = str(row.get(col_material) or "").strip()
                if not material:
                    continue
                producto = str(row.get(col_producto) or "").strip() if col_producto else ""
                marca = str(row.get(col_marca) or "").strip() if col_marca else ""
                to_add.append({"Material": material, "Producto": producto, "Marca": marca})

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

            # normalizar
            norm = []
            for item in to_add:
                if not isinstance(item, dict):
                    continue
                material = str(item.get("Material") or item.get("material") or "").strip()
                if not material:
                    continue
                norm.append({
                    "Material": material,
                    "Producto": item.get("Producto") or item.get("producto") or "",
                    "Marca": item.get("Marca") or item.get("marca") or ""
                })
            to_add = norm

    except Exception as e:
        return jsonify({"error":"No se pudo parsear el archivo", "detail": str(e)}), 400

    # merge y evitar duplicados por 'Material'
    products = read_products()
    existing_materials = {str(p.get("Material")) for p in products}
    added = 0
    for item in to_add:
        if str(item.get("Material")) in existing_materials:
            continue
        products.append(item)
        existing_materials.add(str(item.get("Material")))
        added += 1
    write_products(products)
    return jsonify({"ok":True, "added": added, "total_after": len(products)}), 200
