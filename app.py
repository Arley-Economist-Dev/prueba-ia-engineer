"""
Aplicación Web Unificada de Investigación de Operaciones e Inteligencia Artificial
Grupo Casa Pellas · Proceso de Selección Ingeniero(a) de IA:
- Pestaña 1: Caso 1 · Pedidos Inteligentes Toyota (Casa Pellas)
- Pestaña 2: Caso 2 · Orquestador de Renovaciones (Capesa Seguros)
"""

from __future__ import annotations

import os

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

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

# ---------------------------------------------------------------------------
# Configuración de Página y Estilos Ejecutivos
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Grupo Casa Pellas · Suite IA & Operations Research",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
    }
    .exec-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #b91c1c 100%);
        color: #ffffff;
        padding: 1.25rem 1.6rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.16);
    }
    .exec-banner h1 {
        font-size: 1.55rem;
        font-weight: 700;
        margin: 0 0 0.25rem 0;
        color: #ffffff;
    }
    .exec-banner p {
        font-size: 0.92rem;
        margin: 0;
        color: #e2e8f0;
    }
    .lane-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #2563eb;
        border-radius: 10px;
        padding: 1rem 1.1rem;
        height: 100%;
    }
    .lane-card h4 {
        margin: 0 0 0.4rem 0;
        color: #0f172a;
        font-size: 1.02rem;
    }
    .copilot-box {
        background-color: #f0fdf4;
        border: 1px solid #bbf7d0;
        border-left: 5px solid #16a34a;
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-top: 0.5rem;
        margin-bottom: 0.8rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Funciones con Caché para Carga Ultra-Rápida
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def get_caso1_base_data():
    return load_and_clean_caso1()


@st.cache_data(show_spinner=False)
def get_caso1_Dynamic_plan(
    safety_days: int,
    crm_capture_pct: int,
    rav4_phaseout: bool,
):
    base_data = get_caso1_base_data()
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
    excel_bytes = export_caso1_plan_to_excel_bytes({**base_data, **plan})
    return base_data, plan, excel_bytes


@st.cache_resource(show_spinner=False)
def get_caso2_core_bundle():
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
    return {
        **cleaned,
        "diagnosis": diagnosis,
        "ml_results": ml_results,
    }


# ---------------------------------------------------------------------------
# Encabezado Corporativo
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="exec-banner">
        <h1>Grupo Casa Pellas · Plataforma de IA & Investigación de Operaciones</h1>
        <p>Soporte de Decisiones Ejecutivas · Caso 1: Planificación S&OP de Vehículos Nuevos Toyota | Caso 2: Orquestador Predictivo de Renovaciones Capesa</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_caso1, tab_caso2 = st.tabs(
    [
        "🚗 Caso 1 · Pedidos Inteligentes Toyota (Casa Pellas)",
        "🛡️ Caso 2 · Orquestador de Renovaciones (Capesa Seguros)",
    ]
)


# ===========================================================================
# PESTAÑA 1: CASO 1 · PEDIDOS INTELIGENTES TOYOTA (CASA PELLAS)
# ===========================================================================

with tab_caso1:
    st.subheader("Motor S&OP de Pedidos a Fábrica — Ventana Octubre 2026 (Arribo Febrero 2027)")
    st.caption(
        "Corte de datos: **30/09/2026** · Lead time de fábrica: **4 meses** · "
        "Horizonte de cobertura del pedido: **Febrero – Abril 2027 (3 meses) + Stock de Seguridad** · "
        "Costo financiero de plan piso: **0.9% mensual**."
    )

    # 2. Barra de Parámetros Dinámicos
    with st.container(border=True):
        st.markdown("##### ⚙️ Barra de Parámetros Dinámicos del Planificador S&OP")
        p_col1, p_col2, p_col3 = st.columns([1.2, 1.2, 1.3])
        with p_col1:
            safety_days = st.slider(
                "Días de cobertura de Stock de Seguridad (al 30/Abr/2027)",
                min_value=30,
                max_value=90,
                value=30,
                step=5,
                help="Define el colchón de inventario al cierre de abril 2027 antes de que arribe el pedido de mayo 2027.",
            )
        with p_col2:
            crm_capture_pct = st.slider(
                "Porcentaje de captura de demanda latente CRM Leads (%)",
                min_value=0,
                max_value=100,
                value=50,
                step=5,
                help="Fracción de las oportunidades perdidas por falta de stock/color/versión en el CRM que se incorpora a la demanda objetivo.",
            )
        with p_col3:
            rav4_phaseout = st.toggle(
                "Activar liquidación controlada de RAV4 actual (Comunicado 15/09/2026)",
                value=True,
                help="En mayo 2027 llega la Nueva Generación RAV4 sin apoyo de fábrica para liquidar la generación actual. Con 9 uds en patio + 47 en tránsito (44 del pedido Jul-26), fuerza Pedido = 0 y liquidación hacia stock 0 al 30/04/2027.",
            )

    base_c1, plan_c1, excel_bytes_c1 = get_caso1_Dynamic_plan(
        safety_days=safety_days,
        crm_capture_pct=crm_capture_pct,
        rav4_phaseout=rav4_phaseout,
    )
    order_df = plan_c1["order_recommendations"]
    totals_c1 = plan_c1["order_totals"]
    audit_c1 = base_c1["audit_summary"]

    # Evaluar estado de riesgo de obsolescencia para KPI 4
    rav4_row = order_df[order_df["Modelo"] == "RAV4"].iloc[0]
    rav4_order_qty = int(rav4_row["Pedido_Sugerido_Oct26"])
    rav4_end_stock = float(rav4_row["Inv_Proyectado_30Abr27"])
    inv_over_180 = int(
        plan_c1["pipeline_analysis"]["pipeline_by_model"]["Uds_Mas_180_Dias"].sum()
    )

    # 1. KPIs Ejecutivos
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        st.metric(
            label="Total Unidades a Pedir (Oct 2026)",
            value=f"{totals_c1['total_unidades_pedidas']:,} uds",
            delta=f"Patio: {totals_c1['total_inv_30sep']} | Tránsito: {totals_c1['total_transito_oct_ene']} uds",
        )
    with kpi2:
        st.metric(
            label="Capital Total de Compra Comprometido",
            value=f"${totals_c1['total_capital_comprometido_usd']:,.0f} USD",
            delta=f"Plan Piso (0.9%/mes): ${totals_c1['total_costo_plan_piso_mensual_usd']:,.0f}/mes",
            delta_color="off",
        )
    with kpi3:
        st.metric(
            label="Margen Bruto Proyectado del Pedido",
            value=f"${totals_c1['total_margen_bruto_esperado_usd']:,.0f} USD",
            delta=f"{totals_c1['margen_bruto_ponderado_pct'] * 100:.2f}% s/ Ingreso (${totals_c1['total_ingreso_esperado_usd']:,.0f})",
        )
    with kpi4:
        if rav4_phaseout:
            st.metric(
                label="Alerta de Riesgo de Obsolescencia",
                value="CONTROLADO (RAV4 = 0 uds)",
                delta="56 uds actuales se liquidan a 0 al 30/Abr",
                delta_color="normal",
            )
        else:
            obsolescence_exposure = rav4_end_stock * float(rav4_row["Costo_Unitario_USD"])
            st.metric(
                label="Alerta de Riesgo de Obsolescencia",
                value=f"ALTO (+{rav4_order_qty} RAV4 pedidas)",
                delta=f"Sobrestock May-27: {rav4_end_stock:.0f} uds (${obsolescence_exposure:,.0f})",
                delta_color="inverse",
            )

    if rav4_phaseout:
        st.info(
            "📌 **Política RAV4 Activa (Comunicado 15/09/2026):** Existen **9 unidades en patio** y **47 en tránsito** "
            "(44 del pedido `PF-41141` de julio + 3 rezagadas de abril) = **56 unidades disponibles** para los 7 meses previos "
            "al arribo de la nueva generación en mayo 2027 (~8.0 uds/mes requeridas). El motor fija **Pedido Octubre = 0 uds** "
            "para evitar pérdidas por liquidación forzosa (descuentos de 4% a 10% sobre precio). "
            f"*(Auditoría de base: {audit_c1['notas_credito_filas']} Notas de Crédito `NC-` neteadas = {audit_c1['unidades_netas_reales']:,} uds netas; "
            f"11 modelos y 7 sucursales normalizadas)*."
        )
    else:
        st.warning(
            "⚠️ **Alerta Crítica RAV4 Desactivada:** Al desactivar la liquidación controlada, el motor solicita "
            f"**{rav4_order_qty} unidades adicionales** de la generación saliente, dejando **{rav4_end_stock:.1f} unidades remanentes** "
            "al 30 de abril de 2027 sin apoyo de fábrica frente al lanzamiento de la Nueva Generación en mayo 2027."
        )

    # 3. Tabla Maestra de Pedidos + 5. Botón de Exportación a Excel
    hdr_col1, hdr_col2 = st.columns([3, 1])
    with hdr_col1:
        st.markdown("#### 📋 Tabla Maestra de Pedidos por Modelo (Ventana Octubre 2026)")
    with hdr_col2:
        st.download_button(
            label="📥 Exportar Plan Consolidado a Excel (.xlsx)",
            data=excel_bytes_c1,
            file_name=f"Plan_Pedidos_Toyota_Oct2026_SS{safety_days}d_CRM{crm_capture_pct}pct.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            type="primary",
        )

    master_display_df = pd.DataFrame(
        {
            "Modelo": order_df["Modelo"],
            "Lote (Mín/Múlt)": order_df["Lote_Min_Mult"],
            "Inventario Actual (30/Sep)": order_df["Inv_30Sep"],
            "En Tránsito": order_df["Transito_Oct26_Ene27"],
            "Demanda Oct26-Ene27": order_df["Demanda_Oct26_Ene27_4M"],
            "Stock Proyectado al 31/Ene": order_df["Inv_Proyectado_31Ene27"],
            "Demanda Feb-Abr": order_df["Demanda_Feb27_Abr27_3M"],
            "Stock Seguridad Obj.": order_df["Stock_Seguridad_Objetivo"],
            "Pedido Sugerido Bruto": order_df["Necesidad_Neta_Feb_Abr"],
            "Pedido Final (Mín/Múlt)": order_df["Pedido_Sugerido_Oct26"],
            "Inversión (USD)": order_df["Capital_Comprometido_USD"],
            "Margen (USD)": order_df["Margen_Bruto_Esperado_USD"],
            "Plan Piso Mensual (USD)": order_df["Costo_Plan_Piso_Mensual_USD"],
        }
    )

    st.dataframe(
        master_display_df.style.format(
            {
                "Inventario Actual (30/Sep)": "{:,}",
                "En Tránsito": "{:,}",
                "Demanda Oct26-Ene27": "{:,.1f}",
                "Stock Proyectado al 31/Ene": "{:,.1f}",
                "Demanda Feb-Abr": "{:,.1f}",
                "Stock Seguridad Obj.": "{:,.1f}",
                "Pedido Sugerido Bruto": "{:,.1f}",
                "Pedido Final (Mín/Múlt)": "{:,}",
                "Inversión (USD)": "${:,.0f}",
                "Margen (USD)": "${:,.0f}",
                "Plan Piso Mensual (USD)": "${:,.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # 4. Gráficos Interactivos de Plotly
    st.markdown("---")
    st.markdown("#### 📈 Visualización Operativa: Proyección de Inventario y Mezcla Óptima (Versión / Color)")

    g_col1, g_col2 = st.columns([1.15, 1.0])

    with g_col1:
        selected_curve_model = st.selectbox(
            "Seleccionar vista de la curva de inventario proyectado (Sep 2026 – Abr 2027):",
            options=["Todos los Modelos (Consolidado)"] + OFFICIAL_MODELS,
            index=0,
        )
        proj_df = plan_c1["monthly_projection_df"]
        if selected_curve_model == "Todos los Modelos (Consolidado)":
            curve_data = (
                proj_df.groupby(["Orden_Mes", "Periodo", "Etiqueta_Mes"], as_index=False)
                .agg(
                    Inventario_Cierre_Uds=("Inventario_Cierre_Uds", "sum"),
                    Demanda_Mensual_Uds=("Demanda_Mensual_Uds", "sum"),
                    Llegadas_Uds=("Llegadas_Uds", "sum"),
                )
                .sort_values("Orden_Mes")
            )
            chart_title = "Trayectoria Consolidada: Inventario al Cierre vs Demanda y Llegadas"
        else:
            curve_data = proj_df[proj_df["Modelo"] == selected_curve_model].sort_values(
                "Orden_Mes"
            )
            chart_title = f"Trayectoria Mensual ({selected_curve_model}): Inventario vs Demanda y Arribo"

        fig_inv = go.Figure()
        fig_inv.add_trace(
            go.Bar(
                x=curve_data["Etiqueta_Mes"],
                y=curve_data["Llegadas_Uds"],
                name="Llegadas a Patio (Tránsito / Pedido Oct)",
                marker_color="#93c5fd",
                opacity=0.65,
            )
        )
        fig_inv.add_trace(
            go.Scatter(
                x=curve_data["Etiqueta_Mes"],
                y=curve_data["Inventario_Cierre_Uds"],
                name="Inventario Proyectado al Cierre (uds)",
                mode="lines+markers+text",
                text=[f"{v:.0f}" for v in curve_data["Inventario_Cierre_Uds"]],
                textposition="top center",
                line=dict(color="#1d4ed8", width=3.5),
                marker=dict(size=9),
            )
        )
        fig_inv.add_trace(
            go.Scatter(
                x=curve_data["Etiqueta_Mes"],
                y=curve_data["Demanda_Mensual_Uds"],
                name="Demanda Mensual Planificada (uds)",
                mode="lines+markers",
                line=dict(color="#dc2626", width=2.5, dash="dash"),
                marker=dict(size=7),
            )
        )
        fig_inv.update_layout(
            title=chart_title,
            xaxis_title="Mes de Proyección (Corte Sep 2026 -> Cierre Ciclo Abr 2027)",
            yaxis_title="Unidades",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            height=430,
            margin=dict(l=20, r=20, t=60, b=20),
            barmode="overlay",
        )
        st.plotly_chart(fig_inv, use_container_width=True)

    with g_col2:
        models_with_order = [
            m
            for m in OFFICIAL_MODELS
            if int(
                order_df.loc[order_df["Modelo"] == m, "Pedido_Sugerido_Oct26"].iloc[0]
            )
            > 0
        ]
        default_mix_options = models_with_order if models_with_order else OFFICIAL_MODELS
        selected_mix_model = st.selectbox(
            "Seleccionar modelo para desglose de Versión y Color:",
            options=OFFICIAL_MODELS,
            index=OFFICIAL_MODELS.index(default_mix_options[0]),
        )
        mix_sub = plan_c1["version_color_mix"][
            plan_c1["version_color_mix"]["Modelo"] == selected_mix_model
        ].copy()
        pedido_mod_sel = int(
            order_df.loc[
                order_df["Modelo"] == selected_mix_model, "Pedido_Sugerido_Oct26"
            ].iloc[0]
        )

        value_col_mix = (
            "Unidades_Sugeridas"
            if pedido_mod_sel > 0
            else "Share_Optimo_Pct"
        )
        mix_title_suffix = (
            f"{pedido_mod_sel} uds pedidas"
            if pedido_mod_sel > 0
            else "0 uds pedidas (Mix histórico %)"
        )

        fig_mix = px.bar(
            mix_sub,
            x="Versión",
            y=value_col_mix,
            color="Color",
            text_auto=True,
            title=f"Mezcla Recomendada por Versión y Color — {selected_mix_model} ({mix_title_suffix})",
            labels={
                "Unidades_Sugeridas": "Unidades a Pedir",
                "Share_Optimo_Pct": "Participación Óptima (%)",
            },
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig_mix.update_layout(
            height=430,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=20, r=20, t=60, b=20),
        )
        st.plotly_chart(fig_mix, use_container_width=True)

    with st.expander("🔎 Ver Detalle Completo de Mezcla Sugerida por Modelo, Versión y Color"):
        st.dataframe(
            mix_sub[
                [
                    "Modelo",
                    "Versión",
                    "Color",
                    "Ventas_Hist_Uds",
                    "Leads_Stockout_Version_Uds",
                    "Share_Optimo_Pct",
                    "Unidades_Sugeridas",
                ]
            ].style.format(
                {
                    "Ventas_Hist_Uds": "{:,}",
                    "Leads_Stockout_Version_Uds": "{:,.0f}",
                    "Share_Optimo_Pct": "{:.2f}%",
                    "Unidades_Sugeridas": "{:,}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )


# ===========================================================================
# PESTAÑA 2: CASO 2 · ORQUESTADOR DE RENOVACIONES (CAPESA SEGUROS)
# ===========================================================================

with tab_caso2:
    st.subheader("Diagnóstico Operativo, Priorización Predictiva P(Fuga) y Arquitectura de 3 Carriles")

    c2_bundle = get_caso2_core_bundle()
    audit_c2 = c2_bundle["audit_summary"]
    diag_c2 = c2_bundle["diagnosis"]
    ml_c2 = c2_bundle["ml_results"]
    findings_c2 = diag_c2["key_findings"]

    st.caption(
        f"Auditoría de Datos: **{audit_c2['filas_originales']:,} registros brutos** $\\rightarrow$ "
        f"**{audit_c2['polizas_duplicadas_eliminadas']} duplicados eliminados** $\\rightarrow$ "
        f"**{audit_c2['polizas_unicas_limpias']:,} pólizas únicas** · "
        f"Mediana de anticipación actual: **{audit_c2['mediana_dias_anticipacion']:.0f} días** (Meta: **20 días**) · "
        f"**{audit_c2['polizas_post_vencimiento_raw']} pólizas** contactadas post-vencimiento."
    )

    # 1. Panel de Diagnóstico Ejecutivo
    st.markdown("#### 1️⃣ Panel de Diagnóstico Ejecutivo del Cuello de Botella")
    d_col1, d_col2, d_col3 = st.columns(3)

    # Gráfico 1: Curva de renovación según días de anticipación (Manual vs Automáticos)
    with d_col1:
        curve_ant = diag_c2["anticipation_curve"]
        curve_manual = curve_ant[curve_ant["Forma de pago"] == "Manual"].copy()
        fig_ant = px.bar(
            curve_manual,
            x="Tramo_Anticipacion",
            y="Tasa_Renovacion_Pct",
            text="Tasa_Renovacion_Pct",
            color="Tasa_Renovacion_Pct",
            color_continuous_scale="RdYlGn",
            title="Tasa de Renovación Manual según Anticipación",
            labels={
                "Tramo_Anticipacion": "Ventana de Primer Contacto",
                "Tasa_Renovacion_Pct": "Renovación (%)",
            },
        )
        fig_ant.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_ant.update_layout(
            height=370,
            coloraxis_showscale=False,
            yaxis_range=[0, 95],
            xaxis_tickangle=-20,
            margin=dict(l=15, r=15, t=50, b=20),
        )
        st.plotly_chart(fig_ant, use_container_width=True)
        st.caption(
            "En pago **Manual**, contactar a **>=20 días** logra alta retención, pero la mitad se contacta a **<=4 días** (y 577 post-vencimiento)."
        )

    # Gráfico 2: Distribución de llamadas por Forma de Pago (12.6% desperdiciado)
    with d_col2:
        pay_eff = diag_c2["payment_efficiency"].copy()
        fig_pay = make_subplots(specs=[[{"secondary_y": True}]])
        fig_pay.add_trace(
            go.Bar(
                x=pay_eff["Forma de pago"],
                y=pay_eff["Llamadas_Bitacora"],
                name="Llamadas en Bitácora",
                text=[
                    f"{v:,} ({p:.1f}%)"
                    for v, p in zip(
                        pay_eff["Llamadas_Bitacora"], pay_eff["Share_Llamadas_Pct"]
                    )
                ],
                textposition="auto",
                marker_color=["#0ea5e9", "#38bdf8", "#f97316"],
            ),
            secondary_y=False,
        )
        fig_pay.add_trace(
            go.Scatter(
                x=pay_eff["Forma de pago"],
                y=pay_eff["Tasa_Renovacion_Raw_Pct"],
                name="Tasa de Renovación (%)",
                mode="lines+markers+text",
                text=[f"{r:.1f}%" for r in pay_eff["Tasa_Renovacion_Raw_Pct"]],
                textposition="top center",
                line=dict(color="#15803d", width=3),
                marker=dict(size=9),
            ),
            secondary_y=True,
        )
        fig_pay.update_layout(
            title="Llamadas vs Renovación por Forma de Pago",
            height=370,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=15, r=15, t=50, b=20),
        )
        fig_pay.update_yaxes(title_text="Llamadas Realizadas", secondary_y=False)
        fig_pay.update_yaxes(
            title_text="Renovación (%)", range=[0, 110], secondary_y=True
        )
        st.plotly_chart(fig_pay, use_container_width=True)
        st.caption(
            f"**{findings_c2['llamadas_domiciliado_financiado']:,} llamadas ({findings_c2['pct_llamadas_domiciliado_financiado']:.1f}%)** dedicadas a Domiciliado (94.5%) y Financiado (91.0%), restando capacidad a Manual (44.5%)."
        )

    # Gráfico 3: Quiebre estructural tras salida de G06 y G07 en diciembre 2025
    with d_col3:
        m_evol = diag_c2["monthly_evolution"].copy()
        m_evol["Mes_Str"] = m_evol["Mes_Vencimiento"].dt.strftime("%Y-%m")
        fig_break = make_subplots(specs=[[{"secondary_y": True}]])
        fig_break.add_trace(
            go.Bar(
                x=m_evol["Mes_Str"],
                y=m_evol["Polizas_Por_Gestor"],
                name="Pólizas / Gestor / Mes",
                marker_color=np.where(
                    m_evol["Mes_Vencimiento"] < "2025-12-01", "#64748b", "#ef4444"
                ),
                opacity=0.65,
            ),
            secondary_y=False,
        )
        fig_break.add_trace(
            go.Scatter(
                x=m_evol["Mes_Str"],
                y=m_evol["Tasa_Renovacion_Global_Pct"],
                name="Renovación Global (%)",
                mode="lines+markers",
                line=dict(color="#1d4ed8", width=3),
            ),
            secondary_y=True,
        )
        fig_break.add_trace(
            go.Scatter(
                x=m_evol["Mes_Str"],
                y=m_evol["Pct_En_Meta_20d"],
                name="% En Meta (>=20 días)",
                mode="lines+markers",
                line=dict(color="#16a34a", width=2.5, dash="dot"),
            ),
            secondary_y=True,
        )
        fig_break.update_layout(
            title="Quiebre Estructural Dic 2025 (Salida G06 y G07: 7 -> 5 Gestores)",
            height=370,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            margin=dict(l=15, r=15, t=50, b=20),
        )
        fig_break.update_yaxes(
            title_text="Pólizas por Gestor", range=[0, 500], secondary_y=False
        )
        fig_break.update_yaxes(
            title_text="Porcentaje (%)", range=[0, 80], secondary_y=True
        )
        st.plotly_chart(fig_break, use_container_width=True)
        st.caption(
            "Al caer de **7 a 5 gestores** el `01/12/2025`, la carga subió de **292 a 381 pólizas/gestor**, y la renovación cayó de **62.0% a 50.6%**."
        )

    # 2. Arquitectura Operativa de 3 Carriles + 4. Simulador de ROI para el Comité Directivo
    st.markdown("---")
    st.markdown("#### 2️⃣ Arquitectura Operativa de 3 Carriles & Simulador de ROI para el Comité Directivo")

    with st.container(border=True):
        st.markdown("##### 🎛️ Parámetros del Simulador de ROI (Tiempo Real)")
        s_col1, s_col2, s_col3 = st.columns(3)
        with s_col1:
            sim_contact_days = st.slider(
                "Efectividad Bot T-25: Días de anticipación asegurados en Cartera Manual",
                min_value=10,
                max_value=25,
                value=22,
                step=1,
                help="El Agente Conversacional contacta a T-25 días por WhatsApp/Voz y entrega las pólizas en ventana de >=20 días.",
            )
        with s_col2:
            sim_ai_closure_pct = st.slider(
                "Auto-cierre digital del Bot Conversacional en pólizas de bajo riesgo (%)",
                min_value=10,
                max_value=70,
                value=35,
                step=5,
                help="Porcentaje del tramo de menor complejidad que confirma su renovación directamente con el Bot T-25 sin consumir llamadas humanas.",
            )
        with s_col3:
            sim_human_uplift_pct = st.slider(
                "Efectividad adicional de negociación humana en Bandeja Priorizada (%)",
                min_value=0,
                max_value=20,
                value=6,
                step=1,
                help="Reducción porcentual adicional sobre P(Fuga) lograda por los 5 gestores al negociar con tiempo y cotización alternativa.",
            )

    sim_res = simulate_three_lane_architecture(
        c2_bundle["renovaciones"],
        ml_c2,
        target_contact_days=sim_contact_days,
        ai_agent_closure_share_low_risk=sim_ai_closure_pct / 100.0,
        human_retention_uplift_high_value=sim_human_uplift_pct / 100.0,
        zero_touch_recovery_rate=0.25,
    )
    sim_m = sim_res["simulation_metrics"]
    lanes_df = sim_res["lanes_summary_df"]

    r_kpi1, r_kpi2, r_kpi3, r_kpi4 = st.columns(4)
    with r_kpi1:
        st.metric(
            label="Comisiones Anuales Rescatadas (ROI)",
            value=f"+${sim_m['impacto_economico_anual_usd']:,.0f} USD/año",
            delta=f"Total Anual: ${sim_m['comision_simulada_anual_usd']:,.0f} vs ${sim_m['comision_actual_anual_usd']:,.0f}",
        )
    with r_kpi2:
        st.metric(
            label="Tasa de Renovación Global Simulada",
            value=f"{sim_m['tasa_renovacion_global_simulada_pct']:.2f}%",
            delta=f"+{sim_m['puntos_retencion_global_ganados_pp']:.2f} pp (Actual: {sim_m['tasa_renovacion_global_actual_pct']:.2f}%)",
        )
    with r_kpi3:
        st.metric(
            label="Pólizas Anuales Recuperadas",
            value=f"+{sim_m['polizas_recuperadas_anual']:,} pólizas/año",
            delta=f"Renovación Manual: {sim_m['tasa_renovacion_manual_actual_pct']:.1f}% -> {sim_m['tasa_renovacion_manual_simulada_pct']:.1f}%",
        )
    with r_kpi4:
        st.metric(
            label="Ocupación de los 5 Gestores Humanos",
            value=f"{sim_m['utilizacion_capacidad_humana_pct']:.1f}% capacidad",
            delta=f"{sim_m['llamadas_humanas_requeridas_mes_3carriles']:,} de {sim_m['capacidad_mensual_5_gestores_llamadas']:,} llamadas/mes",
        )

    l_c1, l_c2, l_c3 = st.columns(3)
    with l_c1:
        row_l1 = lanes_df.iloc[0]
        st.markdown(
            f"""
            <div class="lane-card">
                <h4>⚡ {row_l1['Carril']}</h4>
                <p><b>Universo:</b> {row_l1['Segmento_Objetivo']}</p>
                <p><b>Acción:</b> {row_l1['Mecanismo_IA_Automatizacion']}</p>
                <p><b>Capacidad Liberada:</b> {row_l1['Llamadas_Humanas_Liberadas_Anual']:,} llamadas/año (9,808 en 13M)</p>
                <p><b>Comisiones Rescatadas:</b> +${row_l1['Impacto_Comisiones_Anual_USD']:,.0f} USD/año</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with l_c2:
        row_l2 = lanes_df.iloc[1]
        st.markdown(
            f"""
            <div class="lane-card" style="border-left-color: #16a34a;">
                <h4>🤖 {row_l2['Carril']}</h4>
                <p><b>Universo:</b> {row_l2['Segmento_Objetivo']}</p>
                <p><b>Acción:</b> {row_l2['Mecanismo_IA_Automatizacion']}</p>
                <p><b>Pólizas Retenidas por Timing:</b> +{row_l2['Polizas_Adicionales_Retenidas_Anual']:,} pólizas/año</p>
                <p><b>Comisiones Rescatadas:</b> +${row_l2['Impacto_Comisiones_Anual_USD']:,.0f} USD/año</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with l_c3:
        row_l3 = lanes_df.iloc[2]
        st.markdown(
            f"""
            <div class="lane-card" style="border-left-color: #ea580c;">
                <h4>🎯 {row_l3['Carril']}</h4>
                <p><b>Universo:</b> {row_l3['Segmento_Objetivo']}</p>
                <p><b>Acción:</b> {row_l3['Mecanismo_IA_Automatizacion']}</p>
                <p><b>Pólizas Retenidas por Negociación:</b> +{row_l3['Polizas_Adicionales_Retenidas_Anual']:,} pólizas/año</p>
                <p><b>Comisiones Rescatadas:</b> +${row_l3['Impacto_Comisiones_Anual_USD']:,.0f} USD/año</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # 3. Bandeja de Trabajo Inteligente para los 5 Gestores (G01 a G05) + Copiloto IA
    st.markdown("---")
    st.markdown("#### 3️⃣ Bandeja de Trabajo Inteligente para los 5 Gestores Activos (G01 a G05) & Copiloto IA")
    st.caption(
        "Índice de Priorización Comercial: **`Comisión en Riesgo (USD) = Prima_Renovación × %_Comisión × P(Fuga)`** · "
        f"ROC-AUC del modelo predictivo: **{ml_c2['model_metrics']['roc_auc_operativo_logit']:.4f} (Logit) / {ml_c2['model_metrics']['roc_auc_operativo_gbm']:.4f} (GBM)** · "
        f"El **Top 30%** de la bandeja concentra el **{ml_c2['model_metrics']['top_30pct_captura_valor_riesgo_pct']:.1f}%** de todo el valor económico en riesgo."
    )

    equipo_df = c2_bundle["equipo"]
    active_gestores = ["G01", "G02", "G03", "G04", "G05"]
    gestor_labels = {
        row["Código"]: f"{row['Código']} · {row['Nombre']}"
        for _, row in equipo_df[equipo_df["Código"].isin(active_gestores)].iterrows()
    }

    f_col1, f_col2, f_col3 = st.columns([1.2, 1.1, 1.1])
    with f_col1:
        selected_gestor = st.selectbox(
            "Filtrar Bandeja por Gestor Activo (G01 a G05):",
            options=["Todos los Gestores Activos (G01–G05)"]
            + [gestor_labels[g] for g in active_gestores],
            index=1,
        )
    with f_col2:
        selected_ramo = st.selectbox(
            "Filtrar por Ramo:",
            options=["Todos los Ramos", "Autos", "Médico", "Daños / Hogar", "Vida"],
            index=0,
        )
    with f_col3:
        only_pending = st.checkbox(
            "Mostrar solo pólizas en riesgo alto / no renovadas",
            value=True,
        )

    bandeja_df = ml_c2["bandeja_priorizada_df"].copy()
    bandeja_df = bandeja_df[bandeja_df["Gestor"].isin(active_gestores)]

    if selected_gestor != "Todos los Gestores Activos (G01–G05)":
        g_code = selected_gestor.split(" · ")[0].strip()
        bandeja_df = bandeja_df[bandeja_df["Gestor"] == g_code]

    if selected_ramo != "Todos los Ramos":
        bandeja_df = bandeja_df[bandeja_df["Ramo"] == selected_ramo]

    if only_pending:
        bandeja_df = bandeja_df[bandeja_df["Fuga_Bin"] == 1]

    bandeja_df = bandeja_df.sort_values(
        "Valor_En_Riesgo_USD", ascending=False
    ).reset_index(drop=True)

    bandeja_view = pd.DataFrame(
        {
            "Póliza": bandeja_df["Póliza"],
            "Gestor": bandeja_df["Gestor"],
            "ID Cliente": bandeja_df["ID cliente"],
            "Teléfono": bandeja_df["Teléfono cliente"],
            "Ramo": bandeja_df["Ramo"],
            "Segmento": bandeja_df["Segmento"],
            "Aseguradora": bandeja_df["Aseguradora"],
            "Fecha Vencimiento": bandeja_df["Fecha de vencimiento"].dt.strftime("%Y-%m-%d"),
            "Prima Anterior (USD)": bandeja_df["Prima anterior (USD)"],
            "Prima Renovación (USD)": bandeja_df["Prima de renovación (USD)"],
            "% Cambio Prima": bandeja_df["% cambio de prima"] * 100.0,
            "Comisión Potencial (USD)": bandeja_df["Comision_Renovacion_USD"],
            "P(Fuga) %": bandeja_df["P_Fuga"] * 100.0,
            "Comisión en Riesgo (USD)": bandeja_df["Valor_En_Riesgo_USD"],
        }
    )

    st.dataframe(
        bandeja_view.head(100).style.format(
            {
                "Prima Anterior (USD)": "${:,.2f}",
                "Prima Renovación (USD)": "${:,.2f}",
                "% Cambio Prima": "{:+.1f}%",
                "Comisión Potencial (USD)": "${:,.2f}",
                "P(Fuga) %": "{:.1f}%",
                "Comisión en Riesgo (USD)": "${:,.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
        height=320,
    )

    # Módulo Copiloto IA
    st.markdown("##### 🤖 Módulo Copiloto IA de Retención y Recotización Multi-Aseguradora")
    if not bandeja_df.empty:
        top_policies = bandeja_df.head(50)
        policy_options = [
            f"{r['Póliza']} | {r['Ramo']} ({r['Segmento']}) | {r['Aseguradora']} | "
            f"Comisión en Riesgo: ${r['Valor_En_Riesgo_USD']:,.2f} USD | P(Fuga): {r['P_Fuga']*100:.1f}% | "
            f"Cambio Prima: {r['% cambio de prima']*100:+.1f}%"
            for _, r in top_policies.iterrows()
        ]
        selected_option = st.selectbox(
            "Seleccionar póliza de la Bandeja Priorizada para asistir al gestor con el Copiloto IA:",
            options=policy_options,
            index=0,
        )
        selected_poliza_id = selected_option.split(" | ")[0].strip()
        selected_row = top_policies[
            top_policies["Póliza"] == selected_poliza_id
        ].iloc[0]

        copilot_out = generate_copilot_recommendation(
            selected_row,
            c2_bundle["renovaciones"],
            equipo_df=equipo_df,
        )

        cp1, cp2, cp3, cp4 = st.columns(4)
        with cp1:
            st.metric(
                "Póliza / Cliente",
                f"{copilot_out['poliza']}",
                f"{copilot_out['cliente_id']} · Tel: {copilot_out['telefono']}",
                delta_color="off",
            )
        with cp2:
            st.metric(
                "Probabilidad de Fuga P(Fuga)",
                f"{copilot_out['p_fuga_pct']:.1f}%",
                f"Comisión en Riesgo: ${copilot_out['comision_en_riesgo_usd']:,.2f} USD",
                delta_color="inverse",
            )
        with cp3:
            st.metric(
                "Prima Renovación vs Anterior",
                f"${copilot_out['prima_renovacion_usd']:,.2f} USD",
                f"{copilot_out['cambio_prima_pct']:+.1f}% (Ant: ${copilot_out['prima_anterior_usd']:,.2f})",
                delta_color="inverse" if copilot_out["hubo_aumento_prima"] else "normal",
            )
        with cp4:
            st.metric(
                "Cotización Alternativa Sugerida",
                f"${copilot_out['prima_alternativa_sugerida_usd']:,.2f} USD",
                f"Ahorro: ${copilot_out['ahorro_potencial_cliente_usd']:,.2f} ({copilot_out['aseguradora_alternativa']})",
            )

        st.markdown(
            f"""
            <div class="copilot-box">
                <b>🗣️ Argumento Comercial Recomendado por el Copiloto IA:</b><br>
                {copilot_out['argumento_retencion']}
            </div>
            """,
            unsafe_allow_html=True,
        )

        c_left, c_right = st.columns([1.0, 1.4])
        with c_left:
            st.markdown("**🔍 Impulsores de Riesgo Detectados en la Póliza:**")
            for factor in copilot_out["factores_riesgo"]:
                st.markdown(f"- {factor}")
            st.markdown(f"- **Estrategia Óptima:** {copilot_out['estrategia_precio']}")

        with c_right:
            st.markdown("**📊 Matriz de Cotización Alternativa Multi-Aseguradora:**")
            st.dataframe(
                copilot_out["cotizaciones_df"].style.format(
                    {
                        "Prima Anual (USD)": "${:,.2f}",
                        "Ahorro vs Cotización Base (USD)": "${:,.2f}",
                        "Comisión Capesa (USD)": "${:,.2f}",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
    else:
        st.info("No hay pólizas que coincidan con el filtro seleccionado.")

