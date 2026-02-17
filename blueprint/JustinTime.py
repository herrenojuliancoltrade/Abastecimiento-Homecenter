"""
blueprint/JustinTime.py
Blueprint Flask: JustinTime - Versión optimizada con filtros 2025 y estado "sale"
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from conexiones.conexion_odoo import fetch_order_lines  # Mantener importación original

justinTime_bp = Blueprint(
    "justintime",  # Mantener nombre original
    __name__,
    template_folder="../templates",
    static_folder="../static",
)

@justinTime_bp.route("/justintime", strict_slashes=False)
def index():
    """Renderiza la plantilla"""
    return render_template("justinTime.html")

@justinTime_bp.route("/api/justintime", strict_slashes=False)
def api_data():
    """
    API optimizada con:
    - Filtro por año 2025 (fijo)
    - Filtro por estado "sale"
    - Paginación eficiente
    """
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 25))
        
        # Validar parámetros
        if page < 1:
            page = 1
        if per_page > 100:
            per_page = 100

        # Traer todos los registros con filtros aplicados
        all_rows = fetch_order_lines(limit=None)
        
        # Aplicar filtros: año 2025 y estado "sale"
        filtered_rows = []
        for row in all_rows:
            # Filtrar por año 2025
            create_date = row.get("create_date", "")
            if not create_date or not create_date.startswith("2025"):
                continue
                
            # Filtrar por estado "sale"
            state = row.get("state", "").lower()
            if state != "sale":
                continue
                
            filtered_rows.append(row)
        
        if not filtered_rows:
            return jsonify({
                "success": True,
                "page": page,
                "per_page": per_page,
                "total": 0,
                "total_pages": 0,
                "data": []
            })

        total = len(filtered_rows)

        # Ordenar por fecha de creación (más reciente primero)
        filtered_rows_sorted = sorted(
            filtered_rows, 
            key=lambda r: r.get("create_date") or "0000-00-00", 
            reverse=True
        )

        # Paginación eficiente
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_data = filtered_rows_sorted[start_idx:end_idx]

        total_pages = (total + per_page - 1) // per_page

        return jsonify({
            "success": True,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
            "data": page_data,
        })

    except Exception as e:
        current_app.logger.error(f"Error en API justintime: {str(e)}")
        return jsonify({
            "success": False, 
            "error": "Error interno del servidor"
        }), 500