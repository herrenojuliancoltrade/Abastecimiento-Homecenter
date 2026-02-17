from flask import Blueprint, render_template, jsonify, request
from pathlib import Path
import pandas as pd
import json
from datetime import date
from dateutil.relativedelta import relativedelta
import math

forecast_bp = Blueprint('forecast', __name__, url_prefix='/forecast', template_folder='../templates')

DATA_DIR = Path(__file__).resolve().parent.parent / 'conexiones' / 'data_ops'

def load_json_to_df(p: Path):
    try:
        if not p.exists():
            return pd.DataFrame()
        try:
            df = pd.read_json(p, convert_dates=False)
        except ValueError:
            with p.open('r', encoding='utf-8') as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                raw = [raw]
            df = pd.DataFrame(raw)
        return df
    except Exception as e:
        print(f"Error cargando {p}: {e}")
        return pd.DataFrame()

def normalize_str(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return ''
    return str(x).strip()

def parse_multi_param(name):
    v = request.args.get(name)
    if not v:
        return []
    parts = [p.strip() for p in v.split(',') if p.strip() != '']
    return [p.lower() for p in parts]

def prepare_dataframes():
    inventario_fp = DATA_DIR / 'inventario_claro.json'
    transitos_fp = DATA_DIR / 'transitos.json'
    ventas_fp = DATA_DIR / 'ventas_claro.json'
    productos_fp = DATA_DIR / 'productos_claro.json'
    puntos_fp = DATA_DIR / 'puntos_venta_claro.json'
    metas_fp = DATA_DIR / 'metas.json'

    df_inv = load_json_to_df(inventario_fp)
    df_tra = load_json_to_df(transitos_fp)
    df_ven = load_json_to_df(ventas_fp)
    df_prod = load_json_to_df(productos_fp)
    df_puntos = load_json_to_df(puntos_fp)
    df_metas = load_json_to_df(metas_fp)

    # Normalizaciones
    if not df_inv.empty:
        if 'Inventario' in df_inv.columns:
            df_inv['Inventario'] = pd.to_numeric(df_inv['Inventario'], errors='coerce').fillna(0)
        if 'Material' in df_inv.columns:
            df_inv['Material'] = df_inv['Material'].astype(str)
        if 'Centro Costos' in df_inv.columns:
            df_inv['Centro Costos'] = df_inv['Centro Costos'].astype(str)
    if not df_tra.empty:
        if 'Transitos' in df_tra.columns:
            df_tra['Transitos'] = pd.to_numeric(df_tra['Transitos'], errors='coerce').fillna(0)
        if 'Material' in df_tra.columns:
            df_tra['Material'] = df_tra['Material'].astype(str)
        if 'Centro Costos' in df_tra.columns:
            df_tra['Centro Costos'] = df_tra['Centro Costos'].astype(str)
    if not df_ven.empty:
        if 'Cantidad' in df_ven.columns:
            df_ven['Cantidad'] = pd.to_numeric(df_ven['Cantidad'], errors='coerce').fillna(0)
        if 'Fecha Venta' in df_ven.columns:
            df_ven['Fecha Venta'] = pd.to_datetime(df_ven['Fecha Venta'], errors='coerce')
        if 'Material' in df_ven.columns:
            df_ven['Material'] = df_ven['Material'].astype(str)
        if 'Centro Costos' in df_ven.columns:
            df_ven['Centro Costos'] = df_ven['Centro Costos'].astype(str)
    if not df_prod.empty:
        if 'Material' in df_prod.columns:
            df_prod['Material'] = df_prod['Material'].astype(str)
        if 'Producto' in df_prod.columns:
            df_prod['Producto'] = df_prod['Producto'].astype(str)
        if 'Marca' in df_prod.columns:
            df_prod['Marca'] = df_prod['Marca'].astype(str)
    if not df_puntos.empty:
        if 'Centro Costos' in df_puntos.columns:
            df_puntos['Centro Costos'] = df_puntos['Centro Costos'].astype(str)
        if 'Punto de Venta' in df_puntos.columns:
            df_puntos['Punto de Venta'] = df_puntos['Punto de Venta'].astype(str)
        if 'Canal o Regional' in df_puntos.columns:
            df_puntos['Canal o Regional'] = df_puntos['Canal o Regional'].astype(str)
    if not df_metas.empty:
        if 'Material' in df_metas.columns:
            df_metas['Material'] = df_metas['Material'].astype(str)
        if 'Centro Costos' in df_metas.columns:
            df_metas['Centro Costos'] = df_metas['Centro Costos'].astype(str)
        if 'Meta Cantidad' in df_metas.columns:
            df_metas['Meta Cantidad'] = pd.to_numeric(df_metas['Meta Cantidad'], errors='coerce').fillna(0)

    return df_inv, df_tra, df_ven, df_prod, df_puntos, df_metas

@forecast_bp.route('/')
def forecast_page():
    return render_template('forecast.html')

@forecast_bp.route('/options')
def forecast_options():
    df_inv, df_tra, df_ven, df_prod, df_puntos, df_metas = prepare_dataframes()

    centros_filter = parse_multi_param('centro')
    puntos_filter = parse_multi_param('punto')
    materials_filter = parse_multi_param('material')
    productos_filter = parse_multi_param('producto')
    marcas_filter = parse_multi_param('marca')
    canales_filter = parse_multi_param('canal')

    centros = set()
    puntos = set()
    materials = set()
    productos = set()
    marcas = set()
    canales = set()

    if not df_puntos.empty:
        for _, r in df_puntos.iterrows():
            cc = normalize_str(r.get('Centro Costos'))
            pv = normalize_str(r.get('Punto de Venta'))
            canal = normalize_str(r.get('Canal o Regional'))
            if centros_filter and cc.lower() not in centros_filter:
                continue
            if puntos_filter and pv.lower() not in puntos_filter:
                continue
            if canales_filter and canal.lower() not in canales_filter:
                continue
            centros.add(cc)
            puntos.add(pv)
            if canal != '':
                canales.add(canal)

    if not df_inv.empty:
        for c in df_inv['Centro Costos'].dropna().unique().tolist():
            c = normalize_str(c)
            if centros_filter and c.lower() not in centros_filter:
                continue
            centros.add(c)
    if not df_tra.empty:
        for c in df_tra['Centro Costos'].dropna().unique().tolist():
            c = normalize_str(c)
            if centros_filter and c.lower() not in centros_filter:
                continue
            centros.add(c)
    if not df_ven.empty:
        for c in df_ven['Centro Costos'].dropna().unique().tolist():
            c = normalize_str(c)
            if centros_filter and c.lower() not in centros_filter:
                continue
            centros.add(c)

    if not df_prod.empty:
        for _, r in df_prod.iterrows():
            mat = normalize_str(r.get('Material'))
            prod = normalize_str(r.get('Producto')) if 'Producto' in r else ''
            marca = normalize_str(r.get('Marca')) if 'Marca' in r else ''
            if materials_filter and mat.lower() not in materials_filter:
                continue
            if marcas_filter and marca != '' and marca.lower() not in marcas_filter:
                continue
            materials.add(mat)
            if prod != '':
                productos.add(prod)
            if marca != '':
                marcas.add(marca)

    return jsonify({
        'centros': sorted(list(centros)),
        'puntos': sorted(list(puntos)),
        'materials': sorted(list(materials)),
        'productos': sorted(list(productos)),
        'marcas': sorted(list(marcas)),
        'canales': sorted(list(canales))
    })

@forecast_bp.route('/data')
def forecast_data():
    """VERSIÓN OPTIMIZADA - Usa merge en lugar de máscaras repetitivas"""
    df_inv, df_tra, df_ven, df_prod, df_puntos, df_metas = prepare_dataframes()

    centros_filter = parse_multi_param('centro')
    puntos_filter = parse_multi_param('punto')
    materials_filter = parse_multi_param('material')
    productos_filter = parse_multi_param('producto')
    marcas_filter = parse_multi_param('marca')
    canales_filter = parse_multi_param('canal')

    try:
        page = max(1, int(request.args.get('page', 1)))
    except Exception:
        page = 1
    try:
        page_size = int(request.args.get('page_size', 50))
        if page_size <= 0:
            page_size = 50
    except Exception:
        page_size = 50
    if page_size > 1000:
        page_size = 1000

    # Maps
    prod_map = {}
    if not df_prod.empty and 'Material' in df_prod.columns:
        for _, r in df_prod.iterrows():
            m = normalize_str(r.get('Material'))
            prod_map[m] = {
                'Producto': normalize_str(r.get('Producto')) if 'Producto' in r else '',
                'Marca': normalize_str(r.get('Marca')) if 'Marca' in r else ''
            }

    puntos_map = {}
    if not df_puntos.empty and 'Centro Costos' in df_puntos.columns:
        for _, r in df_puntos.iterrows():
            cc = normalize_str(r.get('Centro Costos'))
            puntos_map[cc] = {
                'Punto de Venta': normalize_str(r.get('Punto de Venta')) if 'Punto de Venta' in r else '',
                'Canal o Regional': normalize_str(r.get('Canal o Regional')) if 'Canal o Regional' in r else ''
            }

    # Candidates
    candidates = set()
    if not df_inv.empty and {'Centro Costos','Material'}.issubset(df_inv.columns):
        for _, r in df_inv.iterrows():
            cc = normalize_str(r.get('Centro Costos'))
            mat = normalize_str(r.get('Material'))
            if mat in prod_map:
                candidates.add((cc, mat))
    if not df_tra.empty and {'Centro Costos','Material'}.issubset(df_tra.columns):
        for _, r in df_tra.iterrows():
            cc = normalize_str(r.get('Centro Costos'))
            mat = normalize_str(r.get('Material'))
            if mat in prod_map:
                candidates.add((cc, mat))
    if not df_ven.empty and {'Centro Costos','Material'}.issubset(df_ven.columns):
        for _, r in df_ven.iterrows():
            cc = normalize_str(r.get('Centro Costos'))
            mat = normalize_str(r.get('Material'))
            if mat in prod_map:
                candidates.add((cc, mat))

    # ===== OPTIMIZACIÓN: Pre-agrupar y crear diccionarios =====
    today = date.today()
    months = [(today - relativedelta(months=i)).replace(day=1) for i in range(1, 4)]
    
    # Ventas agrupadas - OPTIMIZADO con set_index
    ventas_monthly_dict = {}
    ventas_current_dict = {}
    ventas_all_dict = {}
    
    if not df_ven.empty:
        df_ven['year'] = df_ven['Fecha Venta'].dt.year
        df_ven['month'] = df_ven['Fecha Venta'].dt.month
        
        # Agrupar ventas históricas
        ventas_grouped = df_ven.groupby(['Centro Costos','Material','year','month'], dropna=False)['Cantidad'].sum()
        ventas_monthly_dict = ventas_grouped.to_dict()
        
        # Ventas del mes actual
        cy = today.year
        cm = today.month
        df_current = df_ven[(df_ven['year'] == cy) & (df_ven['month'] == cm)]
        if not df_current.empty:
            ventas_current = df_current.groupby(['Centro Costos','Material'])['Cantidad'].sum()
            ventas_current_dict = ventas_current.to_dict()
        
        # Mediana - todas las ventas por CC + Material
        ventas_all = df_ven.groupby(['Centro Costos','Material'])['Cantidad'].median()
        ventas_all_dict = ventas_all.to_dict()

    # Inventario agrupado - OPTIMIZADO con to_dict
    inv_dict = {}
    if not df_inv.empty:
        inv_grouped = df_inv.groupby(['Centro Costos','Material'], dropna=False)['Inventario'].sum()
        inv_dict = inv_grouped.to_dict()
    
    # Tránsitos agrupados - OPTIMIZADO con to_dict
    tra_dict = {}
    if not df_tra.empty:
        tra_grouped = df_tra.groupby(['Centro Costos','Material'], dropna=False)['Transitos'].sum()
        tra_dict = tra_grouped.to_dict()

    def candidate_matches_filters(cc, mat):
        if centros_filter and cc.lower() not in centros_filter:
            return False
        punto = puntos_map.get(cc, {}).get('Punto de Venta','').lower()
        if puntos_filter and punto not in puntos_filter:
            return False
        if materials_filter and mat.lower() not in materials_filter:
            return False
        prod_name = prod_map.get(mat, {}).get('Producto','').lower()
        if productos_filter:
            found = False
            for pat in productos_filter:
                if pat in prod_name:
                    found = True
                    break
            if not found:
                return False
        marca = prod_map.get(mat, {}).get('Marca','').lower()
        if marcas_filter and marca not in marcas_filter:
            return False
        canal_val = puntos_map.get(cc, {}).get('Canal o Regional','').lower()
        if canales_filter and canal_val not in canales_filter:
            return False
        return True

    records = []
    for cc, mat in sorted(candidates):
        if not candidate_matches_filters(cc, mat):
            continue

        # ===== LOOKUPS OPTIMIZADOS - Sin máscaras booleanas =====
        
        # Ventas por mes (últimos 3 meses excluyendo actual)
        month_totals = []
        for d in months:
            key = (cc, mat, d.year, d.month)
            month_totals.append(int(ventas_monthly_dict.get(key, 0)))
        
        ventas_pasado = month_totals[0]
        ventas_promedio = round(sum(month_totals) / 3.0, 2)
        
        # Ventas mes actual
        ventas_actual = int(ventas_current_dict.get((cc, mat), 0))
        
        # Inventario y tránsitos
        inventario = int(inv_dict.get((cc, mat), 0))
        transitos = int(tra_dict.get((cc, mat), 0))
        
        # Mediana
        mediana = ventas_all_dict.get((cc, mat))
        if mediana is not None and pd.notna(mediana):
            mediana = float(round(float(mediana), 2))
        else:
            mediana = None

        # Filtro de inclusión
        if not (inventario > 0 or transitos > 0 or ventas_actual > 0 or ventas_pasado > 0 or ventas_promedio > 0):
            continue

        # Cálculos
        envio_3_meses = round(ventas_promedio - inventario, 2)
        envio_pasadas = round(ventas_pasado - inventario, 2)

        indicador_3_meses = None
        if ventas_promedio != 0:
            indicador_3_meses = round(inventario / ventas_promedio, 4)
        indicador_mes_pasado = None
        if ventas_pasado != 0:
            indicador_mes_pasado = round(inventario / ventas_pasado, 4)

        producto_name = prod_map.get(mat, {}).get('Producto','')
        marca_name = prod_map.get(mat, {}).get('Marca','')
        punto_name = puntos_map.get(cc, {}).get('Punto de Venta','')
        canal_name = puntos_map.get(cc, {}).get('Canal o Regional','')

        rec = {
            'Centro Costos': cc,
            'Material': mat,
            'Productos': producto_name,
            'Marca': marca_name,
            'Punto de Venta': punto_name,
            'Canal o Regional': canal_name,
            'Ventas_Mes_Actual': ventas_actual,
            'Ventas_Mes_Pasado': ventas_pasado,
            'Ventas_Promedio_3_Meses': ventas_promedio,
            'Mediana': mediana,
            'Inventario': inventario,
            'Transitos': transitos,
            'Indicador_3_Meses': indicador_3_meses,
            'Indicador_Mes_Pasado': indicador_mes_pasado,
            'Envio_3_Meses': envio_3_meses,
            'Envio_Pasadas': envio_pasadas
        }
        records.append(rec)

    # Sort por Envio_Pasadas descendente xdd
    records = sorted(records, key=lambda x: (-(x.get('Envio_Pasadas') or 0), x.get('Centro Costos') or '', x.get('Material') or ''))

    total = len(records)
    total_pages = math.ceil(total / page_size) if page_size > 0 else 1
    if page > total_pages and total_pages > 0:
        page = total_pages
    start = (page - 1) * page_size
    end = start + page_size
    page_records = records[start:end]

    return jsonify({
        'records': page_records,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages
    })