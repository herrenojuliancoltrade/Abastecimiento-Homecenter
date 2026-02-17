import json
from pathlib import Path
from threading import Lock
from flask import (
    Blueprint, render_template, jsonify, request, send_file
)
from io import BytesIO
import pandas as pd
import re
from datetime import datetime

inventario_bp = Blueprint(
    'inventario', __name__, url_prefix='/inventario',
    template_folder='../templates', static_folder='../static'
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
JSON_REL_PATH = Path("conexiones") / "data_ops" / "inventario_claro.json"
JSON_PATH = PROJECT_DIR / JSON_REL_PATH

# rutas relativas para validar existencia de productos y puntos de venta
PRODUCTOS_JSON_PATH = PROJECT_DIR / Path("conexiones") / "data_ops" / "productos_claro.json"
PUNTOS_JSON_PATH = PROJECT_DIR / Path("conexiones") / "data_ops" / "puntos_venta_claro.json"

_file_lock = Lock()

def _ensure_file(path=JSON_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def read_items():
    _ensure_file(JSON_PATH)
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

def write_items(list_items):
    _ensure_file(JSON_PATH)
    with _file_lock:
        with JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump(list_items, f, ensure_ascii=False, indent=2)

def normalize_item(raw):
    """
    Normaliza keys entrantes a:
    "Centro Costos", "Material", "Inventario"
    """
    if not isinstance(raw, dict):
        return None
    centro = raw.get("Centro Costos") or raw.get("centro costos") or raw.get("Centro") or raw.get("centro") or ""
    material = raw.get("Material") or raw.get("material") or ""
    inventario = raw.get("Inventario") or raw.get("inventario") or raw.get("Cantidad") or raw.get("cantidad") or 0
    # intentar convertir inventario a int si posible
    try:
        if isinstance(inventario, str):
            inventario = inventario.strip()
            inventario = int(float(inventario)) if inventario != "" else 0
        else:
            inventario = int(inventario)
    except Exception:
        inventario = 0
    return {
        "Centro Costos": str(centro).strip(),
        "Material": str(material).strip(),
        "Inventario": inventario
    }

# helper para leer JSON genérico (productos / puntos)
def _read_json(path: Path):
    _ensure_file(path)
    try:
        txt = path.read_text(encoding="utf-8").strip()
        if not txt:
            return []
        data = json.loads(txt)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data
        return []
    except Exception:
        # intentar newline-delimited
        res = []
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                res.append(json.loads(line))
            except Exception:
                continue
        return res

# --------- Canonicalización robusta ----------
def _canon_material_variants(value):
    """
    Devuelve un set de variantes canónicas para un material:
    - valor original string limpiado
    - solo dígitos (sin espacios, sin .0)
    - sin ceros a la izquierda
    """
    res = set()
    if value is None:
        return res
    s = str(value).strip()
    if not s:
        return res
    # original trimmed
    res.add(s)
    # extraer solo dígitos (si existen)
    digits = re.sub(r'\D', '', s)
    if digits:
        # quitar ceros a la izquierda
        nozeros = digits.lstrip('0') or '0'
        res.add(digits)
        res.add(nozeros)
    # si tiene decimal como '1234.0', también añadir parte entera
    m = re.match(r'^(\d+)\.0+$', s)
    if m:
        res.add(m.group(1))
    return set(x for x in res if x is not None and x != "")

def _canon_centro_variants(value):
    """
    Devuelve variantes canónicas para centro de costos:
    - uppercase, trimmed
    - quitar espacios y caracteres no alfanuméricos
    - si comienza con 'C' se añade variante sin 'C'
    - si es sólo dígitos, se añade con prefijo 'C'
    """
    res = set()
    if value is None:
        return res
    s = str(value).strip()
    if not s:
        return res
    # original uppercase trimmed
    s_up = s.upper()
    res.add(s_up)
    # solo alfanuméricos
    alnum = re.sub(r'[^A-Za-z0-9]', '', s_up)
    if alnum:
        res.add(alnum)
    # si empieza con C o c, variante sin C
    if alnum.upper().startswith('C') and len(alnum) > 1:
        without_c = alnum[1:]
        res.add(without_c)
    # si es solo dígitos, añade con prefijo C
    only_digits = re.sub(r'\D', '', s)
    if only_digits:
        res.add(only_digits)
        res.add(only_digits.lstrip('0') or '0')
        res.add('C' + only_digits)
    return set(x for x in res if x is not None and x != "")

# Cargar sets canónicos desde productos/puntos
def _load_existing_materials_canon():
    data = _read_json(PRODUCTOS_JSON_PATH)
    canon = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        mat = item.get("Material") or item.get("material") or ""
        for v in _canon_material_variants(mat):
            canon.add(v)
    return canon

def _load_existing_centros_canon():
    data = _read_json(PUNTOS_JSON_PATH)
    canon = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        # intentar varias keys: "Centro Costos", "Centro", "Punto de Venta"
        centro = item.get("Centro Costos") or item.get("Centro") or item.get("Punto de Venta") or item.get("punto de venta") or ""
        for v in _canon_centro_variants(centro):
            canon.add(v)
    return canon

# --------------------------------------------

@inventario_bp.route('/')
def index():
    return render_template('inventario.html')

# API: listar
@inventario_bp.route('/api/items', methods=['GET'])
def api_list_items():
    items = read_items()
    return jsonify(items), 200

# API: crear (permitir duplicados)
@inventario_bp.route('/api/items', methods=['POST'])
def api_create_item():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error": "Cuerpo inválido"}), 400
    item = normalize_item(payload)
    if not item or not item.get("Material"):
        return jsonify({"error": "El campo 'Material' es obligatorio"}), 400
    items = read_items()
    items.append(item)  # permitimos duplicados
    write_items(items)
    return jsonify(item), 201

# API: actualizar por índice (no usamos ID en los objetos)
@inventario_bp.route('/api/items/<int:index>', methods=['PUT'])
def api_update_item(index):
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error": "Cuerpo inválido"}), 400
    items = read_items()
    if index < 0 or index >= len(items):
        return jsonify({"error": "Registro no encontrado"}), 404
    new_item = normalize_item(payload)
    if not new_item or not new_item.get("Material"):
        return jsonify({"error": "El campo 'Material' es obligatorio"}), 400
    items[index] = new_item
    write_items(items)
    return jsonify(new_item), 200

# API: borrar uno por índice
@inventario_bp.route('/api/items/<int:index>', methods=['DELETE'])
def api_delete_item(index):
    items = read_items()
    if index < 0 or index >= len(items):
        return jsonify({"error": "Registro no encontrado"}), 404
    items.pop(index)
    write_items(items)
    return jsonify({"ok": True}), 200

# API: borrar todo (confirmación desde frontend)
@inventario_bp.route('/api/delete_all', methods=['POST'])
def api_delete_all():
    data = request.get_json(force=True) or {}
    confirmations = int(data.get("confirmaciones", 0))
    if confirmations < 3:
        return jsonify({"error": "Se requieren 3 confirmaciones para eliminar todos los datos", "confirmaciones_recibidas": confirmations}), 400
    write_items([])
    return jsonify({"ok": True, "deleted_all": True}), 200

# API: exportar (Excel o JSON) - actualizado para incluir timestamp en el nombre de archivo
@inventario_bp.route('/api/export', methods=['GET'])
def api_export():
    fmt = request.args.get("format", "excel").lower()
    items = read_items()
    df = pd.DataFrame(items)
    for c in ["Centro Costos", "Material", "Inventario"]:
        if c not in df.columns:
            df[c] = ""
    df = df[["Centro Costos", "Material", "Inventario"]]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if fmt in ("excel", "xlsx"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Inventario")
        output.seek(0)
        filename = f"inventario_claro_{ts}.xlsx"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        mem = BytesIO()
        mem.write(json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"))
        mem.seek(0)
        filename = f"inventario_claro_{ts}.json"
        return send_file(mem, as_attachment=True, download_name=filename, mimetype="application/json")

# API: importar (Excel o JSON)
@inventario_bp.route('/api/import', methods=['POST'])
def api_import():
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró archivo en el formulario (campo 'file')"}), 400
    f = request.files['file']
    filename = (f.filename or "").lower()
    content = f.read()
    to_add = []
    try:
        if filename.endswith(('.xls', '.xlsx')) or content[:4] == b'PK\x03\x04':
            # Excel
            try:
                df = pd.read_excel(BytesIO(content), dtype=str)
            except Exception as e:
                return jsonify({"error": "No se pudo leer el archivo Excel", "detail": str(e)}), 400
            df.columns = [str(c).strip() for c in df.columns]
            lower_map = {c.lower(): c for c in df.columns}
            def get_col(possible):
                for opt in possible:
                    lo = opt.lower()
                    if lo in lower_map:
                        return lower_map[lo]
                return None
            col_centro = get_col(["Centro Costos", "Centro", "centro costos", "centro"])
            col_material = get_col(["Material", "material", "MATERIAL"])
            col_invent = get_col(["Inventario", "inventario", "Cantidad", "cantidad", "Qty", "qty"])
            if not col_material:
                return jsonify({"error": "El archivo Excel debe tener una columna 'Material'"}), 400
            for _, row in df.iterrows():
                centro = str(row.get(col_centro) or "").strip() if col_centro else ""
                material = str(row.get(col_material) or "").strip()
                invent = row.get(col_invent) if col_invent else 0
                try:
                    invent = int(float(str(invent))) if str(invent).strip() != "" else 0
                except Exception:
                    invent = 0
                to_add.append({
                    "Centro Costos": centro,
                    "Material": material,
                    "Inventario": invent
                })
        else:
            s = content.decode("utf-8", errors="replace").strip()
            parsed = json.loads(s)
            if isinstance(parsed, dict):
                if "Material" in parsed or "material" in parsed:
                    to_add = [parsed]
                else:
                    return jsonify({"error": "Formato JSON inválido (falta 'Material')"}), 400
            elif isinstance(parsed, list):
                to_add = parsed
            else:
                return jsonify({"error": "Formato JSON inválido"}), 400
        # Normalizar y agregar (permitir duplicados)
        norm = []
        for item in to_add:
            n = normalize_item(item)
            if not n or not n.get("Material"):
                continue
            norm.append(n)
        items = read_items()
        items.extend(norm)
        write_items(items)
        return jsonify({"ok": True, "added": len(norm), "total_after": len(items)}), 200
    except Exception as e:
        return jsonify({"error": "No se pudo parsear el archivo", "detail": str(e)}), 400

# Nuevo endpoint: devuelve los pendientes únicos escaneando todo el inventario
@inventario_bp.route('/api/pending', methods=['GET'])
def api_pending():
    items = read_items()
    existing_materials_canon = _load_existing_materials_canon()
    existing_centros_canon = _load_existing_centros_canon()
    missing_materials_set = set()
    missing_centros_set = set()

    for it in items:
        mat_raw = str(it.get("Material") or "").strip()
        cen_raw = str(it.get("Centro Costos") or "").strip()

        # Si el material no tiene representación canónica en existing -> pendiente
        mat_variants = _canon_material_variants(mat_raw)
        if mat_raw and not (mat_variants & existing_materials_canon):
            missing_materials_set.add(mat_raw)

        cen_variants = _canon_centro_variants(cen_raw)
        if cen_raw and not (cen_variants & existing_centros_canon):
            missing_centros_set.add(cen_raw)

    return jsonify({
        "missing_materials": sorted(list(missing_materials_set)),
        "missing_centros": sorted(list(missing_centros_set))
    }), 200
