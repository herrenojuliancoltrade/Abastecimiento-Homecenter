# blueprint/compras.py
import json
import re
import os
import tempfile
from pathlib import Path
from threading import Lock
from io import BytesIO

import pandas as pd
from flask import Blueprint, render_template, jsonify, request, send_file

# Intentar usar portalocker si está instalado para bloqueo entre procesos (opcional)
try:
    import portalocker
    _HAS_PORTALOCKER = True
except Exception:
    _HAS_PORTALOCKER = False

compras_bp = Blueprint(
    'compras', __name__,
    url_prefix='/compras',
    template_folder='../templates',
    static_folder='../static'
)

# Ruta relativa al archivo JSON (resuelta desde la ubicación de este archivo)
PROJECT_DIR = Path(__file__).resolve().parent.parent
JSON_REL_PATH = Path("conexiones") / "data_ops" / "data_compras.json"
JSON_PATH = PROJECT_DIR / JSON_REL_PATH

_thread_lock = Lock()

# ---------- Helpers ----------
def _ensure_file():
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not JSON_PATH.exists():
        tmp = JSON_PATH.with_suffix('.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, JSON_PATH)

def _normalize_material(raw):
    """
    Normaliza el identificador 'Material' para comparaciones:
    - maneja notación científica "8,40081E+11" (reemplaza coma decimal por punto si aplica)
    - convierte floats a enteros cuando corresponde
    - elimina espacios y sufijo .0
    - devuelve string vacío si no válido
    """
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""
    s = s.replace('\u200b', '').replace(' ', '')

    # Si contiene 'E' o 'e', probar a parsear notación científica,
    # reemplazando coma decimal por punto si aparece
    if re.search(r'[eE]', s):
        cand = s.replace(',', '.')
        try:
            val = float(cand)
            if abs(val - int(val)) < 1e-6:
                return str(int(val))
            return format(val, 'f').rstrip('0').rstrip('.')
        except Exception:
            pass

    # Si tiene comas como separadores de miles (ej "1,234,567"), quitarlas
    if re.fullmatch(r'[\d\.,]+', s):
        # intentar transformar coma decimal a punto si hay solo una coma y no hay puntos
        if s.count(',') == 1 and s.count('.') == 0:
            try:
                val = float(s.replace(',', '.'))
                if abs(val - int(val)) < 1e-6:
                    return str(int(val))
                return format(val, 'f').rstrip('0').rstrip('.')
            except:
                pass
        # quitar separadores no numéricos
        cleaned = re.sub(r'[^\d]', '', s)
        if cleaned:
            return cleaned

    # eliminar sufijo .0
    s = re.sub(r'\.0+$', '', s)
    return s

def _normalize_text(x):
    if x is None:
        return ""
    return str(x).strip()

def read_compras():
    _ensure_file()
    # Si portalocker disponible, usar bloqueo de lectura compartida
    if _HAS_PORTALOCKER:
        with open(JSON_PATH, 'r', encoding='utf-8') as fh:
            try:
                portalocker.lock(fh, portalocker.LOCK_SH)
                text = fh.read().strip()
            finally:
                try:
                    portalocker.unlock(fh)
                except Exception:
                    pass
    else:
        with _thread_lock:
            text = JSON_PATH.read_text(encoding='utf-8').strip()

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

def write_compras(list_products):
    _ensure_file()
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(JSON_PATH.parent))
    try:
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
            json.dump(list_products, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, JSON_PATH)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

# ---------- Rutas ----------
@compras_bp.route('/')
def compras():
    return render_template('compras.html')

@compras_bp.route('/api/compras', methods=['GET'])
def api_list_compras():
    try:
        items = read_compras()
        norm = []
        for it in items:
            if not isinstance(it, dict):
                continue
            norm.append({
                "Material": _normalize_text(it.get("Material", "")),
                "Producto": _normalize_text(it.get("Producto", "")),
                "Marca": _normalize_text(it.get("Marca", "")),
                "Sugerido": it.get("Sugerido", 0),
                "Confirmar": bool(it.get("Confirmar", False)),
                "Observacion": _normalize_text(it.get("Observacion", ""))
            })
        return jsonify(norm), 200
    except Exception as e:
        return jsonify({"error": "No se pudo leer el archivo", "detail": str(e)}), 500

