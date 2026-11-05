"""
Motor de Investigación de Operaciones y Planificación de Inventario (S&OP)
Caso 1: Pedido de Vehículos Nuevos a Fábrica (Ventana Octubre 2026).
"""

from __future__ import annotations

import io
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constantes Oficiales y Reglas de Negocio (Comunicados de Fábrica y Gerencia)
# ---------------------------------------------------------------------------

OFFICIAL_MODELS: List[str] = [
    "Hilux",
    "Fortuner",
    "Corolla",
    "Corolla Cross",
    "Yaris",
    "Yaris Cross",
    "RAV4",
    "Land Cruiser Prado",
    "Rush",
    "Hiace",
    "Raize",
]

OFFICIAL_BRANCHES: List[str] = [
    "Managua Central",
    "Managua Sur",
    "León",
    "Chinandega",
    "Estelí",
    "Juigalpa",
    "Matagalpa",
]

# Regla de Lotes y Mínimos de fábrica (Comunicado 03/06/2025): (Mínimo, Múltiplo)
LOT_RULES: Dict[str, Tuple[int, int]] = {
    "Hilux": (12, 6),
    "Fortuner": (8, 4),
    "Corolla": (6, 6),
    "Corolla Cross": (12, 6),
    "Yaris": (16, 8),
    "Yaris Cross": (12, 6),
    "RAV4": (4, 4),
    "Land Cruiser Prado": (2, 2),
    "Rush": (8, 4),
    "Hiace": (3, 3),
    "Raize": (12, 6),
}

# Motivos de pérdida en CRM asociados a desabastecimiento / falta de inventario
STOCKOUT_REASONS: List[str] = [
    "Sin disponibilidad / sin inventario",
    "Sin disponibilidad",
    "Sin inventario",
    "No hay unidades disponibles",
    "Sin stock",
    "Sin disponibilidad de versión/color",
    "Color no disponible",
    "Versión no disponible",
]

CUTOFF_DATE = pd.Timestamp("2026-09-30")
FLOORPLAN_MONTHLY_RATE = 0.009  # 0.9% mensual sobre costo unitario


def get_default_excel_path() -> Path:
    """Localiza automáticamente el archivo Excel del Caso 1 en el espacio de trabajo."""
    candidates = [
        Path("Caso 1 - Pedido Vehiculos Nuevos/Caso 1 - Base de datos Vehiculos Nuevos.xlsx"),
        Path(__file__).resolve().parent.parent
        / "Caso 1 - Pedido Vehiculos Nuevos"
        / "Caso 1 - Base de datos Vehiculos Nuevos.xlsx",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "No se encontró 'Caso 1 - Base de datos Vehiculos Nuevos.xlsx'."
    )


# ---------------------------------------------------------------------------
# 1. Limpieza y Normalización
# ---------------------------------------------------------------------------

def normalize_model_name(val: Any) -> Any:
    """
    Estandariza cualquier variante de nombre de modelo hacia los 11 nombres oficiales
    de la hoja 'Economía por modelo', corrigiendo mayúsculas, espacios dobles y
    prefijos como 'Toyota '.
    """
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"(?i)^toyota\s+", "", s).strip()
    s_lower = s.lower()
    for official in OFFICIAL_MODELS:
        if s_lower == official.lower():
            return official
    return s


def normalize_branch_name(val: Any) -> Any:
    """Normaliza las variantes de nombres de las 7 sucursales en Ventas y Leads."""
    if pd.isna(val):
        return np.nan
    s = re.sub(r"\s+", " ", str(val).strip()).lower()
    mapping = {
        "managua central": "Managua Central",
        "managua sur": "Managua Sur",
        "mga sur": "Managua Sur",
        "chinandega": "Chinandega",
        "esteli": "Estelí",
        "estelí": "Estelí",
        "juigalpa": "Juigalpa",
        "matagalpa": "Matagalpa",
        "leon": "León",
        "león": "León",
    }
    return mapping.get(s, str(val).strip())


