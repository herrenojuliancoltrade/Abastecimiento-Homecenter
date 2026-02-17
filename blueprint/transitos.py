# blueprint/transitos.py
import json
from pathlib import Path
from threading import Lock
from flask import Blueprint, render_template, jsonify, request, send_file
from io import BytesIO
import pandas as pd

transitos_bp = Blueprint(
    'transitos', __name__, url_prefix='/transitos',
    template_folder='../templates', static_folder='../static'
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
JSON_REL_PATH = Path("conexiones") / "data_ops" / "transitos.json"
JSON_PATH = PROJECT_DIR / JSON_REL_PATH
# rutas relativas adicionales para validar existencia (productos y puntos)
PRODUCTOS_JSON_PATH = PROJECT_DIR / Path("conexiones") / "data_ops" / "productos_claro.json"
PUNTOS_JSON_PATH = PROJECT_DIR / Path("conexiones") / "data_ops" / "puntos_venta_claro.json"

_file_lock = Lock()

def _ensure_file():
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not JSON_PATH.exists():
        with JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def _read_json(path: Path):
    """
    Lee un JSON que puede ser lista, objeto o line-delimited.
    Devuelve lista de objetos.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8").strip()
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
                    res.append(json.loads(line))
                except Exception:
                    continue
            return res
    except Exception:
        return []

def read_transitos():
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

def write_transitos(list_items):
    _ensure_file()
    with _file_lock:
        with JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump(list_items, f, ensure_ascii=False, indent=2)

def normalize_entry(raw):
    """
    Normaliza keys a: "Centro Costos", "Material", "Transitos"
    """
    if not isinstance(raw, dict):
        return None
    centro = raw.get("Centro Costos") or raw.get("centro costos") or raw.get("Centro") or raw.get("centro") or ""
    material = raw.get("Material") or raw.get("material") or ""
    transitos = raw.get("Transitos") or raw.get("transitos") or raw.get("Cantidad") or raw.get("cantidad") or 0
    try:
        if isinstance(transitos, str):
            transitos = transitos.strip()
            transitos = int(float(transitos)) if transitos != "" else 0
        else:
            transitos = int(transitos)
    except Exception:
        transitos = 0
    return {
        "Centro Costos": str(centro).strip(),
        "Material": str(material).strip(),
        "Transitos": transitos
    }

# helpers para validar existencia (productos y puntos)
def _load_existing_materials():
    data = _read_json(PRODUCTOS_JSON_PATH)
    # los archivos de productos pueden tener objetos con key "Material"
    mats = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        m = item.get("Material") or item.get("material") or ""
        if m is not None:
            mm = str(m).strip()
            if mm:
                mats.add(mm)
    return mats

def _load_existing_centros():
    data = _read_json(PUNTOS_JSON_PATH)
    cents = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        # algunos JSON usan "Centro Costos" o "Centro"
        c = item.get("Centro Costos") or item.get("Centro") or item.get("centro") or item.get("Centro Cost") or ""
        if c is not None:
            cc = str(c).strip()
            if cc:
                cents.add(cc)
    return cents

@transitos_bp.route('/')
def index():
    return render_template('transitos.html')

# API: listar
@transitos_bp.route('/api/items', methods=['GET'])
def api_list():
    items = read_transitos()
    return jsonify(items), 200

# API: crear (permitir duplicados)
@transitos_bp.route('/api/items', methods=['POST'])
def api_create():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error": "Cuerpo inválido"}), 400
    entry = normalize_entry(payload)
    if not entry or not entry.get("Material"):
        return jsonify({"error": "El campo 'Material' es obligatorio"}), 400
    items = read_transitos()
    items.append(entry)
    write_transitos(items)
    return jsonify(entry), 201

# API: actualizar por índice
@transitos_bp.route('/api/items/<int:index>', methods=['PUT'])
def api_update(index):
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error": "Cuerpo inválido"}), 400
    items = read_transitos()
    if index < 0 or index >= len(items):
        return jsonify({"error": "Registro no encontrado"}), 404
    new_entry = normalize_entry(payload)
    if not new_entry or not new_entry.get("Material"):
        return jsonify({"error": "El campo 'Material' es obligatorio"}), 400
    items[index] = new_entry
    write_transitos(items)
    return jsonify(new_entry), 200

# API: borrar uno por índice
@transitos_bp.route('/api/items/<int:index>', methods=['DELETE'])
def api_delete(index):
    items = read_transitos()
    if index < 0 or index >= len(items):
        return jsonify({"error": "Registro no encontrado"}), 404
    items.pop(index)
    write_transitos(items)
    return jsonify({"ok": True}), 200

# API: borrar todo (requiere 3 confirmaciones desde frontend)
@transitos_bp.route('/api/delete_all', methods=['POST'])
def api_delete_all():
    data = request.get_json(force=True) or {}
    confirmations = int(data.get("confirmaciones", 0))
    if confirmations < 3:
        return jsonify({"error": "Se requieren 3 confirmaciones para eliminar todos los datos", "confirmaciones_recibidas": confirmations}), 400
    write_transitos([])
    return jsonify({"ok": True, "deleted_all": True}), 200

# API: exportar (Excel o JSON)
@transitos_bp.route('/api/export', methods=['GET'])
def api_export():
    fmt = request.args.get("format", "excel").lower()
    items = read_transitos()
    df = pd.DataFrame(items)
    for c in ["Centro Costos", "Material", "Transitos"]:
        if c not in df.columns:
            df[c] = ""
    df = df[["Centro Costos", "Material", "Transitos"]]
    if fmt in ("excel", "xlsx"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Transitos")
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="transitos.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        mem = BytesIO()
        mem.write(json.dumps(items, ensure_ascii=False, indent=2).encode("utf-8"))
        mem.seek(0)
        return send_file(mem, as_attachment=True, download_name="transitos.json", mimetype="application/json")

# API: importar (Excel o JSON)
@transitos_bp.route('/api/import', methods=['POST'])
def api_import():
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró archivo en el formulario (campo 'file')"}), 400
    f = request.files['file']
    filename = (f.filename or "").lower()
    content = f.read()
    to_add = []
    try:
        if filename.endswith(('.xls', '.xlsx')) or content[:4] == b'PK\x03\x04':
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
            col_trans = get_col(["Transitos", "transitos", "Cantidad", "cantidad", "Qty", "qty"])
            if not col_material:
                return jsonify({"error": "El archivo Excel debe tener una columna 'Material'"}), 400
            for _, row in df.iterrows():
                centro = str(row.get(col_centro) or "").strip() if col_centro else ""
                material = str(row.get(col_material) or "").strip()
                trans = row.get(col_trans) if col_trans else 0
                try:
                    trans = int(float(str(trans))) if str(trans).strip() != "" else 0
                except Exception:
                    trans = 0
                to_add.append({
                    "Centro Costos": centro,
                    "Material": material,
                    "Transitos": trans
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
        norm = []
        for item in to_add:
            n = normalize_entry(item)
            if not n or not n.get("Material"):
                continue
            norm.append(n)
        items = read_transitos()
        items.extend(norm)
        write_transitos(items)
        return jsonify({"ok": True, "added": len(norm), "total_after": len(items)}), 200
    except Exception as e:
        return jsonify({"error": "No se pudo parsear el archivo", "detail": str(e)}), 400

# Nuevo endpoint: devuelve los pendientes únicos escaneando todos los registros actuales
@transitos_bp.route('/api/pending', methods=['GET'])
def api_pending():
    items = read_transitos()
    existing_materials = _load_existing_materials()
    existing_centros = _load_existing_centros()
    missing_materials_set = set()
    missing_centros_set = set()
    for v in items:
        if not isinstance(v, dict):
            continue
        mat = str(v.get("Material") or "").strip()
        cen = str(v.get("Centro Costos") or "").strip()
        if mat and mat not in existing_materials:
            missing_materials_set.add(mat)
        if cen and cen not in existing_centros:
            missing_centros_set.add(cen)
    return jsonify({
        "missing_materials": sorted(list(missing_materials_set)),
        "missing_centros": sorted(list(missing_centros_set))
    }), 200
