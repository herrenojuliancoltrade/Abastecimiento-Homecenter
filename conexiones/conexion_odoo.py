#!/usr/bin/env python3
"""
conexion_odoo.py
Versión optimizada con filtros por año 2025 y estado "sale"
"""

import os
import logging
import xmlrpc.client
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any

# --- logging básico ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

# --- Resolver la ruta del .env ---
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
COLTRADE_ROOT = os.path.dirname(THIS_DIR)
ENV_PATH = os.path.join(COLTRADE_ROOT, ".env")

if os.path.exists(ENV_PATH):
    load_dotenv(dotenv_path=ENV_PATH)
    logging.info(f".env cargado desde: {ENV_PATH}")
else:
    load_dotenv()
    logging.warning(f"No se encontró .env en {ENV_PATH}. Se intentó cargar .env por defecto.")

# --- Leer variables desde entorno ---
URL = os.getenv("ODOO_URL")
DB = os.getenv("ODOO_DB")
USERNAME = os.getenv("ODOO_USERNAME")
API_KEY = os.getenv("ODOO_API_KEY")

missing = [k for k, v in (
    ("ODOO_URL", URL),
    ("ODOO_DB", DB),
    ("ODOO_USERNAME", USERNAME),
    ("ODOO_API_KEY", API_KEY)
) if not v]

if missing:
    logging.error("Faltan variables obligatorias en el entorno: %s", ", ".join(missing))
    raise RuntimeError(f"Faltan variables en .env: {', '.join(missing)}")

def get_connection():
    logging.info("Conectando a Odoo en %s ...", URL)
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common", allow_none=True)
    version = common.version()
    logging.info("Servidor Odoo versión: %s", version.get("server_version"))
    uid = common.authenticate(DB, USERNAME, API_KEY, {})
    if not uid:
        logging.error("Falló la autenticación con Odoo. Revisa .env")
        raise RuntimeError("Autenticación Odoo fallida")
    logging.info("Autenticación correcta (UID=%s).", uid)
    models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", allow_none=True)
    return models, uid

def extract_id(value: Any) -> Optional[int]:
    """
    Extrae el id desde distintos formatos posibles que devuelve Odoo
    """
    if value is None:
        return None
    if isinstance(value, (list, tuple)) and len(value) > 0:
        try:
            return int(value[0])
        except Exception:
            return None
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except Exception:
        return None

def fetch_order_lines(limit: Optional[int] = None) -> List[Dict]:
    """
    Versión optimizada para obtener líneas de pedido
    con filtros por año 2025 y estado "sale"
    """
    try:
        models, uid = get_connection()

        # Dominio con filtros fijos: año 2025 y estado "sale"
        domain = [
            ('create_date', '>=', '2025-01-01'),
            ('create_date', '<', '2026-01-01'),
            ('state', '=', 'sale')
        ]
        
        # Campos optimizados
        fields_line = [
            "id", "order_id", "product_id", "product_uom_qty", 
            "qty_delivered", "price_unit", "name_short", "create_date"
        ]
        
        params = {"fields": fields_line}
        if limit:
            params["limit"] = int(limit)
            
        # Ordenar por fecha de creación en la consulta
        params["order"] = "create_date DESC"

        logging.info("Leyendo sale.order.line con filtros 2025 y estado=sale (limit=%s)...", str(limit))
        lines = models.execute_kw(DB, uid, API_KEY, "sale.order.line", "search_read", [domain], params)

        if not lines:
            logging.info("No se devolvieron líneas de pedido para 2025 con estado 'sale'.")
            return []

        # Recolectar IDs únicos de forma más eficiente
        product_ids = set()
        order_ids = set()
        
        for l in lines:
            if pid := extract_id(l.get("product_id")):
                product_ids.add(pid)
            if oid := extract_id(l.get("order_id")):
                order_ids.add(oid)

        # Leer productos en batch
        products_map = {}
        if product_ids:
            logging.info("Leyendo product.product para %d productos...", len(product_ids))
            product_fields = ["id", "default_code", "x_studio_marca"]
            try:
                products = models.execute_kw(DB, uid, API_KEY, "product.product", "read", 
                                           [list(product_ids)], {"fields": product_fields})
                products_map = {p["id"]: p for p in products}
            except Exception as e:
                logging.warning("Error leyendo product.product: %s", str(e))

        # Leer órdenes en batch
        orders_map = {}
        if order_ids:
            logging.info("Leyendo sale.order para %d órdenes...", len(order_ids))
            order_fields = [
                "id", "state", "create_date", "effective_date",
                "x_studio_canal", "x_studio_fuente_1", 
                "x_studio_orden_fuente", "name", "user_id"
            ]
            try:
                orders = models.execute_kw(DB, uid, API_KEY, "sale.order", "read", 
                                         [list(order_ids)], {"fields": order_fields})
                orders_map = {o["id"]: o for o in orders}
            except Exception as e:
                logging.warning("Error leyendo sale.order: %s", str(e))

        # Combinar registros de forma más eficiente
        results = []
        for line in lines:
            pid = extract_id(line.get("product_id"))
            oid = extract_id(line.get("order_id"))

            prod = products_map.get(pid, {}) if pid else {}
            order = orders_map.get(oid, {}) if oid else {}

            # Extraer vendedor de forma segura
            vendedor = ""
            userval = order.get("user_id")
            if isinstance(userval, (list, tuple)) and len(userval) > 1:
                vendedor = userval[1]
            elif userval:
                vendedor = str(userval)

            registro = {
                "ref_interna": prod.get("default_code", ""),
                "price_unit": float(line.get("price_unit", 0)),
                "nombre_corto": line.get("name_short", ""),
                "qty_delivered": float(line.get("qty_delivered", 0)),
                "cantidad": float(line.get("product_uom_qty", 0)),
                "state": order.get("state", ""),
                "create_date": order.get("create_date", line.get("create_date", "")),
                "effective_date": order.get("effective_date", ""),
                "canal": order.get("x_studio_canal", ""),
                "fuente": order.get("x_studio_fuente_1", ""),
                "marca": prod.get("x_studio_marca", ""),
                "orden_fuente": order.get("x_studio_orden_fuente", ""),
                "referencia": order.get("name", ""),
                "vendedor": vendedor,
            }
            results.append(registro)

        logging.info("Se generaron %d registros para 2025 con estado 'sale'.", len(results))
        return results

    except Exception as e:
        logging.exception("Error en fetch_order_lines: %s", e)
        return []

# debug rápido al ejecutar el módulo directamente
if __name__ == "__main__":
    rows = fetch_order_lines(limit=50)
    print(f"Registros devueltos para 2025 con estado 'sale': {len(rows)}")
    for r in rows[:10]:
        print(r)