def load_and_clean_caso1(
    excel_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """
    Carga todas las hojas del archivo Excel del Caso 1, aplica la normalización
    de modelos y sucursales, e identifica y netea las Notas de Crédito en Ventas.
    """
    path = Path(excel_path) if excel_path else get_default_excel_path()
    xl = pd.ExcelFile(path)

    economia = xl.parse("Economía por modelo").copy()
    economia["Modelo"] = economia["Modelo"].apply(normalize_model_name)

    ventas_raw = xl.parse("Ventas").copy()
    inventario = xl.parse("Inventario").copy()
    leads = xl.parse("Leads").copy()
    pedidos = xl.parse("Pedidos").copy()
    comunicados = xl.parse("Comunicados").copy()

    # Normalización de Modelos
    ventas_raw["Modelo_raw"] = ventas_raw["Modelo"]
    ventas_raw["Modelo"] = ventas_raw["Modelo"].apply(normalize_model_name)
    ventas_raw["Sucursal_raw"] = ventas_raw["Sucursal"]
    ventas_raw["Sucursal"] = ventas_raw["Sucursal"].apply(normalize_branch_name)
    ventas_raw["Fecha"] = pd.to_datetime(ventas_raw["Fecha"])
    ventas_raw["Mes"] = ventas_raw["Fecha"].dt.to_period("M").dt.to_timestamp()
    ventas_raw["Versión"] = ventas_raw["Versión"].astype(str).str.strip()
    ventas_raw["Color"] = ventas_raw["Color"].astype(str).str.strip()

    inventario["Modelo"] = inventario["Modelo"].apply(normalize_model_name)
    inventario["Mes (cierre)"] = pd.to_datetime(inventario["Mes (cierre)"])
    inventario["Versión"] = inventario["Versión"].astype(str).str.strip()
    inventario["Color"] = inventario["Color"].astype(str).str.strip()

    leads["Modelo de interés"] = leads["Modelo de interés"].apply(normalize_model_name)
    if "Modelo comprado (si difiere)" in leads.columns:
        leads["Modelo comprado (si difiere)"] = leads[
            "Modelo comprado (si difiere)"
        ].apply(normalize_model_name)
    leads["Sucursal"] = leads["Sucursal"].apply(normalize_branch_name)
    leads["Fecha creación"] = pd.to_datetime(leads["Fecha creación"])
    leads["Fecha cierre"] = pd.to_datetime(leads["Fecha cierre"])
    leads["Mes_cierre"] = leads["Fecha cierre"].dt.to_period("M").dt.to_timestamp()

    pedidos["Modelo"] = pedidos["Modelo"].apply(normalize_model_name)
    pedidos["Fecha pedido"] = pd.to_datetime(pedidos["Fecha pedido"])
    pedidos["Fecha estimada de llegada"] = pd.to_datetime(
        pedidos["Fecha estimada de llegada"]
    )
    pedidos["Fecha de recepción"] = pd.to_datetime(pedidos["Fecha de recepción"])
    pedidos["Versión"] = pedidos["Versión"].astype(str).str.strip()
    pedidos["Color"] = pedidos["Color"].astype(str).str.strip()

    # Identificación y neteo de Notas de Crédito (NC-)
    is_nc = ventas_raw["Factura"].astype(str).str.strip().str.upper().str.startswith(
        "NC-"
    ) | (ventas_raw["Unidades"] < 0)
    ventas_raw["Es_Nota_Credito"] = is_nc
    # Extraer la factura original referenciada en la Nota ("Devolución ref. FAC-xxxxxx")
    ventas_raw["Factura_Ref_NC"] = (
        ventas_raw["Nota"]
        .astype(str)
        .str.extract(r"(FAC-\d+)", expand=False)
    )
    referenced_invoices = set(ventas_raw.loc[is_nc, "Factura_Ref_NC"].dropna().unique())
    ventas_raw["Anulada_Por_NC"] = ventas_raw["Factura"].isin(referenced_invoices)

    # Identificar pedidos especiales de flota fuera de ventana (ej. 60 Hilux y 45 Yaris)
    ventas_raw["Es_Pedido_Especial_Flota"] = ventas_raw["Unidades"] >= 15
    ventas_raw["Ingreso_Bruto_USD"] = (
        ventas_raw["Unidades"] * ventas_raw["Precio unitario (USD)"]
    )

    # Tabla de Ventas Netas Reales (excluyendo las facturas anuladas y sus respectivas NCs
    # cuando son de 1 unidad, o sumando algebraicamente Unidades donde NC = -1)
    # Nota: Algebraicamente en Ventas todas las filas suman exactamente las ventas netas,
    # y adicionalmente marcamos el dataset limpio sin las filas anuladas.
    ventas_netas_sin_anuladas = ventas_raw[
        ~(ventas_raw["Es_Nota_Credito"] | ventas_raw["Anulada_Por_NC"])
    ].copy()

    nc_summary = {
        "total_filas_ventas": int(len(ventas_raw)),
        "notas_credito_filas": int(is_nc.sum()),
        "notas_credito_unidades": int(ventas_raw.loc[is_nc, "Unidades"].sum()),
        "unidades_brutas_facturadas": int(
            ventas_raw.loc[~is_nc, "Unidades"].sum()
        ),
        "unidades_netas_reales": int(ventas_raw["Unidades"].sum()),
        "unidades_flota_especial": int(
            ventas_raw.loc[ventas_raw["Es_Pedido_Especial_Flota"], "Unidades"].sum()
        ),
        "unidades_netas_regulares": int(
            ventas_raw.loc[~ventas_raw["Es_Pedido_Especial_Flota"], "Unidades"].sum()
        ),
        "modelos_originales_sucios": int(ventas_raw["Modelo_raw"].nunique()),
        "modelos_estandarizados": int(ventas_raw["Modelo"].nunique()),
        "sucursales_originales_sucias": int(ventas_raw["Sucursal_raw"].nunique()),
        "sucursales_estandarizadas": int(ventas_raw["Sucursal"].nunique()),
    }

    return {
        "economia": economia,
        "ventas": ventas_raw,
        "ventas_netas_df": ventas_netas_sin_anuladas,
        "inventario": inventario,
        "leads": leads,
        "pedidos": pedidos,
        "comunicados": comunicados,
        "audit_summary": nc_summary,
    }


# ---------------------------------------------------------------------------
# 2. Demanda Insatisfecha (CRM)
# ---------------------------------------------------------------------------

def analyze_unsatisfied_demand(
    leads_df: pd.DataFrame,
    ventas_df: pd.DataFrame,
    weight_recent_12m: float = 0.65,
) -> Dict[str, Any]:
    """
    Agrupa los motivos de pérdida asociados a desabastecimiento en el CRM y calcula
    la demanda mensual no capturada por modelo (histórica 36m, últimos 12m y ponderada).

    Nota operativa: Una oportunidad perdida por stock suele cotizarse o intentarse en más
    de un punto de contacto; por ello se permite parametrizar el factor de conversión
    efectiva de leads de desabastecimiento (`stockout_capture_factor`).
    """
    leads = leads_df.copy()
    leads["Es_Desabastecimiento"] = leads["Motivo de pérdida"].isin(STOCKOUT_REASONS)

    stockout_leads = leads[
        (leads["Resultado"] == "Perdida") & (leads["Es_Desabastecimiento"])
    ].copy()

    # Desglose por motivo de pérdida
    motivos_df = (
        leads[leads["Resultado"] == "Perdida"]
        .groupby(["Motivo de pérdida", "Es_Desabastecimiento"], dropna=False)
        .agg(
            Oportunidades=("ID Oportunidad", "count"),
            Unidades=("Unidades", "sum"),
        )
        .reset_index()
        .sort_values("Unidades", ascending=False)
    )

    # Serie mensual de demanda no capturada por modelo
    monthly_stockout = (
        stockout_leads.groupby(["Mes_cierre", "Modelo de interés"])["Unidades"]
        .sum()
        .unstack(fill_value=0)
        .reindex(columns=OFFICIAL_MODELS, fill_value=0)
    )

    # Ventanas: 36 meses completos (Oct 2023 - Sep 2026) y últimos 12 meses (Oct 2025 - Sep 2026)
    last_12m_cutoff = pd.Timestamp("2025-10-01")
    stockout_12m = stockout_leads[stockout_leads["Fecha cierre"] >= last_12m_cutoff]

    ventas_reg = ventas_df[~ventas_df["Es_Pedido_Especial_Flota"]]
    ventas_12m_reg = ventas_reg[ventas_reg["Fecha"] >= last_12m_cutoff]

    rows = []
    for model in OFFICIAL_MODELS:
        v_36m_total = ventas_df.loc[ventas_df["Modelo"] == model, "Unidades"].sum()
        v_36m_reg = ventas_reg.loc[ventas_reg["Modelo"] == model, "Unidades"].sum()
        v_12m_total = ventas_df.loc[
            (ventas_df["Modelo"] == model) & (ventas_df["Fecha"] >= last_12m_cutoff),
            "Unidades",
        ].sum()
        v_12m_reg = ventas_12m_reg.loc[
            ventas_12m_reg["Modelo"] == model, "Unidades"
        ].sum()

        s_36m = stockout_leads.loc[
            stockout_leads["Modelo de interés"] == model, "Unidades"
        ].sum()
        s_12m = stockout_12m.loc[
            stockout_12m["Modelo de interés"] == model, "Unidades"
        ].sum()

        ventas_mes_36m = v_36m_reg / 36.0
        ventas_mes_12m = v_12m_reg / 12.0
        stockout_mes_36m = s_36m / 36.0
        stockout_mes_12m = s_12m / 12.0

        ventas_mes_pond = (
            weight_recent_12m * ventas_mes_12m
            + (1.0 - weight_recent_12m) * ventas_mes_36m
        )
        stockout_mes_pond = (
            weight_recent_12m * stockout_mes_12m
            + (1.0 - weight_recent_12m) * stockout_mes_36m
        )

        rows.append(
            {
                "Modelo": model,
                "Ventas_Netas_36m_Uds": int(v_36m_total),
                "Ventas_Regulares_36m_Uds": int(v_36m_reg),
                "Ventas_Regulares_12m_Uds": int(v_12m_reg),
                "Ventas_Mensual_36m": round(ventas_mes_36m, 2),
                "Ventas_Mensual_12m": round(ventas_mes_12m, 2),
                "Ventas_Mensual_Ponderada": round(ventas_mes_pond, 2),
                "Demanda_Insatisfecha_36m_Uds": int(s_36m),
                "Demanda_Insatisfecha_12m_Uds": int(s_12m),
                "Demanda_Insatisfecha_Mensual_36m": round(stockout_mes_36m, 2),
                "Demanda_Insatisfecha_Mensual_12m": round(stockout_mes_12m, 2),
                "Demanda_Insatisfecha_Mensual_Pond": round(stockout_mes_pond, 2),
                "Demanda_Real_Mensual_12m": round(
                    ventas_mes_12m + stockout_mes_12m, 2
                ),
                "Demanda_Real_Mensual_Pond": round(
                    ventas_mes_pond + stockout_mes_pond, 2
                ),
            }
        )

    demand_by_model_df = pd.DataFrame(rows)

    return {
        "demand_by_model": demand_by_model_df,
        "motivos_perdida": motivos_df,
        "monthly_stockout": monthly_stockout,
        "stockout_leads_df": stockout_leads,
    }


# ---------------------------------------------------------------------------
# 3. Tránsito y Pipeline
# ---------------------------------------------------------------------------

def analyze_transit_and_inventory(
    pedidos_df: pd.DataFrame,
    inventario_df: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Filtra los pedidos 'En tránsito' al corte (30/09/2026), los clasifica por mes
    estimado de llegada (octubre 2026 a enero 2027) y obtiene el inventario en patio
    al 30/09/2026 con su antigüedad promedio.
    """
    # Inventario al corte 30/09/2026
    inv_corte = inventario_df[inventario_df["Mes (cierre)"] == CUTOFF_DATE].copy()
    inv_by_model = (
        inv_corte.groupby("Modelo")
        .apply(
            lambda g: pd.Series(
                {
                    "Inv_30Sep_Uds": int(g["Unidades"].sum()),
                    "Antiguedad_Promedio_Dias": round(
                        np.average(
                            g["Antigüedad promedio (días)"], weights=g["Unidades"]
                        ),
                        1,
                    )
                    if g["Unidades"].sum() > 0
                    else 0.0,
                    "Uds_Mas_180_Dias": int(
                        g.loc[g["Antigüedad promedio (días)"] > 180, "Unidades"].sum()
                    ),
                }
            ),
            include_groups=False,
        )
        .reindex(OFFICIAL_MODELS, fill_value=0)
        .reset_index()
    )
    inv_by_model["Inv_30Sep_Uds"] = inv_by_model["Inv_30Sep_Uds"].astype(int)
    inv_by_model["Uds_Mas_180_Dias"] = inv_by_model["Uds_Mas_180_Dias"].astype(int)

    # Pedidos en tránsito al corte
    transit = pedidos_df[pedidos_df["Estado"] == "En tránsito"].copy()
    transit["Mes_Llegada"] = (
        transit["Fecha estimada de llegada"].dt.to_period("M").astype(str)
    )

    expected_months = ["2026-10", "2026-11", "2026-12", "2027-01"]
    pivot_transit = (
        transit.pivot_table(
            index="Modelo",
            columns="Mes_Llegada",
            values="Unidades",
            aggfunc="sum",
            fill_value=0,
        )
        .reindex(index=OFFICIAL_MODELS, columns=expected_months, fill_value=0)
        .astype(int)
    )
    pivot_transit["Transito_Oct26_Ene27_Total"] = pivot_transit.sum(axis=1)

    # También desglosar último pedido de julio 2026 vs rezagos de abril 2026
    july_transit = (
        transit[transit["Fecha pedido"] >= "2026-07-01"]
        .groupby("Modelo")["Unidades"]
        .sum()
        .reindex(OFFICIAL_MODELS, fill_value=0)
        .astype(int)
    )
    april_lag_transit = (
        transit[transit["Fecha pedido"] < "2026-07-01"]
        .groupby("Modelo")["Unidades"]
        .sum()
        .reindex(OFFICIAL_MODELS, fill_value=0)
        .astype(int)
    )

    pivot_transit["Transito_Pedido_Jul26"] = july_transit
    pivot_transit["Transito_Rezago_Abr26"] = april_lag_transit
    pivot_transit = pivot_transit.reset_index()

    pipeline_df = pd.merge(inv_by_model, pivot_transit, on="Modelo", how="left")

    return {
        "pipeline_by_model": pipeline_df,
        "transit_detail_df": transit,
        "inventory_cutoff_df": inv_corte,
    }


# ---------------------------------------------------------------------------
# 4. Motor de Pedidos (Ventana Octubre 2026) y Mezcla Óptima Versión/Color
# ---------------------------------------------------------------------------

def apply_lot_rule(
    net_need: float,
    min_order: int,
    multiple: int,
    rounding_mode: str = "ceil",
) -> int:
    """
    Aplica la regla de Lotes y Mínimos de fábrica:
    El pedido debe ser 0 o cumplir (Pedido >= Mínimo y Pedido % Múltiplo == 0).
    """
    if net_need <= 0:
        return 0
    if net_need <= min_order:
        return int(min_order)

    if rounding_mode == "nearest":
        steps = round(net_need / multiple)
    elif rounding_mode == "floor":
        steps = math.floor(net_need / multiple)
    else:  # "ceil" garantiza cobertura sin desabastecimiento
        steps = math.ceil(net_need / multiple)

    order_qty = max(min_order, int(steps * multiple))
    return order_qty


def optimize_october_2026_order(
    data: Dict[str, Any],
    safety_stock_months: float = 1.0,
    stockout_capture_factor: float = 0.50,
    weight_recent_12m: float = 0.65,
    rounding_mode: str = "ceil",
    rav4_controlled_phaseout: bool = True,
) -> Dict[str, Any]:
    """
    Ejecuta el motor de optimización de pedidos para la ventana de Octubre 2026:
    - Lead time = 4 meses (pedido en octubre 2026 llega a inicios de febrero 2027).
    - Cubre la demanda de Feb, Mar y Abr 2027 (3 meses) + Stock de Seguridad.
    - Proyecta el inventario al 31 de enero de 2027:
      Inv_31Ene27 = max(0, Inv_30Sep26 + Tránsito_Oct26_Ene27 - Demanda_Oct26_Ene27).
    - Aplica la Regla Crítica RAV4 (Comunicado 15/09/2026): liquidación controlada
      para que el stock remanente de la generación actual tienda a 0 al 30/04/2027
      antes de la llegada de la nueva generación en mayo 2027.
    - Calcula Capital Comprometido (USD), Ingreso Esperado (USD), Margen Bruto (USD)
      y Costo Financiero Mensual de Plan Piso (0.9%).
    """
    economia = data["economia"].set_index("Modelo")
    demand_info = analyze_unsatisfied_demand(
        data["leads"], data["ventas"], weight_recent_12m=weight_recent_12m
    )
    demand_df = demand_info["demand_by_model"].set_index("Modelo")
    pipeline_info = analyze_transit_and_inventory(data["pedidos"], data["inventario"])
    pipeline_df = pipeline_info["pipeline_by_model"].set_index("Modelo")

    results = []
    for model in OFFICIAL_MODELS:
        inv_sep = int(pipeline_df.loc[model, "Inv_30Sep_Uds"])
        trans_total = int(pipeline_df.loc[model, "Transito_Oct26_Ene27_Total"])
        trans_jul = int(pipeline_df.loc[model, "Transito_Pedido_Jul26"])

        v_mes = float(demand_df.loc[model, "Ventas_Mensual_Ponderada"])
        s_mes = float(demand_df.loc[model, "Demanda_Insatisfecha_Mensual_Pond"])
        demanda_mensual_objetivo = v_mes + stockout_capture_factor * s_mes

        # Demanda durante el lead time (Oct 2026 - Ene 2027: 4 meses)
        # Nota: durante Oct26-Ene27 las ventas están físicamente limitadas por la disponibilidad
        demanda_4m_oct_ene = 4.0 * demanda_mensual_objetivo
        balance_bruto_31ene = inv_sep + trans_total - demanda_4m_oct_ene
        inv_proy_31ene = max(0.0, balance_bruto_31ene)
        deficit_oct_ene = max(0.0, -balance_bruto_31ene)

        # Demanda del ciclo objetivo (Feb 2027 - Abr 2027: 3 meses)
        demanda_3m_feb_abr = 3.0 * demanda_mensual_objetivo

        # Stock de seguridad objetivo al 30/04/2027
        if model == "RAV4" and rav4_controlled_phaseout:
            # Regla Crítica RAV4: Liquidación controlada hacia 0 al 30/04/2027
            ss_target = 0.0
        else:
            ss_target = safety_stock_months * demanda_mensual_objetivo

        necesidad_bruta_feb_abr = demanda_3m_feb_abr + ss_target
        necesidad_neta = max(0.0, necesidad_bruta_feb_abr - inv_proy_31ene)

        min_lot, mult_lot = LOT_RULES[model]

        if model == "RAV4" and rav4_controlled_phaseout:
            # Con 9 en patio + 47 en tránsito (44 de PF-41141 + 3 de PF-41130) = 56 uds disponibles
            # para 7 meses (Oct26-Abr27, ~8 uds/mes), pedir más unidades dejaría inventario
            # obsoleto sin apoyo de fábrica en mayo 2027. Se fuerza liquidación controlada (Pedido = 0).
            pedido_sugerido = 0
            # Ritmo mensual necesario en los 7 meses (Oct26-Abr27) para que el stock tienda a 0:
            ritmo_liquidacion_mensual = (inv_sep + trans_total) / 7.0
            stock_final_30abr = max(
                0.0, (inv_sep + trans_total) - 7.0 * max(demanda_mensual_objetivo, ritmo_liquidacion_mensual)
            )
            nota_regla = (
                f"Liquidación controlada Gen. Actual (9 patio + {trans_total} tránsito "
                f"[{trans_jul} pedido Jul] = {inv_sep + trans_total} uds; meta ~{(inv_sep + trans_total)/7:.1f} uds/mes "
                f"para stock 0 al 30/04/2027)"
            )
        else:
            pedido_sugerido = apply_lot_rule(
                necesidad_neta, min_lot, mult_lot, rounding_mode=rounding_mode
            )
            stock_final_30abr = max(
                0.0, inv_proy_31ene + pedido_sugerido - demanda_3m_feb_abr
            )
            if deficit_oct_ene > 0:
                nota_regla = f"Riesgo quiebre pre-arribo ({deficit_oct_ene:.1f} uds en Oct-Ene); Lote ({min_lot}/{mult_lot})"
            else:
                nota_regla = f"Cobertura normal 3M + {safety_stock_months:.1f}M SS; Lote ({min_lot}/{mult_lot})"

        precio_prom = float(economia.loc[model, "Precio promedio (USD)"])
        margen_pct = float(economia.loc[model, "Margen bruto %"])
        costo_unit = float(economia.loc[model, "Costo unitario promedio (USD)"])
        costo_fin_unit = float(
            economia.loc[model, "Costo financiero mensual por unidad (USD)"]
        )

        capital_comprometido = pedido_sugerido * costo_unit
        ingreso_esperado = pedido_sugerido * precio_prom
        margen_bruto_usd = pedido_sugerido * (precio_prom - costo_unit)
        # Costo financiero mensual del lote al llegar (0.9% sobre capital comprometido)
        costo_plan_piso_mensual = capital_comprometido * FLOORPLAN_MONTHLY_RATE
        # Costo financiero estimado durante el ciclo de rotación promedio del lote (~2 meses en patio)
        meses_estancia_media = (
            (inv_proy_31ene + stock_final_30abr) / (2.0 * demanda_mensual_objetivo)
            if demanda_mensual_objetivo > 0
            else 0.0
        )

        results.append(
            {
                "Modelo": model,
                "Lote_Min_Mult": f"{min_lot} / {mult_lot}",
                "Inv_30Sep": inv_sep,
                "Transito_Oct26_Ene27": trans_total,
                "Transito_Pedido_Jul26": trans_jul,
                "Ventas_Mensual_Base": round(v_mes, 2),
                "Demanda_Insatisfecha_Mensual": round(s_mes, 2),
                "Demanda_Mensual_Planificada": round(demanda_mensual_objetivo, 2),
                "Demanda_Oct26_Ene27_4M": round(demanda_4m_oct_ene, 1),
                "Balance_Bruto_31Ene27": round(balance_bruto_31ene, 1),
                "Inv_Proyectado_31Ene27": round(inv_proy_31ene, 1),
                "Deficit_Oct26_Ene27": round(deficit_oct_ene, 1),
                "Demanda_Feb27_Abr27_3M": round(demanda_3m_feb_abr, 1),
                "Stock_Seguridad_Objetivo": round(ss_target, 1),
                "Necesidad_Neta_Feb_Abr": round(necesidad_neta, 1),
                "Pedido_Sugerido_Oct26": int(pedido_sugerido),
                "Inv_Proyectado_30Abr27": round(stock_final_30abr, 1),
                "Meses_Cobertura_30Abr27": round(
                    stock_final_30abr / demanda_mensual_objetivo, 2
                )
                if demanda_mensual_objetivo > 0
                else 0.0,
                "Costo_Unitario_USD": costo_unit,
                "Precio_Promedio_USD": precio_prom,
                "Margen_Bruto_Pct": margen_pct,
                "Capital_Comprometido_USD": round(capital_comprometido, 2),
                "Ingreso_Esperado_USD": round(ingreso_esperado, 2),
                "Margen_Bruto_Esperado_USD": round(margen_bruto_usd, 2),
                "Costo_Plan_Piso_Mensual_USD": round(costo_plan_piso_mensual, 2),
                "Costo_Fin_Unitario_Tabla_USD": costo_fin_unit,
                "Meses_Estancia_Media_Proy": round(meses_estancia_media, 2),
                "Regla_Aplicada": nota_regla,
            }
        )

    order_df = pd.DataFrame(results)

    # Totales financieros y operativos del pedido
    totals = {
        "total_unidades_pedidas": int(order_df["Pedido_Sugerido_Oct26"].sum()),
        "total_inv_30sep": int(order_df["Inv_30Sep"].sum()),
        "total_transito_oct_ene": int(order_df["Transito_Oct26_Ene27"].sum()),
        "total_capital_comprometido_usd": float(
            order_df["Capital_Comprometido_USD"].sum()
        ),
        "total_ingreso_esperado_usd": float(order_df["Ingreso_Esperado_USD"].sum()),
        "total_margen_bruto_esperado_usd": float(
            order_df["Margen_Bruto_Esperado_USD"].sum()
        ),
        "total_costo_plan_piso_mensual_usd": float(
            order_df["Costo_Plan_Piso_Mensual_USD"].sum()
        ),
        "margen_bruto_ponderado_pct": float(
            order_df["Margen_Bruto_Esperado_USD"].sum()
            / order_df["Ingreso_Esperado_USD"].sum()
        )
        if order_df["Ingreso_Esperado_USD"].sum() > 0
        else 0.0,
        "rav4_unidades_a_liquidar_oct_abr": int(
            order_df.loc[order_df["Modelo"] == "RAV4", "Inv_30Sep"].iloc[0]
            + order_df.loc[order_df["Modelo"] == "RAV4", "Transito_Oct26_Ene27"].iloc[0]
        ),
    }

    # Calcular mezcla óptima de versiones y colores para los modelos con pedido > 0
    mix_df, version_summary_df = suggest_version_color_mix(
        data["ventas"], data["leads"], order_df
    )

    # Proyección mensual de inventario vs demanda (Sep 2026 a Abr 2027)
    monthly_proj_df = project_monthly_inventory_curve(
        order_df, pipeline_info["pipeline_by_model"]
    )

    return {
        "order_recommendations": order_df,
        "order_totals": totals,
        "version_color_mix": mix_df,
        "version_mix_summary": version_summary_df,
        "monthly_projection_df": monthly_proj_df,
        "demand_analysis": demand_info,
        "pipeline_analysis": pipeline_info,
    }


def project_monthly_inventory_curve(
    order_df: pd.DataFrame,
    pipeline_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Construye la curva proyectada mes a mes (Sep 2026 a Abr 2027) de inventario
    en patio, llegadas de tránsito/pedido y demanda mensual por modelo.
    """
    pipe_idx = pipeline_df.set_index("Modelo")
    ord_idx = order_df.set_index("Modelo")

    months_meta = [
        ("2026-09", "Sep 2026 (Corte)"),
        ("2026-10", "Oct 2026"),
        ("2026-11", "Nov 2026"),
        ("2026-12", "Dic 2026"),
        ("2027-01", "Ene 2027"),
        ("2027-02", "Feb 2027 (Arribo Oct)"),
        ("2027-03", "Mar 2027"),
        ("2027-04", "Abr 2027 (Cierre Ciclo)"),
    ]

    rows = []
    for model in OFFICIAL_MODELS:
        inv_curr = float(ord_idx.loc[model, "Inv_30Sep"])
        dem_mes = float(ord_idx.loc[model, "Demanda_Mensual_Planificada"])
        pedido_oct = float(ord_idx.loc[model, "Pedido_Sugerido_Oct26"])

        rows.append(
            {
                "Modelo": model,
                "Periodo": "2026-09",
                "Etiqueta_Mes": "Sep 2026 (Corte)",
                "Orden_Mes": 0,
                "Llegadas_Uds": 0.0,
                "Demanda_Mensual_Uds": round(dem_mes, 2),
                "Inventario_Cierre_Uds": round(inv_curr, 1),
            }
        )

        for idx_m, (m_code, m_label) in enumerate(months_meta[1:], start=1):
            if m_code in ["2026-10", "2026-11", "2026-12", "2027-01"]:
                arrivals = float(pipe_idx.loc[model, m_code])
            elif m_code == "2027-02":
                arrivals = pedido_oct
            else:
                arrivals = 0.0

            inv_curr = max(0.0, inv_curr + arrivals - dem_mes)
            rows.append(
                {
                    "Modelo": model,
                    "Periodo": m_code,
                    "Etiqueta_Mes": m_label,
                    "Orden_Mes": idx_m,
                    "Llegadas_Uds": round(arrivals, 1),
                    "Demanda_Mensual_Uds": round(dem_mes, 2),
                    "Inventario_Cierre_Uds": round(inv_curr, 1),
                }
            )

    return pd.DataFrame(rows)


def export_caso1_plan_to_excel_bytes(pipeline_result: Dict[str, Any]) -> bytes:
    """
    Genera un archivo Excel en memoria (bytes) con el Plan Consolidado de Pedidos
    Octubre 2026, listo para descarga desde Streamlit (`st.download_button`).
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # 1. Tabla Maestra de Pedidos
        pipeline_result["order_recommendations"].to_excel(
            writer, sheet_name="1_Tabla_Maestra_Pedidos", index=False
        )
        # 2. Mezcla recomendada por Versión y Color (solo modelos con pedido > 0 o todos)
        pipeline_result["version_color_mix"].to_excel(
            writer, sheet_name="2_Mezcla_Version_Color", index=False
        )
        # 3. Resumen por Versión
        pipeline_result["version_mix_summary"].to_excel(
            writer, sheet_name="3_Resumen_Versiones", index=False
        )
        # 4. Proyección Mensual de Inventario
        pipeline_result["monthly_projection_df"].to_excel(
            writer, sheet_name="4_Proyeccion_Mensual_Inv", index=False
        )
        # 5. Demanda Insatisfecha CRM
        pipeline_result["demand_analysis"]["demand_by_model"].to_excel(
            writer, sheet_name="5_Demanda_CRM_Stockout", index=False
        )
        # 6. Tránsito y Patio al Corte
        pipeline_result["pipeline_analysis"]["pipeline_by_model"].to_excel(
            writer, sheet_name="6_Pipeline_Transito", index=False
        )
    return output.getvalue()


def _largest_remainder_allocation(weights: np.ndarray, total_units: int) -> np.ndarray:
    """
    Asigna `total_units` unidades enteras según un vector de pesos usando el método de
    Restos Mayores (Hamilton / Largest Remainder), garantizando que la suma exacta
    coincida con `total_units`.
    """
    if total_units <= 0 or len(weights) == 0:
        return np.zeros(len(weights), dtype=int)
    w_sum = float(np.sum(weights))
    if w_sum <= 0:
        probs = np.ones(len(weights)) / len(weights)
    else:
        probs = weights / w_sum

    exact = probs * total_units
    floors = np.floor(exact).astype(int)
    remainder = int(total_units - np.sum(floors))
    if remainder > 0:
        fractions = exact - floors
        top_indices = np.argsort(-fractions)[:remainder]
        floors[top_indices] += 1
    return floors


def suggest_version_color_mix(
    ventas_df: pd.DataFrame,
    leads_df: pd.DataFrame,
    order_df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Sugiere la mezcla óptima de versiones y colores por modelo según su rotación
    histórica (ventas netas regulares + ajuste por demanda insatisfecha en CRM).
    """
    # Filtramos ventas regulares (sin los 2 pedidos especiales de flota de 60 y 45 uds)
    v_reg = ventas_df[~ventas_df["Es_Pedido_Especial_Flota"]].copy()

    # Pesos por Modelo + Versión + Color en ventas históricas
    vc_sales = (
        v_reg.groupby(["Modelo", "Versión", "Color"])["Unidades"]
        .sum()
        .reset_index()
        .rename(columns={"Unidades": "Ventas_Hist_Uds"})
    )
    vc_sales["Ventas_Hist_Uds"] = vc_sales["Ventas_Hist_Uds"].clip(lower=0)

    # Incorporar demanda insatisfecha por Modelo + Versión en CRM para reforzar versiones escasas
    stockout_leads = leads_df[
        (leads_df["Resultado"] == "Perdida")
        & (leads_df["Motivo de pérdida"].isin(STOCKOUT_REASONS))
    ]
    v_stockout = (
        stockout_leads.groupby(["Modelo de interés", "Versión de interés"])["Unidades"]
        .sum()
        .reset_index()
        .rename(
            columns={
                "Modelo de interés": "Modelo",
                "Versión de interés": "Versión",
                "Unidades": "Leads_Stockout_Version_Uds",
            }
        )
    )

    vc_merged = pd.merge(vc_sales, v_stockout, on=["Modelo", "Versión"], how="left")
    vc_merged["Leads_Stockout_Version_Uds"] = vc_merged[
        "Leads_Stockout_Version_Uds"
    ].fillna(0)

    # Distribuir el refuerzo de stockout de la versión proporcionalmente entre sus colores
    version_totals = vc_merged.groupby(["Modelo", "Versión"])[
        "Ventas_Hist_Uds"
    ].transform("sum")
    color_share_in_version = np.where(
        version_totals > 0, vc_merged["Ventas_Hist_Uds"] / version_totals, 0.0
    )
    vc_merged["Score_Rotacion"] = (
        vc_merged["Ventas_Hist_Uds"]
        + 0.5 * vc_merged["Leads_Stockout_Version_Uds"] * color_share_in_version
    )

    order_map = order_df.set_index("Modelo")["Pedido_Sugerido_Oct26"].to_dict()

    mix_rows = []
    for model in OFFICIAL_MODELS:
        sub = vc_merged[vc_merged["Modelo"] == model].copy()
        if sub.empty:
            continue
        sub = sub.sort_values(["Score_Rotacion", "Ventas_Hist_Uds"], ascending=False)
        total_model_sales = sub["Ventas_Hist_Uds"].sum()
        total_model_score = sub["Score_Rotacion"].sum()
        pedido_m = int(order_map.get(model, 0))

        alloc = _largest_remainder_allocation(
            sub["Score_Rotacion"].to_numpy(), pedido_m
        )
        sub["Share_Ventas_Hist_Pct"] = (
            (sub["Ventas_Hist_Uds"] / total_model_sales * 100.0).round(2)
            if total_model_sales > 0
            else 0.0
        )
        sub["Share_Optimo_Pct"] = (
            (sub["Score_Rotacion"] / total_model_score * 100.0).round(2)
            if total_model_score > 0
            else 0.0
        )
        sub["Pedido_Sugerido_Modelo"] = pedido_m
        sub["Unidades_Sugeridas"] = alloc
        mix_rows.append(sub)

    mix_df = pd.concat(mix_rows, ignore_index=True)

    version_summary_df = (
        mix_df.groupby(["Modelo", "Versión"], as_index=False)
        .agg(
            Ventas_Hist_Uds=("Ventas_Hist_Uds", "sum"),
            Leads_Stockout_Uds=("Leads_Stockout_Version_Uds", "first"),
            Share_Ventas_Hist_Pct=("Share_Ventas_Hist_Pct", "sum"),
            Share_Optimo_Pct=("Share_Optimo_Pct", "sum"),
            Pedido_Sugerido_Modelo=("Pedido_Sugerido_Modelo", "first"),
            Unidades_Sugeridas=("Unidades_Sugeridas", "sum"),
        )
        .sort_values(["Modelo", "Unidades_Sugeridas", "Ventas_Hist_Uds"], ascending=[True, False, False])
    )

    return mix_df, version_summary_df


def run_caso1_pipeline(
    excel_path: Optional[str | Path] = None,
    safety_stock_months: float = 1.0,
    stockout_capture_factor: float = 0.50,
    weight_recent_12m: float = 0.65,
    rounding_mode: str = "ceil",
    rav4_controlled_phaseout: bool = True,
) -> Dict[str, Any]:
    """
    Punto de entrada integral para la interfaz gráfica o notebooks del Caso 1.
    Devuelve todos los DataFrames limpios, tablas del motor S&OP y métricas ejecutivas.
    """
    raw_and_clean = load_and_clean_caso1(excel_path=excel_path)
    opt = optimize_october_2026_order(
        raw_and_clean,
        safety_stock_months=safety_stock_months,
        stockout_capture_factor=stockout_capture_factor,
        weight_recent_12m=weight_recent_12m,
        rounding_mode=rounding_mode,
        rav4_controlled_phaseout=rav4_controlled_phaseout,
    )
    return {
        **raw_and_clean,
        **opt,
    }


if __name__ == "__main__":
    res = run_caso1_pipeline()
    print("=== AUDITORIA CASO 1 ===")
    for k, v in res["audit_summary"].items():
        print(f"  {k}: {v}")
    print("\n=== TABLA MAESTRA DE PEDIDO OCTUBRE 2026 ===")
    cols = [
        "Modelo",
        "Inv_30Sep",
        "Transito_Oct26_Ene27",
        "Demanda_Mensual_Planificada",
        "Inv_Proyectado_31Ene27",
        "Necesidad_Neta_Feb_Abr",
        "Lote_Min_Mult",
        "Pedido_Sugerido_Oct26",
        "Capital_Comprometido_USD",
        "Margen_Bruto_Esperado_USD",
        "Costo_Plan_Piso_Mensual_USD",
    ]
    print(res["order_recommendations"][cols].to_string(index=False))
    print("\n=== TOTALES DEL PEDIDO ===")
    for k, v in res["order_totals"].items():
        print(f"  {k}: {v:,.2f}" if isinstance(v, float) else f"  {k}: {v}")