@compras_bp.route('/api/import', methods=['POST'])
def api_import_compras():
    """
    Importa archivo (Excel/CSV/JSON), usa sólo Material, Producto, Marca, Sugerido.
    Agrupa por Material dentro del archivo y luego mergea con el JSON existente sumando 'Sugerido'.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No se encontró archivo en el formulario (campo 'file')"}), 400

    f = request.files['file']
    filename = (f.filename or "").lower()
    content = f.read()

    try:
        is_excel = filename.endswith(('.xls', '.xlsx')) or content[:4] == b'PK\x03\x04'
        is_csv = filename.endswith('.csv') or (b',' in content[:2048] or b';' in content[:2048])

        if is_excel:
            engine = None
            if filename.endswith('.xlsx'):
                engine = 'openpyxl'
            df = pd.read_excel(BytesIO(content), dtype=str, engine=engine) if engine else pd.read_excel(BytesIO(content), dtype=str)
        elif is_csv:
            try:
                df = pd.read_csv(BytesIO(content), dtype=str, sep=None, engine='python')
            except Exception:
                df = pd.read_csv(BytesIO(content), dtype=str)
        else:
            s = content.decode('utf-8', errors='replace').strip()
            parsed = json.loads(s)
            if isinstance(parsed, dict):
                parsed = [parsed]
            rows = []
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                rows.append(item)
            df = pd.DataFrame(rows)
    except Exception as e:
        return jsonify({"error": "No se pudo leer el archivo de entrada", "detail": str(e)}), 400

    df.columns = [str(c).strip() for c in df.columns]
    lower_map = {c.lower(): c for c in df.columns}

    def get_col(possible):
        for opt in possible:
            lo = opt.lower()
            if lo in lower_map:
                return lower_map[lo]
        return None

    col_material = get_col(["Material", "material", "MATERIAL"])
    col_producto = get_col(["Producto", "producto", "PRODUCTO", "Descripcion", "descripcion"])
    col_marca = get_col(["Marca", "marca", "MARCA", "Brand", "brand"])
    col_sugerido = get_col(["Sugerido", "sugerido", "SUGERIDO"])

    if not col_material:
        return jsonify({"error": "El archivo debe contener una columna 'Material'"}), 400

    df[col_material] = df[col_material].astype(str).fillna("").str.strip()
    if col_producto:
        df[col_producto] = df[col_producto].astype(str).fillna("").str.strip()
    else:
        df['Producto'] = ""
        col_producto = 'Producto'
    if col_marca:
        df[col_marca] = df[col_marca].astype(str).fillna("").str.strip()
    else:
        df['Marca'] = ""
        col_marca = 'Marca'
    if col_sugerido:
        df[col_sugerido] = df[col_sugerido].astype(str).fillna("").str.replace(',', '.', regex=False).str.strip()
    else:
        df['Sugerido'] = "0"
        col_sugerido = 'Sugerido'

    imported_map = {}
    for _, row in df.iterrows():
        raw_mat = row.get(col_material, "")
        mat = _normalize_material(raw_mat)
        if not mat:
            continue
        prod = _normalize_text(row.get(col_producto, ""))
        marca = _normalize_text(row.get(col_marca, ""))
        sug_raw = str(row.get(col_sugerido, "")).strip()
        try:
            sug_val = float(sug_raw) if sug_raw not in ("", None) else 0.0
        except Exception:
            m = re.search(r'[-+]?\d+(\.\d+)?', sug_raw.replace(',', '.'))
            if m:
                sug_val = float(m.group(0))
            else:
                sug_val = 0.0

        if mat in imported_map:
            imported_map[mat]["Sugerido"] += sug_val
        else:
            imported_map[mat] = {
                "Material": mat,
                "Producto": prod,
                "Marca": marca,
                "Sugerido": sug_val
            }

    for k, v in imported_map.items():
        sv = v["Sugerido"]
        if abs(sv - int(sv)) < 1e-6:
            v["Sugerido"] = int(sv)
        else:
            v["Sugerido"] = float(round(sv, 6))

    existing = read_compras()
    existing_map = {}
    for it in existing:
        mat_norm = _normalize_material(it.get("Material"))
        if not mat_norm:
            continue
        existing_map[mat_norm] = {
            "Material": mat_norm,
            "Producto": _normalize_text(it.get("Producto", "")),
            "Marca": _normalize_text(it.get("Marca", "")),
            "Sugerido": float(it.get("Sugerido", 0)) if it.get("Sugerido", "") != "" else 0.0,
            "Confirmar": bool(it.get("Confirmar", False)),
            "Observacion": _normalize_text(it.get("Observacion", ""))
        }

    added = 0
    updated = 0
    for mat, data in imported_map.items():
        sug = float(data["Sugerido"])
        if mat in existing_map:
            existing_map[mat]["Sugerido"] = existing_map[mat].get("Sugerido", 0) + sug
            if not existing_map[mat].get("Producto") and data.get("Producto"):
                existing_map[mat]["Producto"] = data.get("Producto")
            if not existing_map[mat].get("Marca") and data.get("Marca"):
                existing_map[mat]["Marca"] = data.get("Marca")
            updated += 1
        else:
            existing_map[mat] = {
                "Material": mat,
                "Producto": data.get("Producto", ""),
                "Marca": data.get("Marca", ""),
                "Sugerido": sug,
                "Confirmar": False,
                "Observacion": ""
            }
            added += 1

    result_list = []
    for mat, it in existing_map.items():
        sv = it.get("Sugerido", 0)
        if abs(sv - int(sv)) < 1e-6:
            sv = int(sv)
        else:
            sv = float(round(sv, 6))
        result_list.append({
            "Material": it.get("Material", ""),
            "Producto": it.get("Producto", ""),
            "Marca": it.get("Marca", ""),
            "Sugerido": sv,
            "Confirmar": bool(it.get("Confirmar", False)),
            "Observacion": it.get("Observacion", "") or ""
        })

    try:
        write_compras(result_list)
    except Exception as e:
        return jsonify({"error": "No se pudo escribir el archivo destino", "detail": str(e)}), 500

    return jsonify({
        "ok": True,
        "added": added,
        "updated": updated,
        "total_after": len(result_list)
    }), 200

@compras_bp.route('/api/export_excel', methods=['GET'])
def api_export_excel():
    """
    Exporta todos los registros a un archivo Excel (.xlsx).
    Agrega columna 'Estado' -> 'Aprobado' si Confirmar true, 'No aprobado' si false.
    """
    try:
        data = read_compras()
        # Normalizar y construir DataFrame
        rows = []
        for it in data:
            if not isinstance(it, dict):
                continue
            confirmar = bool(it.get("Confirmar", False))
            estado = "Aprobado" if confirmar else "No aprobado"
            rows.append({
                "Material": _normalize_text(it.get("Material", "")),
                "Producto": _normalize_text(it.get("Producto", "")),
                "Marca": _normalize_text(it.get("Marca", "")),
                "Sugerido": it.get("Sugerido", ""),
                "Estado": estado,
                "Observacion": _normalize_text(it.get("Observacion", "")),
            })
        df = pd.DataFrame(rows, columns=["Material", "Producto", "Marca", "Sugerido", "Estado", "Observacion"])

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Compras")
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="compras.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        return jsonify({"error": "No se pudo generar el Excel", "detail": str(e)}), 500

@compras_bp.route('/api/update', methods=['POST'])
def api_update_item():
    """
    Actualiza campos de un registro identificado por 'Material'.
    Espera JSON: {"Material": "...", "Confirmar": true/false (opcional), "Observacion": "..." (opcional)}
    """
    try:
        payload = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "Cuerpo JSON inválido"}), 400

    if not payload or "Material" not in payload:
        return jsonify({"error": "Se requiere el campo 'Material'"}), 400

    raw_mat = payload.get("Material")
    mat = _normalize_material(raw_mat)
    if not mat:
        return jsonify({"error": "Material inválido"}), 400

    try:
        items = read_compras()
        found = False
        for it in items:
            if _normalize_material(it.get("Material")) == mat:
                # actualizar Confirmar si viene
                if "Confirmar" in payload:
                    it["Confirmar"] = bool(payload.get("Confirmar", False))
                # actualizar Observacion si viene
                if "Observacion" in payload:
                    it["Observacion"] = str(payload.get("Observacion") or "")
                # actualizar Producto/Marca opcional (no se sobrescriben por defecto)
                if "Producto" in payload:
                    it["Producto"] = str(payload.get("Producto") or it.get("Producto",""))
                if "Marca" in payload:
                    it["Marca"] = str(payload.get("Marca") or it.get("Marca",""))
                found = True
                break

        if not found:
            return jsonify({"error": "Registro no encontrado para actualizar"}), 404

        write_compras(items)
        return jsonify({"ok": True, "updated": mat}), 200
    except Exception as e:
        return jsonify({"error": "Error al actualizar", "detail": str(e)}), 500
