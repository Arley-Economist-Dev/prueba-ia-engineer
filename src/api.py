"""
Capa de Servicios REST de Alto Rendimiento (FastAPI)
Conecta en memoria los motores matemáticos de Caso 1 (src/caso1_engine.py) y
Caso 2 (src/caso2_engine.py) para responder en sub-milisegundos al cliente SPA.
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any, Dict, Optional

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse

from src.caso1_engine import (
    OFFICIAL_MODELS,
    export_caso1_plan_to_excel_bytes,
    load_and_clean_caso1,
    optimize_october_2026_order,
)
from src.caso2_engine import (
    diagnose_bottleneck,
    generate_copilot_recommendation,
    load_and_clean_caso2,
    simulate_three_lane_architecture,
    train_churn_model_and_score,
)

router = APIRouter(prefix="/api", tags=["Casa Pellas AI Suite API"])

# ---------------------------------------------------------------------------
# Caché en Memoria (Singleton) para Respuesta Instantánea (<25ms)
# ---------------------------------------------------------------------------

_CASO1_BASE_CACHE: Optional[Dict[str, Any]] = None
_CASO2_BUNDLE_CACHE: Optional[Dict[str, Any]] = None


def get_caso1_cached() -> Dict[str, Any]:
    global _CASO1_BASE_CACHE
    if _CASO1_BASE_CACHE is None:
        _CASO1_BASE_CACHE = load_and_clean_caso1()
    return _CASO1_BASE_CACHE


def get_caso2_cached() -> Dict[str, Any]:
    global _CASO2_BUNDLE_CACHE
    if _CASO2_BUNDLE_CACHE is None:
        cleaned = load_and_clean_caso2()
        diagnosis = diagnose_bottleneck(
            cleaned["renovaciones"],
            cleaned["bitacora"],
            cleaned["equipo"],
            renovaciones_raw_df=cleaned["renovaciones_raw"],
        )
        ml_results = train_churn_model_and_score(
            cleaned["renovaciones"],
            model_type="logistic",
        )
        _CASO2_BUNDLE_CACHE = {
            **cleaned,
            "diagnosis": diagnosis,
            "ml_results": ml_results,
        }
    return _CASO2_BUNDLE_CACHE


def warmup_engines() -> None:
    """Pre-carga ambos motores en memoria al arrancar FastAPI."""
    get_caso1_cached()
    get_caso2_cached()


# ---------------------------------------------------------------------------
# 1. Endpoints Caso 1 · Pedidos Inteligentes Toyota
# ---------------------------------------------------------------------------

@router.get("/caso1/pedidos")
def api_caso1_pedidos(
    safety_days: int = Query(30, ge=0, le=120, description="Días de stock de seguridad"),
    crm_capture_pct: int = Query(
        50, ge=0, le=100, description="% de captura de demanda insatisfecha CRM"
    ),
    rav4_phaseout: bool = Query(
        True, description="Activar liquidación controlada de RAV4 generación actual"
    ),
) -> Dict[str, Any]:
    base_data = get_caso1_cached()
    safety_months = safety_days / 30.0
    capture_factor = crm_capture_pct / 100.0

    plan = optimize_october_2026_order(
        base_data,
        safety_stock_months=safety_months,
        stockout_capture_factor=capture_factor,
        weight_recent_12m=0.65,
        rounding_mode="ceil",
        rav4_controlled_phaseout=rav4_phaseout,
    )

    order_df = plan["order_recommendations"]
    rav4_row = order_df[order_df["Modelo"] == "RAV4"].iloc[0]
    rav4_order_qty = int(rav4_row["Pedido_Sugerido_Oct26"])
    rav4_end_stock = float(rav4_row["Inv_Proyectado_30Abr27"])
    rav4_exposure_usd = round(rav4_end_stock * float(rav4_row["Costo_Unitario_USD"]), 2)

    return {
        "parameters": {
            "safety_days": safety_days,
            "crm_capture_pct": crm_capture_pct,
            "rav4_phaseout": rav4_phaseout,
        },
        "audit_summary": base_data["audit_summary"],
        "totals": {
            **plan["order_totals"],
            "rav4_order_qty": rav4_order_qty,
            "rav4_end_stock_abr27": rav4_end_stock,
            "rav4_obsolescence_exposure_usd": rav4_exposure_usd,
        },
        "official_models": OFFICIAL_MODELS,
        "models": order_df.to_dict(orient="records"),
        "monthly_projection": plan["monthly_projection_df"].to_dict(orient="records"),
        "version_color_mix": plan["version_color_mix"].to_dict(orient="records"),
        "version_summary": plan["version_mix_summary"].to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# 2. Endpoints Caso 2 · Orquestador de Renovaciones Capesa
# ---------------------------------------------------------------------------

@router.get("/caso2/diagnostico")
def api_caso2_diagnostico() -> Dict[str, Any]:
    bundle = get_caso2_cached()
    diag = bundle["diagnosis"]
    ml = bundle["ml_results"]

    monthly_df = diag["monthly_evolution"].copy()
    monthly_df["Mes_Str"] = monthly_df["Mes_Vencimiento"].dt.strftime("%Y-%m")
    monthly_df = monthly_df.drop(columns=["Mes_Vencimiento"])

    equipo_df = diag["equipo_performance"].copy()
    for col in ["Fecha de ingreso al área", "Fecha de salida"]:
        if col in equipo_df.columns:
            equipo_df[col] = (
                pd.to_datetime(equipo_df[col]).dt.strftime("%Y-%m-%d").fillna("Activo")
            )
    equipo_df = equipo_df.fillna("")

    return {
        "audit_summary": bundle["audit_summary"],
        "key_findings": diag["key_findings"],
        "model_metrics": ml["model_metrics"],
        "anticipation_curve": diag["anticipation_curve"].to_dict(orient="records"),
        "payment_efficiency": diag["payment_efficiency"].to_dict(orient="records"),
        "structural_break": diag["structural_break"].to_dict(orient="records"),
        "monthly_evolution": monthly_df.to_dict(orient="records"),
        "motivos_no_renovacion": diag["motivos_no_renovacion"]
        .fillna(0)
        .to_dict(orient="records"),
        "feature_importance": ml["feature_importance_df"].to_dict(orient="records"),
        "decile_lift": ml["decile_lift_table"].to_dict(orient="records"),
        "equipo": equipo_df.to_dict(orient="records"),
    }


import pandas as pd


@router.get("/caso2/priorizacion")
def api_caso2_priorizacion(
    gestor: str = Query("ALL", description="Código de gestor (ALL, G01..G05)"),
    ramo: str = Query("ALL", description="Ramo (ALL, Autos, Médico, Daños / Hogar, Vida)"),
    only_at_risk: bool = Query(True, description="Solo pólizas no renovadas / en riesgo"),
    limit: int = Query(100, ge=10, le=500, description="Máximo de filas a retornar"),
    target_contact_days: int = Query(
        22, ge=10, le=25, description="Días de anticipación asegurados por Bot T-25"
    ),
    ai_closure_pct: int = Query(
        35, ge=10, le=70, description="% de auto-cierre digital del Bot en bajo riesgo"
    ),
    human_uplift_pct: int = Query(
        6, ge=0, le=25, description="% de efectividad adicional de negociación humana"
    ),
) -> Dict[str, Any]:
    bundle = get_caso2_cached()
    ml = bundle["ml_results"]
    equipo_df = bundle["equipo"]

    sim_res = simulate_three_lane_architecture(
        bundle["renovaciones"],
        ml,
        target_contact_days=target_contact_days,
        ai_agent_closure_share_low_risk=ai_closure_pct / 100.0,
        human_retention_uplift_high_value=human_uplift_pct / 100.0,
        zero_touch_recovery_rate=0.25,
    )

    active_codes = ["G01", "G02", "G03", "G04", "G05"]
    gestores_list = [
        {"codigo": r["Código"], "nombre": r["Nombre"], "label": f"{r['Código']} · {r['Nombre']}"}
        for _, r in equipo_df[equipo_df["Código"].isin(active_codes)].iterrows()
    ]

    df = ml["bandeja_priorizada_df"].copy()
    df = df[df["Gestor"].isin(active_codes)]

    if gestor and gestor != "ALL":
        df = df[df["Gestor"] == gestor]
    if ramo and ramo != "ALL":
        df = df[df["Ramo"] == ramo]
    if only_at_risk:
        df = df[df["Fuga_Bin"] == 1]

    total_matching = int(len(df))
    total_risk_matching_usd = round(float(df["Valor_En_Riesgo_USD"].sum()), 2)

    sub = df.head(limit).copy()
    policies_out = []
    for _, r in sub.iterrows():
        policies_out.append(
            {
                "poliza": str(r["Póliza"]),
                "ranking": int(r["Ranking_Prioridad"]),
                "gestor": str(r["Gestor"]),
                "cliente_id": str(r["ID cliente"]),
                "telefono": str(r["Teléfono cliente"]),
                "ramo": str(r["Ramo"]),
                "segmento": str(r["Segmento"]),
                "aseguradora": str(r["Aseguradora"]),
                "origen": str(r["Origen"]),
                "fecha_vencimiento": pd.to_datetime(r["Fecha de vencimiento"]).strftime(
                    "%Y-%m-%d"
                ),
                "dias_anticipacion": None
                if pd.isna(r["dias_anticipacion"])
                else int(r["dias_anticipacion"]),
                "antiguedad_anios": int(r["Antigüedad del cliente (años)"]),
                "siniestros_ultimo_anio": int(r["Siniestros último año"]),
                "prima_anterior_usd": round(float(r["Prima anterior (USD)"]), 2),
                "prima_renovacion_usd": round(float(r["Prima de renovación (USD)"]), 2),
                "cambio_prima_pct": round(float(r["% cambio de prima"]) * 100.0, 1),
                "comision_pct": round(float(r["% comisión"]) * 100.0, 1),
                "comision_potencial_usd": round(
                    float(r["Comision_Renovacion_USD"]), 2
                ),
                "p_fuga_pct": round(float(r["P_Fuga"]) * 100.0, 1),
                "valor_en_riesgo_usd": round(float(r["Valor_En_Riesgo_USD"]), 2),
                "segmento_prioridad": str(r["Segmento_Prioridad"]),
            }
        )

    return {
        "filters": {
            "gestor": gestor,
            "ramo": ramo,
            "only_at_risk": only_at_risk,
            "total_matching_policies": total_matching,
            "total_matching_risk_usd": total_risk_matching_usd,
        },
        "gestores_list": gestores_list,
        "simulation_metrics": sim_res["simulation_metrics"],
        "lanes_summary": sim_res["lanes_summary_df"].to_dict(orient="records"),
        "policies": policies_out,
    }


@router.get("/caso2/copiloto/{poliza_id}")
def api_caso2_copiloto(poliza_id: str) -> Dict[str, Any]:
    bundle = get_caso2_cached()
    bandeja = bundle["ml_results"]["bandeja_priorizada_df"]
    match = bandeja[bandeja["Póliza"] == poliza_id]
    if match.empty:
        # Buscar en toda la base de renovaciones si no está en Manual
        all_ren = bundle["renovaciones"]
        match = all_ren[all_ren["Póliza"] == poliza_id]
        if match.empty:
            raise HTTPException(
                status_code=404, detail=f"Póliza '{poliza_id}' no encontrada."
            )

    row = match.iloc[0]
    cop = generate_copilot_recommendation(
        row,
        bundle["renovaciones"],
        equipo_df=bundle["equipo"],
    )
    return {
        **{k: v for k, v in cop.items() if k != "cotizaciones_df"},
        "cotizaciones": cop["cotizaciones_df"].to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# 3. Endpoints de Exportación Directa a Excel
# ---------------------------------------------------------------------------

@router.get("/exportar/caso1")
def api_exportar_caso1(
    safety_days: int = Query(30, ge=0, le=120),
    crm_capture_pct: int = Query(50, ge=0, le=100),
    rav4_phaseout: bool = Query(True),
):
    # Si son los parámetros base y existe el archivo precalculado en outputs/, servirlo o generarlo al vuelo
    static_path = Path("outputs/Pedido_Recomendado_Octubre_2026.xlsx")
    if (
        safety_days == 30
        and crm_capture_pct == 50
        and rav4_phaseout is True
        and static_path.exists()
    ):
        return FileResponse(
            path=str(static_path),
            filename="Pedido_Recomendado_Octubre_2026.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    base_data = get_caso1_cached()
    plan = optimize_october_2026_order(
        base_data,
        safety_stock_months=safety_days / 30.0,
        stockout_capture_factor=crm_capture_pct / 100.0,
        weight_recent_12m=0.65,
        rounding_mode="ceil",
        rav4_controlled_phaseout=rav4_phaseout,
    )
    excel_bytes = export_caso1_plan_to_excel_bytes({**base_data, **plan})
    filename = f"Pedido_Recomendado_Octubre_2026_SS{safety_days}d_CRM{crm_capture_pct}pct.xlsx"
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/exportar/caso2")
def api_exportar_caso2():
    static_path = Path("outputs/Bandeja_Priorizada_Capesa.xlsx")
    if not static_path.exists():
        raise HTTPException(
            status_code=404,
            detail="El archivo outputs/Bandeja_Priorizada_Capesa.xlsx no existe. Ejecute test_pipeline.py.",
        )
    return FileResponse(
        path=str(static_path),
        filename="Bandeja_Priorizada_Capesa.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

