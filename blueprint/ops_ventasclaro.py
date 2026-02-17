import json
from pathlib import Path
from threading import Lock
from flask import Blueprint, render_template, jsonify, request, send_file
from io import BytesIO
import pandas as pd
from datetime import datetime, date
import time

ventasclaro_bp = Blueprint(
    'ventasclaro', __name__,
    url_prefix='/ventasclaro',
    template_folder='../templates',
    static_folder='../static'
)

PROJECT_DIR = Path(__file__).resolve().parent.parent
JSON_REL_PATH = Path("conexiones") / "data_ops" / "ventas_claro.json"
JSON_PATH = PROJECT_DIR / JSON_REL_PATH

# rutas relativas adicionales para validar existencia
PRODUCTOS_JSON_PATH = PROJECT_DIR / Path("conexiones") / "data_ops" / "productos_claro.json"
PUNTOS_JSON_PATH = PROJECT_DIR / Path("conexiones") / "data_ops" / "puntos_venta_claro.json"

_file_lock = Lock()
_import_lock = Lock()
_last_import_time = 0
_import_cooldown = 30  # 30 segundos de espera

def _ensure_file(path=JSON_PATH):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def _normalize_date_str(s):
    if s is None:
        return ""
    s = str(s).strip()
    if not s:
        return ""
    for fmt in ("%Y-%m-%d","%d/%m/%Y","%d-%m-%Y","%Y/%m/%d","%m/%d/%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            continue
    return s

def _read_json(path):
    _ensure_file(path)
    try:
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            return []
        data = json.loads(text)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data
        return []
    except Exception:
        res = []
        raw = path.read_text(encoding="utf-8", errors="ignore")
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                res.append(json.loads(line))
            except Exception:
                continue
        return res

def read_ventas():
    _ensure_file(JSON_PATH)
    with _file_lock:
        text = JSON_PATH.read_text(encoding="utf-8").strip()
        if not text:
            return []
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                objs = [data]
            elif isinstance(data, list):
                objs = data
            else:
                return []
            clean = []
            for o in objs:
                if not isinstance(o, dict):
                    continue
                centro = str(o.get("Centro Costos") or o.get("centro_costos") or o.get("centro") or "").strip()
                material = str(o.get("Material") or o.get("material") or "").strip()
                fecha = _normalize_date_str(o.get("Fecha Venta") or o.get("fecha_venta") or o.get("fecha") or "")
                cantidad_raw = o.get("Cantidad", 0)
                try:
                    if cantidad_raw is None or cantidad_raw == "":
                        cantidad = 0
                    else:
                        if isinstance(cantidad_raw, (int, float)):
                            cantidad = cantidad_raw
                        else:
                            cantidad = float(str(cantidad_raw).strip())
                            if float(cantidad).is_integer():
                                cantidad = int(cantidad)
                except Exception:
                    cantidad = 0
                if centro == "" and material == "":
                    continue
                clean.append({
                    "Centro Costos": centro,
                    "Material": material,
                    "Fecha Venta": fecha,
                    "Cantidad": cantidad
                })
            return clean
        except json.JSONDecodeError:
            res = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                centro = str(o.get("Centro Costos") or o.get("centro_costos") or o.get("centro") or "").strip()
                material = str(o.get("Material") or o.get("material") or "").strip()
                fecha = _normalize_date_str(o.get("Fecha Venta") or o.get("fecha_venta") or o.get("fecha") or "")
                cantidad_raw = o.get("Cantidad", 0)
                try:
                    if cantidad_raw is None or cantidad_raw == "":
                        cantidad = 0
                    else:
                        if isinstance(cantidad_raw, (int, float)):
                            cantidad = cantidad_raw
                        else:
                            cantidad = float(str(cantidad_raw).strip())
                            if float(cantidad).is_integer():
                                cantidad = int(cantidad)
                except Exception:
                    cantidad = 0
                if centro == "" and material == "":
                    continue
                res.append({
                    "Centro Costos": centro,
                    "Material": material,
                    "Fecha Venta": fecha,
                    "Cantidad": cantidad
                })
            return res

def write_ventas(list_ventas):
    _ensure_file(JSON_PATH)
    with _file_lock:
        with JSON_PATH.open("w", encoding="utf-8") as f:
            json.dump(list_ventas, f, ensure_ascii=False, indent=2)

# helpers para validar existencia
def _load_existing_materials():
    data = _read_json(PRODUCTOS_JSON_PATH)
    return { str(item.get("Material") or "").strip() for item in data if item }

def _load_existing_centros():
    data = _read_json(PUNTOS_JSON_PATH)
    return { str(item.get("Centro Costos") or item.get("Centro") or "").strip() for item in data if item }

# util for parsing normalized date to datetime.date
def _parse_norm_date_to_date(norm):
    if not norm:
        return None
    try:
        return datetime.strptime(norm, "%Y-%m-%d").date()
    except Exception:
        return None

# Spanish month names
SPANISH_MONTHS = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

@ventasclaro_bp.route('/')
def index():
    return render_template('ventasclaro.html')

# Listar
@ventasclaro_bp.route('/api/ventas', methods=['GET'])
def api_list_ventas():
    ventas = read_ventas()
    return jsonify(ventas), 200

# Crear (añade al final) - devuelve missing_materials y missing_centros si aplica
@ventasclaro_bp.route('/api/ventas', methods=['POST'])
def api_create_venta():
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error":"Cuerpo inválido"}), 400

    centro = str(payload.get("Centro Costos","")).strip()
    material = str(payload.get("Material","")).strip()
    fecha = _normalize_date_str(payload.get("Fecha Venta",""))
    cantidad_raw = payload.get("Cantidad", 0)
    try:
        if cantidad_raw is None or cantidad_raw == "":
            cantidad = 0
        else:
            if isinstance(cantidad_raw, (int, float)):
                cantidad = cantidad_raw
            else:
                cantidad = float(str(cantidad_raw).strip())
                if float(cantidad).is_integer():
                    cantidad = int(cantidad)
    except Exception:
        return jsonify({"error":"Campo 'Cantidad' inválido"}), 400

    new_obj = {
        "Centro Costos": centro,
        "Material": material,
        "Fecha Venta": fecha,
        "Cantidad": cantidad
    }

    ventas = read_ventas()
    ventas.append(new_obj)
    write_ventas(ventas)

    existing_materials = _load_existing_materials()
    existing_centros = _load_existing_centros()

    missing_materials = []
    missing_centros = []

    if material and material not in existing_materials:
        missing_materials.append(material)
    if centro and centro not in existing_centros:
        missing_centros.append(centro)

    resp = {"ok": True, "venta": new_obj}
    if missing_materials or missing_centros:
        resp["missing_materials"] = list(dict.fromkeys(missing_materials))
        resp["missing_centros"] = list(dict.fromkeys(missing_centros))

    return jsonify(resp), 201

# Actualizar por índice (0-based) - valida y devuelve missing si aplica
@ventasclaro_bp.route('/api/ventas/<int:idx>', methods=['PUT'])
def api_update_venta(idx):
    payload = request.get_json(force=True)
    if not payload:
        return jsonify({"error":"Cuerpo inválido"}), 400
    ventas = read_ventas()
    if idx < 0 or idx >= len(ventas):
        return jsonify({"error":"Índice fuera de rango"}), 404

    if "Centro Costos" in payload:
        ventas[idx]["Centro Costos"] = str(payload.get("Centro Costos") or "").strip()
    if "Material" in payload:
        ventas[idx]["Material"] = str(payload.get("Material") or "").strip()
    if "Fecha Venta" in payload:
        ventas[idx]["Fecha Venta"] = _normalize_date_str(payload.get("Fecha Venta") or "")
    if "Cantidad" in payload:
        try:
            cr = payload.get("Cantidad")
            if cr is None or cr == "":
                cval = 0
            else:
                if isinstance(cr, (int, float)):
                    cval = cr
                else:
                    cval = float(str(cr).strip())
                    if float(cval).is_integer():
                        cval = int(cval)
            ventas[idx]["Cantidad"] = cval
        except Exception:
            return jsonify({"error":"Campo 'Cantidad' inválido"}), 400

    write_ventas(ventas)

    existing_materials = _load_existing_materials()
    existing_centros = _load_existing_centros()
    vm = ventas[idx]
    missing_materials = []
    missing_centros = []
    if vm.get("Material") and vm.get("Material") not in existing_materials:
        missing_materials.append(vm.get("Material"))
    if vm.get("Centro Costos") and vm.get("Centro Costos") not in existing_centros:
        missing_centros.append(vm.get("Centro Costos"))

    resp = {"ok": True, "venta": ventas[idx]}
    if missing_materials or missing_centros:
        resp["missing_materials"] = list(dict.fromkeys(missing_materials))
        resp["missing_centros"] = list(dict.fromkeys(missing_centros))

    return jsonify(resp), 200

# Borrar por índice
@ventasclaro_bp.route('/api/ventas/<int:idx>', methods=['DELETE'])
def api_delete_venta(idx):
    ventas = read_ventas()
    if idx < 0 or idx >= len(ventas):
        return jsonify({"error":"Índice fuera de rango"}), 404
    ventas.pop(idx)
    write_ventas(ventas)
    return jsonify({"ok":True}), 200

# Borrar todo (confirmaciones)
@ventasclaro_bp.route('/api/delete_all', methods=['POST'])
def api_delete_all():
    data = request.get_json(force=True) or {}
    confirmations = int(data.get("confirmaciones", 0))
    if confirmations < 3:
        return jsonify({"error":"Se requieren 3 confirmaciones para eliminar todos los datos", "confirmaciones_recibidas": confirmations}), 400
    write_ventas([])
    return jsonify({"ok":True, "deleted_all": True}), 200

# Nuevo endpoint: devuelve los pendientes únicos escaneando todas las ventas actuales
@ventasclaro_bp.route('/api/pending', methods=['GET'])
def api_pending():
    ventas = read_ventas()
    existing_materials = _load_existing_materials()
    existing_centros = _load_existing_centros()
    missing_materials_set = set()
    missing_centros_set = set()
    for v in ventas:
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

# Exportar Excel / JSON (sin ids)
@ventasclaro_bp.route('/api/export', methods=['GET'])
def api_export():
    fmt = request.args.get("format", "excel").lower()
    ventas = read_ventas()
    df = pd.DataFrame(ventas)
    for c in ["Centro Costos","Material","Fecha Venta","Cantidad"]:
        if c not in df.columns:
            df[c] = ""
    df = df[["Centro Costos","Material","Fecha Venta","Cantidad"]]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if fmt in ("excel","xlsx"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="VentasClaro")
        output.seek(0)
        filename = f"ventas_claro_{ts}.xlsx"
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        mem = BytesIO()
        mem.write(json.dumps(ventas, ensure_ascii=False, indent=2).encode("utf-8"))
        mem.seek(0)
        filename = f"ventas_claro_{ts}.json"
        return send_file(mem, as_attachment=True, download_name=filename, mimetype="application/json")

# Importar Excel / JSON (devuelve missing lists si aplica) - CON PROTECCIÓN CONTRA IMPORTACIONES DUPLICADAS
@ventasclaro_bp.route('/api/import', methods=['POST'])
def api_import():
    global _last_import_time
    
    with _import_lock:
        current_time = time.time()
        time_since_last_import = current_time - _last_import_time
        
        # Verificar si ha pasado menos de 30 segundos desde la última importación
        if time_since_last_import < _import_cooldown:
            remaining_time = int(_import_cooldown - time_since_last_import)
            return jsonify({
                "error": f"En proceso de importación, espere {remaining_time} segundos para volver a importar"
            }), 429
        
        # Actualizar el tiempo de la última importación
        _last_import_time = current_time
    
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
            col_material = get_col(["Material","material","MATERIAL","Sku","sku"])
            col_fecha = get_col(["Fecha Venta","Fecha_Venta","FechaVenta","fecha venta","fecha_venta","date"])
            col_cantidad = get_col(["Cantidad","cantidad","CANTIDAD","Qty","qty","quantity"])

            if not col_centro or not col_material:
                return jsonify({"error":"El archivo Excel debe tener al menos las columnas 'Centro Costos' y 'Material'"}), 400

            df[col_centro] = df[col_centro].astype(str).fillna("").str.strip()
            if col_cantidad:
                df[col_cantidad] = df[col_cantidad].astype(str).fillna("").str.strip()

            for _, row in df.iterrows():
                centro = str(row.get(col_centro) or "").strip()
                material = str(row.get(col_material) or "").strip()
                if not centro and not material:
                    continue
                fecha = _normalize_date_str(row.get(col_fecha) or "")
                cantidad_val = row.get(col_cantidad, "")
                try:
                    if cantidad_val is None or cantidad_val == "":
                        cantidad = 0
                    else:
                        cantidad = float(str(cantidad_val).strip())
                        if float(cantidad).is_integer():
                            cantidad = int(cantidad)
                except Exception:
                    cantidad = 0
                to_add.append({
                    "Centro Costos": centro,
                    "Material": material,
                    "Fecha Venta": fecha,
                    "Cantidad": cantidad
                })
        else:
            s = content.decode("utf-8", errors="replace").strip()
            parsed = json.loads(s)
            if isinstance(parsed, dict):
                items = [parsed]
            elif isinstance(parsed, list):
                items = parsed
            else:
                return jsonify({"error":"Formato JSON inválido"}), 400

            for item in items:
                if not isinstance(item, dict):
                    continue
                centro = str(item.get("Centro Costos") or item.get("centro_costos") or item.get("centro") or "").strip()
                material = str(item.get("Material") or item.get("material") or "").strip()
                if not centro and not material:
                    continue
                fecha = _normalize_date_str(item.get("Fecha Venta") or item.get("fecha_venta") or item.get("fecha") or "")
                cantidad_raw = item.get("Cantidad") or item.get("cantidad") or 0
                try:
                    if cantidad_raw is None or cantidad_raw == "":
                        cantidad = 0
                    else:
                        if isinstance(cantidad_raw, (int, float)):
                            cantidad = cantidad_raw
                        else:
                            cantidad = float(str(cantidad_raw).strip())
                            if float(cantidad).is_integer():
                                cantidad = int(cantidad)
                except Exception:
                    cantidad = 0
                to_add.append({
                    "Centro Costos": centro,
                    "Material": material,
                    "Fecha Venta": fecha,
                    "Cantidad": cantidad
                })
    except json.JSONDecodeError as jde:
        return jsonify({"error":"JSON inválido", "detail": str(jde)}), 400
    except Exception as e:
        return jsonify({"error":"No se pudo parsear el archivo", "detail": str(e)}), 400

    ventas = read_ventas()
    added = 0

    existing_materials = _load_existing_materials()
    existing_centros = _load_existing_centros()
    missing_materials_set = set()
    missing_centros_set = set()

    for item in to_add:
        ventas.append(item)
        added += 1
        mat = str(item.get("Material") or "").strip()
        cen = str(item.get("Centro Costos") or "").strip()
        if mat and mat not in existing_materials:
            missing_materials_set.add(mat)
        if cen and cen not in existing_centros:
            missing_centros_set.add(cen)

    write_ventas(ventas)

    resp = {"ok": True, "added": added, "total_after": len(ventas)}
    if missing_materials_set or missing_centros_set:
        resp["missing_materials"] = sorted(list(missing_materials_set))
        resp["missing_centros"] = sorted(list(missing_centros_set))

    return jsonify(resp), 200

# --- NUEVO: devolver meses únicos (Mes - Año) ---
@ventasclaro_bp.route('/api/months', methods=['GET'])
def api_months():
    ventas = read_ventas()
    unique = set()
    for v in ventas:
        fs = v.get("Fecha Venta") or ""
        dt = _parse_norm_date_to_date(fs)
        if dt:
            unique.add((dt.year, dt.month))
    # ordenar asc por año, mes
    arr = sorted(list(unique))
    formatted = [f"{SPANISH_MONTHS[m]} - {y}" for (y, m) in arr]
    # si no hay ventas, devolver vacío
    return jsonify({"months": formatted}), 200

# --- NUEVO: borrar registros filtrados por rango de fechas ---
@ventasclaro_bp.route('/api/delete_filtered', methods=['POST'])
def api_delete_filtered():
    data = request.get_json(force=True) or {}
    start_raw = data.get("start_date") or ""
    end_raw = data.get("end_date") or ""

    start_norm = _normalize_date_str(start_raw) if start_raw else ""
    end_norm = _normalize_date_str(end_raw) if end_raw else ""

    start_dt = _parse_norm_date_to_date(start_norm) if start_norm else None
    end_dt = _parse_norm_date_to_date(end_norm) if end_norm else None

    if not start_dt and not end_dt:
        return jsonify({"error":"Se requiere al menos start_date o end_date en formato ISO (YYYY-MM-DD)"}), 400

    ventas = read_ventas()
    kept = []
    deleted_count = 0
    for v in ventas:
        fs = v.get("Fecha Venta") or ""
        dt = _parse_norm_date_to_date(fs)
        # si no podemos parsear la fecha, NO la borramos
        if not dt:
            kept.append(v)
            continue
        remove = False
        # LÓGICA CORREGIDA: Eliminar si está DENTRO del rango
        if start_dt and end_dt:
            if start_dt <= dt <= end_dt:
                remove = True
        elif start_dt and not end_dt:
            if dt >= start_dt:
                remove = True
        elif end_dt and not start_dt:
            if dt <= end_dt:
                remove = True
        
        if remove:
            deleted_count += 1
        else:
            kept.append(v)

    write_ventas(kept)
    return jsonify({"ok": True, "deleted": deleted_count, "remaining": len(kept)}), 200