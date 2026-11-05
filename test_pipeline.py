"""
Script de Validación Integral (QA) y Exportación de Entregables de Soporte.
Valida la reproducibilidad técnica de:
- Caso 1: Pedido de Vehículos Nuevos Toyota (Casa Pellas)
- Caso 2: Renovaciones de Pólizas en Capesa
Genera los archivos Excel consolidados en outputs/ y verifica sumas de control.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
import pandas as pd
import numpy as np

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

from src.caso1_engine import (
    OFFICIAL_MODELS,
    OFFICIAL_BRANCHES,
    run_caso1_pipeline,
)
from src.caso2_engine import (
    run_caso2_pipeline,
    TARGET_ANTICIPATION_DAYS,
)

def run_tests_and_export():
    print("=" * 70)
    print("INICIANDO SUITE DE PRUEBAS DE REPRODUCIBILIDAD (QA & DEVOPS)")
    print("=" * 70)

    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # 1. VALIDACIÓN CASO 1 · VEHÍCULOS NUEVOS
    # -----------------------------------------------------------------------
    print("\n[QA] Ejecutando Caso 1 (S&OP Toyota)...")
    res1 = run_caso1_pipeline()

    audit1 = res1["audit_summary"]
    order_df = res1["order_recommendations"]
    totals1 = res1["order_totals"]
    proj_df = res1["monthly_projection_df"]
    mix_df = res1["version_color_mix"]

    print("  -> Verificando sumas de control Caso 1...")
    # Exactamente 11 modelos oficiales
    assert len(order_df) == 11, f"Error: Se esperaban 11 modelos, se obtuvieron {len(order_df)}"
    assert set(order_df["Modelo"]) == set(OFFICIAL_MODELS), "Error: Nombres de modelos no coinciden con los oficiales"

    # Verificación de Notas de Crédito
    assert audit1["notas_credito_filas"] == 9, f"Error en conteo NC: {audit1['notas_credito_filas']} != 9"
    assert audit1["notas_credito_unidades"] == -9, f"Error en unidades NC: {audit1['notas_credito_unidades']} != -9"
    assert audit1["unidades_netas_reales"] == 5204, f"Error en unidades netas: {audit1['unidades_netas_reales']} != 5204"
    assert audit1["sucursales_estandarizadas"] == 7, f"Error: sucursales {audit1['sucursales_estandarizadas']} != 7"

    # Regla crítica RAV4
    rav4_order = int(order_df.loc[order_df["Modelo"] == "RAV4", "Pedido_Sugerido_Oct26"].iloc[0])
    assert rav4_order == 0, f"Error: Pedido RAV4 debe ser 0 para liquidación controlada, se obtuvo {rav4_order}"

    # Verificación de Múltiplos y Mínimos
    for _, row in order_df.iterrows():
        mod = row["Modelo"]
        ped = int(row["Pedido_Sugerido_Oct26"])
        if ped > 0:
            min_l, mult_l = [int(x.strip()) for x in row["Lote_Min_Mult"].split("/")]
            assert ped >= min_l, f"Error en {mod}: pedido {ped} menor que mínimo {min_l}"
            assert ped % mult_l == 0, f"Error en {mod}: pedido {ped} no es múltiplo de {mult_l}"

    print("  [OK] Todas las sumas de control y reglas del Caso 1 superadas exitosamente.")

    # Exportar Excel Caso 1
    c1_path = output_dir / "Pedido_Recomendado_Octubre_2026.xlsx"
    print(f"  -> Exportando entregable: {c1_path}...")
    with pd.ExcelWriter(c1_path, engine="openpyxl") as writer:
        order_df.to_excel(writer, sheet_name="Resumen_Modelos", index=False)
        proj_df.to_excel(writer, sheet_name="Proyeccion_Mensual", index=False)
        mix_df.to_excel(writer, sheet_name="Mezcla_Version_Color", index=False)
        
        # Hoja de Análisis Financiero
        fin_df = pd.DataFrame([
            {"Métrica Financiera": "Total Unidades a Pedir", "Valor": totals1["total_unidades_pedidas"], "Unidad": "Unidades"},
            {"Métrica Financiera": "Inventario Actual en Patio (30/09/2026)", "Valor": totals1["total_inv_30sep"], "Unidad": "Unidades"},
            {"Métrica Financiera": "Tránsito Confirmado (Oct-26 a Ene-27)", "Valor": totals1["total_transito_oct_ene"], "Unidad": "Unidades"},
            {"Métrica Financiera": "Capital Comprometido de Compra", "Valor": totals1["total_capital_comprometido_usd"], "Unidad": "USD"},
            {"Métrica Financiera": "Ingreso Bruto Proyectado de Venta", "Valor": totals1["total_ingreso_esperado_usd"], "Unidad": "USD"},
            {"Métrica Financiera": "Margen Bruto Proyectado", "Valor": totals1["total_margen_bruto_esperado_usd"], "Unidad": "USD"},
            {"Métrica Financiera": "Margen Bruto Ponderado", "Valor": round(totals1["margen_bruto_ponderado_pct"] * 100, 2), "Unidad": "%"},
            {"Métrica Financiera": "Costo Financiero Plan Piso Mensual (0.9%)", "Valor": totals1["total_costo_plan_piso_mensual_usd"], "Unidad": "USD/mes"},
            {"Métrica Financiera": "Unidades RAV4 en Proceso de Liquidación", "Valor": totals1["rav4_unidades_a_liquidar_oct_abr"], "Unidad": "Unidades"},
        ])
        fin_df.to_excel(writer, sheet_name="Analisis_Financiero", index=False)
    print(f"  [OK] Archivo generado: {c1_path} ({os.path.getsize(c1_path):,} bytes).")

    # -----------------------------------------------------------------------
    # 2. VALIDACIÓN CASO 2 · RENOVACIONES CAPESA
    # -----------------------------------------------------------------------
    print("\n[QA] Ejecutando Caso 2 (Capesa Seguros)...")
    res2 = run_caso2_pipeline()

    audit2 = res2["audit_summary"]
    diag2 = res2["diagnosis"]
    ml2 = res2["ml_results"]
    sim2 = res2["simulation"]

    print("  -> Verificando sumas de control Caso 2...")
    # Deduplicación exacta de 151 pólizas
    assert audit2["filas_originales"] == 25351, f"Error: filas originales {audit2['filas_originales']} != 25351"
    assert audit2["polizas_duplicadas_eliminadas"] == 151, f"Error: duplicados {audit2['polizas_duplicadas_eliminadas']} != 151"
    assert audit2["polizas_unicas_limpias"] == 25200, f"Error: unicas {audit2['polizas_unicas_limpias']} != 25200"

    # Auditoría de contacto y post-vencimiento
    assert audit2["polizas_post_vencimiento_raw"] == 577, f"Error: post-vencimiento raw {audit2['polizas_post_vencimiento_raw']} != 577"
    assert audit2["mediana_dias_anticipacion"] == 4.0, f"Error: mediana dias {audit2['mediana_dias_anticipacion']} != 4.0"

    # Cruce de Bitácora y Formas de Pago
    kf = diag2["key_findings"]
    assert kf["llamadas_totales_bitacora"] == 78058, f"Error en bitácora: {kf['llamadas_totales_bitacora']} != 78058"
    assert kf["llamadas_domiciliado_financiado"] == 9808, f"Error llamadas auto: {kf['llamadas_domiciliado_financiado']} != 9808"
    assert abs(kf["pct_llamadas_domiciliado_financiado"] - 12.57) < 0.1, "Error pct llamadas auto"
    assert kf["perdidas_competencia_raw"] == 4205, f"Error fuga competencia: {kf['perdidas_competencia_raw']} != 4205"
    assert kf["perdidas_sin_contacto_a_tiempo_raw"] == 1125, f"Error fuga tardía: {kf['perdidas_sin_contacto_a_tiempo_raw']} != 1125"

    # ML Score y Priorización
    assert ml2["model_metrics"]["roc_auc_operativo_logit"] > 0.70, "ROC-AUC inferior a 0.70"
    assert len(ml2["bandeja_priorizada_df"]) == 20571, "Total de pólizas manuales evaluadas no coincide"

    print("  [OK] Todas las sumas de control y validaciones del Caso 2 superadas exitosamente.")

    # Exportar Excel Caso 2
    c2_path = output_dir / "Bandeja_Priorizada_Capesa.xlsx"
    print(f"  -> Exportando entregable: {c2_path}...")
    with pd.ExcelWriter(c2_path, engine="openpyxl") as writer:
        # 1. Diagnóstico Operativo
        diag2["payment_efficiency"].to_excel(writer, sheet_name="Diagnostico_Operativo", index=False)
        # 2. Cartera Priorizada (primeras 5,000 para tamaño manejable y máxima relevancia)
        cols_bandeja = [
            "Póliza", "Gestor", "ID cliente", "Teléfono cliente", "Ramo", "Segmento",
            "Aseguradora", "Fecha de vencimiento", "Prima anterior (USD)",
            "Prima de renovación (USD)", "% cambio de prima", "Comision_Renovacion_USD",
            "P_Fuga", "Valor_En_Riesgo_USD", "Segmento_Prioridad", "Ranking_Prioridad"
        ]
        ml2["bandeja_priorizada_df"][cols_bandeja].head(5000).to_excel(
            writer, sheet_name="Cartera_Priorizada", index=False
        )
        # 3. Simulación ROI
        sim2["lanes_summary_df"].to_excel(writer, sheet_name="Simulacion_ROI", index=False)

    print(f"  [OK] Archivo generado: {c2_path} ({os.path.getsize(c2_path):,} bytes).")

    print("\n" + "=" * 70)
    print("REPORTE QA: TODOS LOS TESTS PASARON EXITOSAMENTE (100% REPRODUCIBLE)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests_and_export()

