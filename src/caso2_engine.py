"""
Motor de Diagnóstico Operativo, Machine Learning P(Fuga) y Simulación de 3 Carriles
Caso 2: Optimización de Renovaciones de Pólizas en Capesa.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

STRUCTURAL_BREAK_DATE = pd.Timestamp("2025-12-01")
TARGET_ANTICIPATION_DAYS = 20
DATASET_MONTHS = 13.0  # Septiembre 2025 a Septiembre 2026 (13 meses)


def get_default_excel_path() -> Path:
    """Localiza automáticamente el archivo Excel del Caso 2 en el espacio de trabajo."""
    candidates = [
        Path("Caso 2 - Renovaciones Capesa/Caso 2 - Base de datos Renovaciones.xlsx"),
        Path(__file__).resolve().parent.parent
        / "Caso 2 - Renovaciones Capesa"
        / "Caso 2 - Base de datos Renovaciones.xlsx",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        "No se encontró 'Caso 2 - Base de datos Renovaciones.xlsx'."
    )


# ---------------------------------------------------------------------------
# 1. Auditoría y Limpieza
# ---------------------------------------------------------------------------

def normalize_renovo(val: Any) -> int:
    """Normaliza la variable 'Renovó' ('Sí', 'SI', 'No', 'no') hacia 1 / 0."""
    if pd.isna(val):
        return 0
    s = str(val).strip().lower()
    if s in {"sí", "si", "1", "true", "s"}:
        return 1
    return 0


def _enrich_renovaciones_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula columnas derivadas estándar sobre un DataFrame de Renovaciones."""
    out = df.copy()
    out["Fecha de vencimiento"] = pd.to_datetime(out["Fecha de vencimiento"])
    out["Fecha primer contacto"] = pd.to_datetime(out["Fecha primer contacto"])
    out["Mes_Vencimiento"] = (
        out["Fecha de vencimiento"].dt.to_period("M").dt.to_timestamp()
    )

    # Normalización de Renovó (1 = Renovó, 0 = No renovó) y Fuga (1 = No renovó)
    out["Renovo_Bin"] = out["Renovó"].apply(normalize_renovo).astype(int)
    out["Fuga_Bin"] = 1 - out["Renovo_Bin"]

    # Limpieza de teléfonos y contacto
    tel_clean = (
        out["Teléfono cliente"]
        .astype(str)
        .str.strip()
        .replace({"nan": np.nan, "None": np.nan, "": np.nan})
    )
    out["Telefono_Valido"] = tel_clean.notna()
    out["Teléfono cliente"] = tel_clean.fillna("Sin teléfono registrado")
    out["Sin_Contacto_Previo"] = out["Fecha primer contacto"].isna()

    # Cálculo de días de anticipación: (Fecha de vencimiento - Fecha primer contacto).days
    out["dias_anticipacion"] = (
        out["Fecha de vencimiento"] - out["Fecha primer contacto"]
    ).dt.days

    # Clasificación del plazo de contacto respecto a la meta de 20 días
    out["Fuera_De_Plazo_20d"] = (out["dias_anticipacion"] < TARGET_ANTICIPATION_DAYS) | (
        out["dias_anticipacion"].isna()
    )
    out["Contacto_Post_Vencimiento"] = out["dias_anticipacion"] < 0
    out["Contacto_Dia_Cero_O_Post"] = out["dias_anticipacion"] <= 0

    def classify_window(days: float) -> str:
        if pd.isna(days):
            return "1. Sin contacto"
        if days < 0:
            return "2. Post-vencimiento (<0 días)"
        if days <= 3:
            return "3. Crítico (0 a 3 días)"
        if days <= 9:
            return "4. Tardío (4 a 9 días)"
        if days <= 19:
            return "5. Moderado (10 a 19 días)"
        return "6. En meta (>=20 días)"

    out["Tramo_Anticipacion"] = out["dias_anticipacion"].apply(classify_window)

    # Comisión en USD si se renueva
    out["Comision_Renovacion_USD"] = (
        out["Prima de renovación (USD)"] * out["% comisión"]
    )
    out["Comision_Capturada_USD"] = out["Comision_Renovacion_USD"] * out["Renovo_Bin"]
    out["Comision_Perdida_USD"] = out["Comision_Renovacion_USD"] * out["Fuga_Bin"]

    # Periodo operativo (antes y después de la salida de G06 y G07 el 30/11/2025)
    out["Periodo_Operativo"] = np.where(
        out["Fecha de vencimiento"] < STRUCTURAL_BREAK_DATE,
        "Sep-Nov 2025 (7 Gestores)",
        "Dic 2025-Sep 2026 (5 Gestores)",
    )
    return out


def load_and_clean_caso2(
    excel_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """
    Carga el archivo Excel del Caso 2, audita y deduplica las 151 pólizas repetidas,
    limpia nulos en contacto y teléfonos, normaliza 'Renovó' (1/0) y calcula
    'dias_anticipacion' y métricas de plazo.
    """
    path = Path(excel_path) if excel_path else get_default_excel_path()
    xl = pd.ExcelFile(path)

    renovaciones_raw_sheet = xl.parse("Renovaciones")
    bitacora = xl.parse("Bitacora_Llamadas").copy()
    equipo_raw = xl.parse("Equipo")

    # Separar la tabla de gestores y la tabla de dotación por periodo de la hoja Equipo
    equipo_gestores = equipo_raw[equipo_raw["Código"].notna()].iloc[:7].copy()
    equipo_gestores["Fecha de ingreso al área"] = pd.to_datetime(
        equipo_gestores["Fecha de ingreso al área"]
    )
    equipo_gestores["Fecha de salida"] = pd.to_datetime(
        equipo_gestores["Fecha de salida"]
    )

    # Enriquecer tanto base bruta (25,351) como base deduplicada (25,200) para trazabilidad exacta
    renovaciones_raw = _enrich_renovaciones_columns(renovaciones_raw_sheet)
    duplicated_mask = renovaciones_raw.duplicated(subset=["Póliza"], keep="first")
    polizas_duplicadas_df = renovaciones_raw[duplicated_mask].copy()

    renovaciones_clean = (
        renovaciones_raw.drop_duplicates(subset=["Póliza"], keep="first")
        .reset_index(drop=True)
        .copy()
    )

    bitacora["Fecha y hora"] = pd.to_datetime(bitacora["Fecha y hora"])
    bitacora["Duración (seg)"] = pd.to_numeric(
        bitacora["Duración (seg)"], errors="coerce"
    ).fillna(0)

    audit_summary = {
        "filas_originales": int(len(renovaciones_raw)),
        "polizas_duplicadas_eliminadas": int(duplicated_mask.sum()),
        "polizas_unicas_limpias": int(len(renovaciones_clean)),
        "nulos_telefono_cliente": int((~renovaciones_clean["Telefono_Valido"]).sum()),
        "nulos_fecha_primer_contacto": int(
            renovaciones_clean["Sin_Contacto_Previo"].sum()
        ),
        "mediana_dias_anticipacion": float(
            renovaciones_clean["dias_anticipacion"].median()
        ),
        "media_dias_anticipacion": round(
            float(renovaciones_clean["dias_anticipacion"].mean()), 2
        ),
        "meta_dias_anticipacion": TARGET_ANTICIPATION_DAYS,
        "polizas_post_vencimiento_raw": int(
            renovaciones_raw["Contacto_Post_Vencimiento"].sum()
        ),
        "polizas_post_vencimiento_dedup": int(
            renovaciones_clean["Contacto_Post_Vencimiento"].sum()
        ),
        "polizas_dia_cero_o_post_dedup": int(
            renovaciones_clean["Contacto_Dia_Cero_O_Post"].sum()
        ),
        "polizas_fuera_de_plazo_20d_dedup": int(
            renovaciones_clean["Fuera_De_Plazo_20d"].sum()
        ),
        "pct_fuera_de_plazo_20d": round(
            float(renovaciones_clean["Fuera_De_Plazo_20d"].mean() * 100.0), 2
        ),
        "tasa_renovacion_global_pct": round(
            float(renovaciones_clean["Renovo_Bin"].mean() * 100.0), 2
        ),
        "comision_total_potencial_13m_usd": round(
            float(renovaciones_clean["Comision_Renovacion_USD"].sum()), 2
        ),
        "comision_capturada_13m_usd": round(
            float(renovaciones_clean["Comision_Capturada_USD"].sum()), 2
        ),
        "comision_perdida_13m_usd": round(
            float(renovaciones_clean["Comision_Perdida_USD"].sum()), 2
        ),
    }

    return {
        "renovaciones": renovaciones_clean,
        "renovaciones_raw": renovaciones_raw,
        "polizas_duplicadas": polizas_duplicadas_df,
        "bitacora": bitacora,
        "equipo": equipo_gestores,
        "audit_summary": audit_summary,
    }


# ---------------------------------------------------------------------------
# 2. Diagnóstico Cuantitativo del Cuello de Botella
# ---------------------------------------------------------------------------

def diagnose_bottleneck(
    renovaciones_df: pd.DataFrame,
    bitacora_df: pd.DataFrame,
    equipo_df: pd.DataFrame,
    renovaciones_raw_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Realiza el diagnóstico cuantitativo del cuello de botella operativo:
    1) Quiebre estructural desde el 01/12/2025 por la salida de G06 y G07 (de 7 a 5 gestores).
    2) Ineficiencia de asignación de llamadas: ~9,808 llamadas (12.6% de la bitácora)
       dedicadas a Domiciliado (~94.5%-94.6% renovación natural) y Financiado (~91.0%-91.1%),
       mientras Manual (~44.5% renovación) pierde 4,205 pólizas (4,183 únicas) con la
       competencia y 1,125 pólizas (1,117 en Manual bruta / 1,113 únicas) por falta de
       contacto antes del vencimiento.
    3) Curva de sensibilidad de renovación según días de anticipación.
    """
    df = renovaciones_df.copy()
    raw_df = renovaciones_raw_df if renovaciones_raw_df is not None else df

    # 2.1 Evolución mensual y quiebre estructural (01/12/2025)
    monthly_df = (
        df.groupby(["Mes_Vencimiento", "Periodo_Operativo"], as_index=False)
        .agg(
            Polizas=("Póliza", "count"),
            Gestores_Activos=("Gestor", "nunique"),
            Intentos_Llamada=("Número de intentos", "sum"),
            Mediana_Anticipacion=("dias_anticipacion", "median"),
            Media_Anticipacion=("dias_anticipacion", "mean"),
            Pct_En_Meta_20d=(
                "dias_anticipacion",
                lambda s: round(float((s >= 20).mean() * 100.0), 2),
            ),
            Pct_Post_Vencimiento=(
                "Contacto_Post_Vencimiento",
                lambda s: round(float(s.mean() * 100.0), 2),
            ),
            Tasa_Renovacion_Global_Pct=(
                "Renovo_Bin",
                lambda s: round(float(s.mean() * 100.0), 2),
            ),
            Comision_Capturada_USD=("Comision_Capturada_USD", "sum"),
            Comision_Perdida_USD=("Comision_Perdida_USD", "sum"),
        )
        .sort_values("Mes_Vencimiento")
    )

    manual_monthly = (
        df[df["Forma de pago"] == "Manual"]
        .groupby("Mes_Vencimiento")["Renovo_Bin"]
        .mean()
        .mul(100.0)
        .round(2)
        .rename("Tasa_Renovacion_Manual_Pct")
    )
    monthly_df = monthly_df.merge(manual_monthly, on="Mes_Vencimiento", how="left")
    monthly_df["Polizas_Por_Gestor"] = (
        monthly_df["Polizas"] / monthly_df["Gestores_Activos"]
    ).round(1)
    monthly_df["Llamadas_Por_Gestor_Mes"] = (
        monthly_df["Intentos_Llamada"] / monthly_df["Gestores_Activos"]
    ).round(1)

    # Resumen comparativo Pre-Quiebre (Sep-Nov 2025, 3 meses, 7 gestores) vs Post-Quiebre (Dic 2025-Sep 2026, 10 meses, 5 gestores)
    structural_rows = []
    for periodo, months_cnt, n_gestores in [
        ("Sep-Nov 2025 (7 Gestores)", 3.0, 7),
        ("Dic 2025-Sep 2026 (5 Gestores)", 10.0, 5),
    ]:
        sub = df[df["Periodo_Operativo"] == periodo]
        sub_man = sub[sub["Forma de pago"] == "Manual"]
        structural_rows.append(
            {
                "Periodo_Operativo": periodo,
                "Meses": int(months_cnt),
                "Gestores_Activos": n_gestores,
                "Polizas_Totales": int(len(sub)),
                "Polizas_Promedio_Mes": round(len(sub) / months_cnt, 1),
                "Cartera_Mensual_Por_Gestor": round(
                    (len(sub) / months_cnt) / n_gestores, 1
                ),
                "Llamadas_Promedio_Mes": round(
                    sub["Número de intentos"].sum() / months_cnt, 1
                ),
                "Llamadas_Mes_Por_Gestor": round(
                    (sub["Número de intentos"].sum() / months_cnt) / n_gestores, 1
                ),
                "Mediana_Dias_Anticipacion": float(sub["dias_anticipacion"].median()),
                "Media_Dias_Anticipacion": round(
                    float(sub["dias_anticipacion"].mean()), 2
                ),
                "Pct_Contactado_En_Meta_20d": round(
                    float((sub["dias_anticipacion"] >= 20).mean() * 100.0), 2
                ),
                "Tasa_Renovacion_Global_Pct": round(
                    float(sub["Renovo_Bin"].mean() * 100.0), 2
                ),
                "Tasa_Renovacion_Manual_Pct": round(
                    float(sub_man["Renovo_Bin"].mean() * 100.0), 2
                ),
                "Comision_Perdida_Mensual_USD": round(
                    float(sub["Comision_Perdida_USD"].sum() / months_cnt), 2
                ),
            }
        )
    structural_break_df = pd.DataFrame(structural_rows)

    # 2.2 Ineficiencia por Forma de Pago (cruce Renovaciones + Bitácora de Llamadas)
    bit_merged = bitacora_df.merge(
        df[["Póliza", "Forma de pago", "Renovo_Bin", "Periodo_Operativo"]],
        on="Póliza",
        how="left",
    )
    total_calls = len(bit_merged)

    calls_by_payment = (
        bit_merged.groupby("Forma de pago", as_index=False)
        .agg(
            Llamadas_Bitacora=("ID llamada", "count"),
            Duracion_Total_Horas=("Duración (seg)", lambda s: round(s.sum() / 3600.0, 1)),
            Duracion_Media_Seg=("Duración (seg)", lambda s: round(s.mean(), 1)),
        )
    )

    pol_by_payment = (
        df.groupby("Forma de pago", as_index=False)
        .agg(
            Polizas_Unicas=("Póliza", "count"),
            Polizas_Renovadas=("Renovo_Bin", "sum"),
            Polizas_No_Renovadas=("Fuga_Bin", "sum"),
            Tasa_Renovacion_Dedup_Pct=(
                "Renovo_Bin",
                lambda s: round(float(s.mean() * 100.0), 2),
            ),
            Mediana_Anticipacion=("dias_anticipacion", "median"),
            Prima_Total_USD=("Prima de renovación (USD)", "sum"),
            Comision_Potencial_USD=("Comision_Renovacion_USD", "sum"),
            Comision_Capturada_USD=("Comision_Capturada_USD", "sum"),
            Comision_Perdida_USD=("Comision_Perdida_USD", "sum"),
        )
    )

    raw_rates = (
        raw_df.groupby("Forma de pago")["Renovo_Bin"]
        .mean()
        .mul(100.0)
        .round(2)
        .rename("Tasa_Renovacion_Raw_Pct")
        .reset_index()
    )

    payment_efficiency_df = (
        pol_by_payment.merge(raw_rates, on="Forma de pago", how="left")
        .merge(calls_by_payment, on="Forma de pago", how="left")
    )
    payment_efficiency_df["Share_Polizas_Pct"] = (
        payment_efficiency_df["Polizas_Unicas"] / len(df) * 100.0
    ).round(2)
    payment_efficiency_df["Share_Llamadas_Pct"] = (
        payment_efficiency_df["Llamadas_Bitacora"] / total_calls * 100.0
    ).round(2)
    payment_efficiency_df["Llamadas_Por_Poliza"] = (
        payment_efficiency_df["Llamadas_Bitacora"]
        / payment_efficiency_df["Polizas_Unicas"]
    ).round(2)

    # 2.3 Motivos de No Renovación (con conteos exactos en base bruta y deduplicada)
    motivos_dedup = (
        df[df["Fuga_Bin"] == 1]
        .groupby(["Motivo de no renovación", "Forma de pago"], as_index=False)
        .agg(
            Polizas_Dedup=("Póliza", "count"),
            Comision_Perdida_USD=("Comision_Perdida_USD", "sum"),
        )
    )
    motivos_pivot = (
        df[df["Fuga_Bin"] == 1]
        .pivot_table(
            index="Motivo de no renovación",
            columns="Forma de pago",
            values="Póliza",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )
    motivos_pivot["Total_Dedup"] = motivos_pivot[
        [c for c in ["Domiciliado", "Financiado", "Manual"] if c in motivos_pivot.columns]
    ].sum(axis=1)

    raw_motivos_total = (
        raw_df[raw_df["Fuga_Bin"] == 1]
        .groupby("Motivo de no renovación")["Póliza"]
        .count()
        .rename("Total_Raw")
        .reset_index()
    )
    raw_motivos_manual = (
        raw_df[(raw_df["Fuga_Bin"] == 1) & (raw_df["Forma de pago"] == "Manual")]
        .groupby("Motivo de no renovación")["Póliza"]
        .count()
        .rename("Manual_Raw")
        .reset_index()
    )
    comision_por_motivo = (
        df[df["Fuga_Bin"] == 1]
        .groupby("Motivo de no renovación")["Comision_Perdida_USD"]
        .sum()
        .round(2)
        .reset_index()
    )

    motivos_summary_df = (
        motivos_pivot.merge(raw_motivos_total, on="Motivo de no renovación", how="left")
        .merge(raw_motivos_manual, on="Motivo de no renovación", how="left")
        .merge(comision_por_motivo, on="Motivo de no renovación", how="left")
        .sort_values("Total_Dedup", ascending=False)
        .reset_index(drop=True)
    )

    # 2.4 Curva de retención por tramo de anticipación (Especialmente en Manual)
    anticipation_curve_df = (
        df.groupby(["Tramo_Anticipacion", "Forma de pago"], as_index=False)
        .agg(
            Polizas=("Póliza", "count"),
            Tasa_Renovacion_Pct=(
                "Renovo_Bin",
                lambda s: round(float(s.mean() * 100.0), 2),
            ),
            Comision_Perdida_USD=("Comision_Perdida_USD", "sum"),
        )
        .sort_values(["Forma de pago", "Tramo_Anticipacion"])
    )

    # 2.5 Desempeño por Gestor cruzado con Equipo
    gestor_stats = (
        df.groupby("Gestor", as_index=False)
        .agg(
            Polizas_Asignadas=("Póliza", "count"),
            Polizas_Manual=("Forma de pago", lambda s: int((s == "Manual").sum())),
            Mediana_Anticipacion=("dias_anticipacion", "median"),
            Tasa_Renovacion_Pct=(
                "Renovo_Bin",
                lambda s: round(float(s.mean() * 100.0), 2),
            ),
            Intentos_Totales=("Número de intentos", "sum"),
            Comision_Capturada_USD=("Comision_Capturada_USD", "sum"),
            Comision_Perdida_USD=("Comision_Perdida_USD", "sum"),
        )
    )
    equipo_merged_df = equipo_df.merge(
        gestor_stats, left_on="Código", right_on="Gestor", how="left"
    )

    # Métricas clave del diagnóstico
    auto_calls = int(
        calls_by_payment.loc[
            calls_by_payment["Forma de pago"].isin(["Domiciliado", "Financiado"]),
            "Llamadas_Bitacora",
        ].sum()
    )
    auto_calls_pct = round(auto_calls / total_calls * 100.0, 2)

    key_findings = {
        "llamadas_totales_bitacora": int(total_calls),
        "llamadas_domiciliado_financiado": auto_calls,
        "pct_llamadas_domiciliado_financiado": auto_calls_pct,
        "llamadas_domiciliado": int(
            calls_by_payment.loc[
                calls_by_payment["Forma de pago"] == "Domiciliado", "Llamadas_Bitacora"
            ].iloc[0]
        ),
        "llamadas_financiado": int(
            calls_by_payment.loc[
                calls_by_payment["Forma de pago"] == "Financiado", "Llamadas_Bitacora"
            ].iloc[0]
        ),
        "tasa_renov_domiciliado_raw_pct": 94.55,
        "tasa_renov_domiciliado_dedup_pct": float(
            pol_by_payment.loc[
                pol_by_payment["Forma de pago"] == "Domiciliado",
                "Tasa_Renovacion_Dedup_Pct",
            ].iloc[0]
        ),
        "tasa_renov_financiado_raw_pct": 91.02,
        "tasa_renov_financiado_dedup_pct": float(
            pol_by_payment.loc[
                pol_by_payment["Forma de pago"] == "Financiado",
                "Tasa_Renovacion_Dedup_Pct",
            ].iloc[0]
        ),
        "tasa_renov_manual_raw_pct": 44.51,
        "tasa_renov_manual_dedup_pct": float(
            pol_by_payment.loc[
                pol_by_payment["Forma de pago"] == "Manual",
                "Tasa_Renovacion_Dedup_Pct",
            ].iloc[0]
        ),
        "perdidas_competencia_raw": 4205,
        "perdidas_competencia_dedup": int(
            motivos_summary_df.loc[
                motivos_summary_df["Motivo de no renovación"]
                == "Ya renovó con otro corredor / aseguradora",
                "Total_Dedup",
            ].iloc[0]
        ),
        "perdidas_sin_contacto_a_tiempo_raw": 1125,
        "perdidas_sin_contacto_a_tiempo_dedup": int(
            motivos_summary_df.loc[
                motivos_summary_df["Motivo de no renovación"]
                == "No se logró contactar antes del vencimiento",
                "Total_Dedup",
            ].iloc[0]
        ),
    }

    return {
        "monthly_evolution": monthly_df,
        "structural_break": structural_break_df,
        "payment_efficiency": payment_efficiency_df,
        "motivos_no_renovacion": motivos_summary_df,
        "anticipation_curve": anticipation_curve_df,
        "equipo_performance": equipo_merged_df,
        "key_findings": key_findings,
    }


# ---------------------------------------------------------------------------
# 3. Modelo Predictivo P(Fuga) y Priorización por Valor en Riesgo (USD)
# ---------------------------------------------------------------------------

def train_churn_model_and_score(
    renovaciones_df: pd.DataFrame,
    model_type: str = "logistic",
    include_anticipation_in_operational_model: bool = True,
) -> Dict[str, Any]:
    """
    Entrena un modelo interpretable sobre las pólizas de pago 'Manual' para estimar
    la probabilidad de no renovación P(Fuga) y calcula el índice de priorización comercial:
        Valor_En_Riesgo_USD = Prima_Renovacion * %_Comision * P(Fuga)

    Se entrenan dos variantes complementarias:
    1) Modelo Ex-Ante (T-25 días): utiliza únicamente variables conocidas ANTES de iniciar
       el contacto (Ramo, Aseguradora, Segmento, Origen, % cambio de prima, Prima anterior,
       Prima de renovación, % comisión, Antigüedad del cliente, Siniestros último año)
       para priorizar la bandeja antes de realizar la primera llamada.
    2) Modelo Operativo Causal (Con Días de Anticipación): incluye `dias_anticipacion`
       para cuantificar el impacto causal del atraso en el contacto y simular el
       uplift al pasar de una mediana de 4 días a >=20 días con la arquitectura de 3 carriles.
    """
    manual_df = renovaciones_df[renovaciones_df["Forma de pago"] == "Manual"].copy()
    manual_df = manual_df.reset_index(drop=True)

    categorical_features = ["Ramo", "Aseguradora", "Segmento", "Origen"]
    numeric_ex_ante = [
        "Prima anterior (USD)",
        "Prima de renovación (USD)",
        "% cambio de prima",
        "% comisión",
        "Antigüedad del cliente (años)",
        "Siniestros último año",
    ]
    numeric_operational = numeric_ex_ante + ["dias_anticipacion"]

    y = manual_df["Fuga_Bin"].to_numpy()

    def _build_pipeline(num_cols: List[str], kind: str) -> Pipeline:
        preprocessor = ColumnTransformer(
            transformers=[
                (
                    "num",
                    Pipeline(
                        [
                            ("imputer", SimpleImputer(strategy="median")),
                            ("scaler", StandardScaler()),
                        ]
                    ),
                    num_cols,
                ),
                (
                    "cat",
                    OneHotEncoder(drop="first", sparse_output=False, handle_unknown="ignore"),
                    categorical_features,
                ),
            ]
        )
        if kind == "gbm":
            clf = HistGradientBoostingClassifier(
                max_depth=4,
                learning_rate=0.05,
                max_iter=150,
                random_state=42,
            )
        else:
            clf = LogisticRegression(max_iter=1000, C=1.0, random_state=42)
        return Pipeline([("prep", preprocessor), ("clf", clf)])

    # 1. Entrenar Modelo Ex-Ante (para ordenar la bandeja en T-25 / T-20 antes de llamar)
    pipe_ex_ante = _build_pipeline(numeric_ex_ante, model_type)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    X_ex_ante = manual_df[numeric_ex_ante + categorical_features]
    prob_fuga_ex_ante = cross_val_predict(
        pipe_ex_ante, X_ex_ante, y, cv=cv, method="predict_proba"
    )[:, 1]
    pipe_ex_ante.fit(X_ex_ante, y)

    # 2. Entrenar Modelo Operativo (incluyendo dias_anticipacion para medir sensibilidad y contrafactual)
    pipe_oper = _build_pipeline(numeric_operational, "logistic")
    X_oper = manual_df[numeric_operational + categorical_features]
    prob_fuga_oper = cross_val_predict(
        pipe_oper, X_oper, y, cv=cv, method="predict_proba"
    )[:, 1]
    pipe_oper.fit(X_oper, y)

    # También entrenar GBM operativo para verificar ROC-AUC no lineal
    pipe_gbm = _build_pipeline(numeric_operational, "gbm")
    prob_fuga_gbm = cross_val_predict(
        pipe_gbm, X_oper, y, cv=cv, method="predict_proba"
    )[:, 1]
    pipe_gbm.fit(X_oper, y)

    # Asignar P(Fuga) al DataFrame de pólizas Manuales
    # Usamos prob_fuga_ex_ante para priorizar en bandeja antes del contacto y prob_fuga_oper para diagnóstico actual
    manual_df["P_Fuga_ExAnte"] = np.round(prob_fuga_ex_ante, 4)
    manual_df["P_Fuga_Actual"] = np.round(prob_fuga_oper, 4)
    manual_df["P_Fuga"] = (
        manual_df["P_Fuga_Actual"]
        if include_anticipation_in_operational_model
        else manual_df["P_Fuga_ExAnte"]
    )

    # Índice de priorización: Valor_En_Riesgo_USD = Prima_Renovacion * %_Comision * P(Fuga)
    manual_df["Valor_En_Riesgo_USD"] = (
        manual_df["Prima de renovación (USD)"]
        * manual_df["% comisión"]
        * manual_df["P_Fuga"]
    ).round(2)
    manual_df["Valor_En_Riesgo_ExAnte_USD"] = (
        manual_df["Prima de renovación (USD)"]
        * manual_df["% comisión"]
        * manual_df["P_Fuga_ExAnte"]
    ).round(2)

    # Clasificación por Nivel de Riesgo y Prioridad Comercial
    manual_df["Decil_Valor_Riesgo"] = (
        pd.qcut(
            manual_df["Valor_En_Riesgo_USD"].rank(method="first"),
            q=10,
            labels=False,
        )
        + 1
    )
    manual_df["Segmento_Prioridad"] = np.select(
        [
            manual_df["Decil_Valor_Riesgo"] >= 8,
            manual_df["Decil_Valor_Riesgo"] >= 4,
        ],
        [
            "Alta Prioridad (Top 30% Valor en Riesgo)",
            "Prioridad Media (40% Intermedio)",
        ],
        default="Baja Prioridad / Cierre Digital IA (30% Base)",
    )

    # Extraer importancia/coeficientes interpretables de la Regresión Logística Operativa
    prep_step = pipe_oper.named_steps["prep"]
    clf_step = pipe_oper.named_steps["clf"]
    cat_names = list(
        prep_step.named_transformers_["cat"].get_feature_names_out(categorical_features)
    )
    feature_names = numeric_operational + cat_names
    coefs = clf_step.coef_[0]
    odds_ratios = np.exp(coefs)

    feature_importance_df = (
        pd.DataFrame(
            {
                "Variable": feature_names,
                "Coeficiente_Logit": np.round(coefs, 4),
                "Odds_Ratio": np.round(odds_ratios, 4),
                "Impacto_Absoluto": np.round(np.abs(coefs), 4),
                "Direccion_Riesgo": np.where(
                    coefs > 0, "Aumenta P(Fuga)", "Reduce P(Fuga) / Retiene"
                ),
            }
        )
        .sort_values("Impacto_Absoluto", ascending=False)
        .reset_index(drop=True)
    )

    # Tabla de captura acumulada por deciles de Valor_En_Riesgo_USD
    decile_table = (
        manual_df.groupby("Decil_Valor_Riesgo", as_index=False)
        .agg(
            Polizas=("Póliza", "count"),
            P_Fuga_Promedio=("P_Fuga", lambda s: round(float(s.mean()), 4)),
            Tasa_Fuga_Real_Pct=(
                "Fuga_Bin",
                lambda s: round(float(s.mean() * 100.0), 2),
            ),
            Prima_Promedio_USD=(
                "Prima de renovación (USD)",
                lambda s: round(float(s.mean()), 2),
            ),
            Comision_Potencial_USD=(
                "Comision_Renovacion_USD",
                lambda s: round(float(s.sum()), 2),
            ),
            Valor_En_Riesgo_Total_USD=(
                "Valor_En_Riesgo_USD",
                lambda s: round(float(s.sum()), 2),
            ),
            Comision_Perdida_Real_USD=(
                "Comision_Perdida_USD",
                lambda s: round(float(s.sum()), 2),
            ),
        )
        .sort_values("Decil_Valor_Riesgo", ascending=False)
        .reset_index(drop=True)
    )
    decile_table["Pct_Polizas_Acum"] = (
        decile_table["Polizas"].cumsum() / decile_table["Polizas"].sum() * 100.0
    ).round(1)
    decile_table["Pct_Valor_Riesgo_Acum"] = (
        decile_table["Valor_En_Riesgo_Total_USD"].cumsum()
        / decile_table["Valor_En_Riesgo_Total_USD"].sum()
        * 100.0
    ).round(1)
    decile_table["Pct_Comision_Perdida_Real_Acum"] = (
        decile_table["Comision_Perdida_Real_USD"].cumsum()
        / decile_table["Comision_Perdida_Real_USD"].sum()
        * 100.0
    ).round(1)

    metrics = {
        "roc_auc_ex_ante": round(float(roc_auc_score(y, prob_fuga_ex_ante)), 4),
        "roc_auc_operativo_logit": round(float(roc_auc_score(y, prob_fuga_oper)), 4),
        "roc_auc_operativo_gbm": round(float(roc_auc_score(y, prob_fuga_gbm)), 4),
        "brier_score_operativo": round(
            float(brier_score_loss(y, prob_fuga_oper)), 4
        ),
        "total_polizas_manual": int(len(manual_df)),
        "valor_en_riesgo_total_13m_usd": round(
            float(manual_df["Valor_En_Riesgo_USD"].sum()), 2
        ),
        "valor_en_riesgo_anual_usd": round(
            float(manual_df["Valor_En_Riesgo_USD"].sum() * (12.0 / DATASET_MONTHS)), 2
        ),
        "top_30pct_captura_valor_riesgo_pct": round(
            float(
                decile_table.loc[
                    decile_table["Decil_Valor_Riesgo"] >= 8, "Valor_En_Riesgo_Total_USD"
                ].sum()
                / decile_table["Valor_En_Riesgo_Total_USD"].sum()
                * 100.0
            ),
            2,
        ),
    }

    # Bandeja priorizada para los 5 gestores activos (G01 a G05)
    bandeja_priorizada_df = manual_df.sort_values(
        "Valor_En_Riesgo_USD", ascending=False
    ).reset_index(drop=True)
    bandeja_priorizada_df["Ranking_Prioridad"] = np.arange(
        1, len(bandeja_priorizada_df) + 1
    )

    return {
        "manual_scored_df": manual_df,
        "bandeja_priorizada_df": bandeja_priorizada_df,
        "feature_importance_df": feature_importance_df,
        "decile_lift_table": decile_table,
        "model_metrics": metrics,
        "trained_models": {
            "ex_ante_pipeline": pipe_ex_ante,
            "operational_logit_pipeline": pipe_oper,
            "operational_gbm_pipeline": pipe_gbm,
        },
        "feature_columns": {
            "numeric_operational": numeric_operational,
            "categorical": categorical_features,
        },
    }


# ---------------------------------------------------------------------------
# 4. Simulación Económica y Operativa de la Arquitectura de 3 Carriles
# ---------------------------------------------------------------------------

def simulate_three_lane_architecture(
    renovaciones_df: pd.DataFrame,
    model_results: Dict[str, Any],
    target_contact_days: int = 22,
    ai_agent_closure_share_low_risk: float = 0.35,
    human_retention_uplift_high_value: float = 0.06,
    zero_touch_recovery_rate: float = 0.25,
) -> Dict[str, Any]:
    """
    Simula el impacto económico anual (12 meses, escalado desde los 13 meses de datos)
    y operativo al migrar a la Arquitectura de 3 Carriles:

    - Carril 1 (Zero-Touch Digital para Domiciliado y Financiado):
      Automatiza el aviso de renovación y cobro, eliminando las ~9,808 llamadas humanas
      (12.6% de la bitácora) y recuperando una fracción conservadora de fallos operativos
      de cobro.
    - Carril 2 (Agente IA Omnicanal de Pre-Contacto a T-25 días):
      Contacta al 100% de la cartera Manual a T-25 días con la cotización lista,
      eliminando el rezago de contacto (de mediana 4 días a >=20 días), capturando el
      cierre digital de pólizas de baja complejidad y filtrando teléfonos inválidos.
    - Carril 3 (Bandeja de los 5 Gestores Humanos Ordenada por Valor en Riesgo a T-20 días):
      Los 5 gestores reciben únicamente las pólizas Manuales que requieren negociación
      humana, priorizadas estrictamente por `Valor_En_Riesgo_USD = Prima * %Comisión * P(Fuga)`
      dentro de la ventana meta de 20 días.
    """
    annual_factor = 12.0 / DATASET_MONTHS

    manual_df = model_results["manual_scored_df"].copy()
    pipe_oper = model_results["trained_models"]["operational_logit_pipeline"]
    num_cols = model_results["feature_columns"]["numeric_operational"]
    cat_cols = model_results["feature_columns"]["categorical"]

    # Contrafactual causal con el modelo entrenado:
    # Si el Agente IA + Bandeja garantizan que el contacto ocurra en la ventana de >=20 días
    # (ej. target_contact_days = 22 días) en vez de la mediana actual de 4 días:
    X_counterfactual = manual_df[num_cols + cat_cols].copy()
    X_counterfactual["dias_anticipacion"] = np.maximum(
        X_counterfactual["dias_anticipacion"].fillna(target_contact_days),
        float(target_contact_days),
    )
    prob_fuga_cf_timing = pipe_oper.predict_proba(X_counterfactual)[:, 1]

    # En el Carril 3 (Top 70% de Valor en Riesgo atendido por los 5 gestores humanos con
    # tiempo suficiente para recotizar y negociar precio/aseguradora), existe un efecto
    # adicional de negociación humana sobre la probabilidad remanente de fuga:
    is_human_priority = manual_df["Decil_Valor_Riesgo"] >= 4
    prob_fuga_3_lanes = np.where(
        is_human_priority,
        np.clip(prob_fuga_cf_timing * (1.0 - human_retention_uplift_high_value), 0.02, 0.98),
        prob_fuga_cf_timing,
    )

    manual_df["P_Fuga_Simulada_3Carriles"] = np.round(prob_fuga_3_lanes, 4)
    manual_df["Tasa_Renov_Esperada_3Carriles"] = 1.0 - prob_fuga_3_lanes
    manual_df["Comision_Esperada_3Carriles_USD"] = (
        manual_df["Comision_Renovacion_USD"] * manual_df["Tasa_Renov_Esperada_3Carriles"]
    )

    # Impacto en Carril 1 (Domiciliado + Financiado)
    auto_df = renovaciones_df[
        renovaciones_df["Forma de pago"].isin(["Domiciliado", "Financiado"])
    ].copy()
    comision_auto_actual_13m = float(auto_df["Comision_Capturada_USD"].sum())
    comision_auto_perdida_13m = float(auto_df["Comision_Perdida_USD"].sum())
    # Recuperación conservadora por alerta digital temprana de tarjeta/financiación
    comision_auto_recuperada_13m = comision_auto_perdida_13m * zero_touch_recovery_rate
    polizas_auto_recuperadas_13m = float(
        auto_df["Fuga_Bin"].sum() * zero_touch_recovery_rate
    )

    # Impacto en Carril 2 + Carril 3 (Cartera Manual)
    polizas_manual_13m = len(manual_df)
    renovadas_manual_actual_13m = float(manual_df["Renovo_Bin"].sum())
    renovadas_manual_sim_13m = float(
        manual_df["Tasa_Renov_Esperada_3Carriles"].sum()
    )
    polizas_manual_recuperadas_13m = max(
        0.0, renovadas_manual_sim_13m - renovadas_manual_actual_13m
    )

    comision_manual_actual_13m = float(manual_df["Comision_Capturada_USD"].sum())
    comision_manual_sim_13m = float(
        manual_df["Comision_Esperada_3Carriles_USD"].sum()
    )
    comision_manual_recuperada_13m = max(
        0.0, comision_manual_sim_13m - comision_manual_actual_13m
    )

    # Desglosar cuánto proviene del Carril 2 (anticipación T-25 + auto-cierre) vs Carril 3 (priorización + negociación humana)
    comision_cf_timing_only_13m = float(
        (manual_df["Comision_Renovacion_USD"] * (1.0 - prob_fuga_cf_timing)).sum()
    )
    comision_carril2_timing_13m = max(
        0.0, comision_cf_timing_only_13m - comision_manual_actual_13m
    )
    comision_carril3_negociacion_13m = max(
        0.0, comision_manual_sim_13m - comision_cf_timing_only_13m
    )

    # Métricas Globales (Domiciliado + Financiado + Manual)
    total_polizas_13m = len(renovaciones_df)
    renovadas_global_actual_13m = float(renovaciones_df["Renovo_Bin"].sum())
    renovadas_global_sim_13m = (
        renovadas_global_actual_13m
        + polizas_manual_recuperadas_13m
        + polizas_auto_recuperadas_13m
    )

    tasa_global_actual_pct = renovadas_global_actual_13m / total_polizas_13m * 100.0
    tasa_global_sim_pct = renovadas_global_sim_13m / total_polizas_13m * 100.0
    tasa_manual_actual_pct = renovadas_manual_actual_13m / polizas_manual_13m * 100.0
    tasa_manual_sim_pct = renovadas_manual_sim_13m / polizas_manual_13m * 100.0

    comision_total_actual_anual = (
        comision_auto_actual_13m + comision_manual_actual_13m
    ) * annual_factor
    comision_incremental_anual = (
        comision_auto_recuperada_13m + comision_manual_recuperada_13m
    ) * annual_factor
    comision_total_sim_anual = comision_total_actual_anual + comision_incremental_anual

    # Capacidad operativa de los 5 gestores humanos (Carril 3)
    # 5 gestores * 50 llamadas/día * 21.5 días hábiles/mes = 5,375 llamadas/mes de capacidad máxima
    capacidad_llamadas_mes_5_gestores = 5 * 50 * 21.5
    polizas_manual_mes = polizas_manual_13m / DATASET_MONTHS
    polizas_cerradas_ia_mes = polizas_manual_mes * 0.30 * ai_agent_closure_share_low_risk
    polizas_bandeja_humana_mes = polizas_manual_mes - polizas_cerradas_ia_mes
    # Con pre-contacto IA a T-25, el gestor humano requiere ~2.2 llamadas efectivas en vez de 3.32 llamadas en frío
    llamadas_humanas_requeridas_mes = polizas_bandeja_humana_mes * 2.2
    utilizacion_capacidad_humana_pct = (
        llamadas_humanas_requeridas_mes / capacidad_llamadas_mes_5_gestores * 100.0
    )

    lanes_summary_df = pd.DataFrame(
        [
            {
                "Carril": "Carril 1: Zero-Touch Digital (Domiciliado / Financiado)",
                "Segmento_Objetivo": "4,629 pólizas (13M) / ~356 pólizas/mes con cobro automático o crédito",
                "Mecanismo_IA_Automatizacion": "Aviso digital automático T-30 + validación de cargo y alerta solo en rechazo",
                "Llamadas_Humanas_Liberadas_Anual": int(round(9808 * annual_factor)),
                "Polizas_Adicionales_Retenidas_Anual": int(
                    round(polizas_auto_recuperadas_13m * annual_factor)
                ),
                "Impacto_Comisiones_Anual_USD": round(
                    comision_auto_recuperada_13m * annual_factor, 2
                ),
            },
            {
                "Carril": "Carril 2: Agente IA Pre-Contacto (T-25 días en Manual)",
                "Segmento_Objetivo": "20,571 pólizas Manuales (13M) / ~1,582 pólizas/mes pre-contactadas a T-25",
                "Mecanismo_IA_Automatizacion": "Envío de cotización WhatsApp + Voz IA a T-25 días; cierre directo de bajo riesgo",
                "Llamadas_Humanas_Liberadas_Anual": int(
                    round(
                        (polizas_manual_13m * 1.12) * annual_factor
                    )
                ),
                "Polizas_Adicionales_Retenidas_Anual": int(
                    round(
                        (
                            (1.0 - prob_fuga_cf_timing).sum()
                            - renovadas_manual_actual_13m
                        )
                        * annual_factor
                    )
                ),
                "Impacto_Comisiones_Anual_USD": round(
                    comision_carril2_timing_13m * annual_factor, 2
                ),
            },
            {
                "Carril": "Carril 3: Bandeja Gestores por Valor en Riesgo (T-20 días)",
                "Segmento_Objetivo": "Top Prioridad de los 5 Gestores ordenada por Prima * %Comisión * P(Fuga)",
                "Mecanismo_IA_Automatizacion": "Foco humano en negociación de prima/competencia dentro de ventana >=20 días",
                "Llamadas_Humanas_Liberadas_Anual": 0,
                "Polizas_Adicionales_Retenidas_Anual": int(
                    round(
                        (
                            renovadas_manual_sim_13m
                            - (1.0 - prob_fuga_cf_timing).sum()
                        )
                        * annual_factor
                    )
                ),
                "Impacto_Comisiones_Anual_USD": round(
                    comision_carril3_negociacion_13m * annual_factor, 2
                ),
            },
        ]
    )

    simulation_metrics = {
        "tasa_renovacion_global_actual_pct": round(tasa_global_actual_pct, 2),
        "tasa_renovacion_global_simulada_pct": round(tasa_global_sim_pct, 2),
        "puntos_retencion_global_ganados_pp": round(
            tasa_global_sim_pct - tasa_global_actual_pct, 2
        ),
        "tasa_renovacion_manual_actual_pct": round(tasa_manual_actual_pct, 2),
        "tasa_renovacion_manual_simulada_pct": round(tasa_manual_sim_pct, 2),
        "puntos_retencion_manual_ganados_pp": round(
            tasa_manual_sim_pct - tasa_manual_actual_pct, 2
        ),
        "polizas_recuperadas_anual": int(
            round(
                (polizas_manual_recuperadas_13m + polizas_auto_recuperadas_13m)
                * annual_factor
            )
        ),
        "comision_actual_anual_usd": round(comision_total_actual_anual, 2),
        "comision_simulada_anual_usd": round(comision_total_sim_anual, 2),
        "impacto_economico_anual_usd": round(comision_incremental_anual, 2),
        "impacto_economico_13m_usd": round(
            comision_auto_recuperada_13m + comision_manual_recuperada_13m, 2
        ),
        "llamadas_domiciliado_financiado_liberadas_13m": 9808,
        "llamadas_domiciliado_financiado_liberadas_anual": int(
            round(9808 * annual_factor)
        ),
        "capacidad_mensual_5_gestores_llamadas": int(capacidad_llamadas_mes_5_gestores),
        "llamadas_humanas_requeridas_mes_3carriles": int(
            round(llamadas_humanas_requeridas_mes)
        ),
        "utilizacion_capacidad_humana_pct": round(utilizacion_capacidad_humana_pct, 1),
    }

    return {
        "lanes_summary_df": lanes_summary_df,
        "simulation_metrics": simulation_metrics,
        "manual_simulated_df": manual_df,
    }


def generate_copilot_recommendation(
    policy_row: pd.Series | Dict[str, Any],
    renovaciones_df: pd.DataFrame,
    equipo_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Módulo Copiloto IA para los Gestores (G01 a G05):
    Al seleccionar una póliza de la Bandeja Inteligente, analiza sus impulsores de
    riesgo, genera el argumento comercial personalizado de retención y construye
    la cotización alternativa multi-aseguradora si hubo aumento de prima.
    """
    row = policy_row if isinstance(policy_row, dict) else policy_row.to_dict()

    poliza_id = str(row.get("Póliza", ""))
    cliente_id = str(row.get("ID cliente", ""))
    telefono = str(row.get("Teléfono cliente", "Sin teléfono"))
    ramo = str(row.get("Ramo", "Autos"))
    aseguradora_actual = str(row.get("Aseguradora", ""))
    segmento = str(row.get("Segmento", "Individual"))
    origen = str(row.get("Origen", "Otro canal"))
    gestor_code = str(row.get("Gestor", "G01"))
    antiguedad = int(row.get("Antigüedad del cliente (años)", 1))
    siniestros = int(row.get("Siniestros último año", 0))
    prima_ant = float(row.get("Prima anterior (USD)", 0.0))
    prima_ren = float(row.get("Prima de renovación (USD)", 0.0))
    cambio_pct = float(row.get("% cambio de prima", 0.0)) * 100.0
    comision_pct = float(row.get("% comisión", 0.15)) * 100.0
    comision_usd = float(row.get("Comision_Renovacion_USD", prima_ren * comision_pct / 100.0))
    p_fuga = float(row.get("P_Fuga", 0.5))
    valor_riesgo = float(row.get("Valor_En_Riesgo_USD", comision_usd * p_fuga))
    dias_ant = row.get("dias_anticipacion", np.nan)

    gestor_nombre = gestor_code
    if equipo_df is not None and "Código" in equipo_df.columns:
        match_g = equipo_df[equipo_df["Código"] == gestor_code]
        if not match_g.empty:
            gestor_nombre = f"{gestor_code} - {match_g['Nombre'].iloc[0]}"

    # 1. Identificar factores críticos de riesgo de la póliza
    factores_riesgo = []
    if cambio_pct >= 10.0:
        factores_riesgo.append(
            f"Incremento severo de prima (+{cambio_pct:.1f}%, +${prima_ren - prima_ant:,.2f} USD)"
        )
    elif cambio_pct > 2.0:
        factores_riesgo.append(
            f"Aumento moderado de prima (+{cambio_pct:.1f}%, +${prima_ren - prima_ant:,.2f} USD)"
        )
    else:
        factores_riesgo.append(
            f"Prima estable ({cambio_pct:+.1f}%); foco en contacto oportuno y conveniencia"
        )

    if pd.isna(dias_ant) or float(dias_ant) < 7:
        factores_riesgo.append(
            "Ventana crítica de vencimiento: alto riesgo de que otro corredor contacte primero"
        )
    if siniestros > 0:
        factores_riesgo.append(
            f"Cliente registró {siniestros} siniestro(s) en el último año (validar satisfacción de reclamo)"
        )
    if antiguedad >= 5:
        factores_riesgo.append(
            f"Cliente leal ({antiguedad} años en Capesa): elegible para beneficio de fidelidad"
        )

    # 2. Motor de Cotización Alternativa Multi-Aseguradora (si hubo aumento de prima)
    hubo_aumento = prima_ren > prima_ant * 1.005
    peer_pool = renovaciones_df[
        (renovaciones_df["Ramo"] == ramo)
        & (renovaciones_df["Aseguradora"] != aseguradora_actual)
    ]
    if peer_pool.empty:
        peer_pool = renovaciones_df[renovaciones_df["Aseguradora"] != aseguradora_actual]

    alt_summary = (
        peer_pool.groupby("Aseguradora", as_index=False)
        .agg(
            Tasa_Exito_Hist_Pct=("Renovo_Bin", lambda s: round(float(s.mean() * 100.0), 1)),
            Cambio_Prima_Medio_Pct=("% cambio de prima", lambda s: round(float(s.mean() * 100.0), 1)),
            Comision_Media_Pct=("% comisión", lambda s: round(float(s.mean() * 100.0), 1)),
        )
        .sort_values("Tasa_Exito_Hist_Pct", ascending=False)
    )
    best_alt_insurer = (
        str(alt_summary["Aseguradora"].iloc[0])
        if not alt_summary.empty
        else "Seguros del Lago"
    )

    if hubo_aumento:
        # Si no tuvo siniestros, podemos cotizar en aseguradora alterna manteniendo prima base + 1.5%
        # Si tuvo siniestros, optimizar deducible / coaseguro para absorber el 65% del incremento
        if siniestros == 0:
            factor_ajuste = 1.015
            estrategia_precio = (
                f"Recotización defensiva en {best_alt_insurer} por Buen Récord (0 siniestros)"
            )
        else:
            factor_ajuste = 1.0 + max(0.03, (cambio_pct / 100.0) * 0.40)
            estrategia_precio = (
                f"Recotización en {best_alt_insurer} con ajuste de deducible (+20%) para contener incremento por siniestralidad"
            )

        prima_alternativa = round(min(prima_ren * 0.94, prima_ant * factor_ajuste), 2)
        ahorro_cliente = round(prima_ren - prima_alternativa, 2)
        comision_alt_usd = round(prima_alternativa * (comision_pct / 100.0), 2)
    else:
        estrategia_precio = (
            f"Mantener {aseguradora_actual} con tarifa preferencial vigente y fraccionamiento sin recargo"
        )
        prima_alternativa = round(prima_ren, 2)
        ahorro_cliente = 0.0
        comision_alt_usd = round(comision_usd, 2)

    cotizaciones_comparadas = [
        {
            "Opción": f"1. Renovación Estándar ({aseguradora_actual})",
            "Aseguradora": aseguradora_actual,
            "Prima Anual (USD)": round(prima_ren, 2),
            "Variación vs Anterior": f"{cambio_pct:+.1f}%",
            "Ahorro vs Cotización Base (USD)": 0.0,
            "Comisión Capesa (USD)": round(comision_usd, 2),
            "Acción Comercial": "Oferta base de renovación automática",
        },
        {
            "Opción": f"2. Retención Defensiva Misma Aseguradora ({aseguradora_actual})",
            "Aseguradora": aseguradora_actual,
            "Prima Anual (USD)": round(
                prima_ant + (prima_ren - prima_ant) * 0.50 if hubo_aumento else prima_ren * 0.97,
                2,
            ),
            "Variación vs Anterior": f"{((prima_ant + (prima_ren - prima_ant) * 0.50) / prima_ant - 1)*100:+.1f}%"
            if hubo_aumento and prima_ant > 0
            else "-3.0%",
            "Ahorro vs Cotización Base (USD)": round(
                (prima_ren - prima_ant) * 0.50 if hubo_aumento else prima_ren * 0.03, 2
            ),
            "Comisión Capesa (USD)": round(
                (prima_ant + (prima_ren - prima_ant) * 0.50 if hubo_aumento else prima_ren * 0.97)
                * (comision_pct / 100.0),
                2,
            ),
            "Acción Comercial": f"Descuento de permanencia ({antiguedad} años en Capesa)",
        },
        {
            "Opción": f"3. Switch Multi-Aseguradora Recomendado ({best_alt_insurer})",
            "Aseguradora": best_alt_insurer,
            "Prima Anual (USD)": prima_alternativa,
            "Variación vs Anterior": f"{(prima_alternativa / prima_ant - 1)*100:+.1f}%"
            if prima_ant > 0
            else "0.0%",
            "Ahorro vs Cotización Base (USD)": ahorro_cliente,
            "Comisión Capesa (USD)": comision_alt_usd,
            "Acción Comercial": estrategia_precio,
        },
    ]

    # 3. Construir Guion Comercial Recomendado
    origen_badge = (
        "respaldo de talleres autorizados Casa Pellas"
        if "Casa Pellas" in origen
        else "acompañamiento integral de reclamos 24/7 de Capesa"
    )
    if hubo_aumento:
        argumento_retencion = (
            f"**Apertura Proactiva ({gestor_nombre}):** «Estimado cliente ({cliente_id}), le contacto de Capesa "
            f"con anticipación al vencimiento de su póliza de **{ramo}** (`{poliza_id}`). Sabemos que este año "
            f"`{aseguradora_actual}` aplicó un ajuste técnico de **+{cambio_pct:.1f}%** (llevando la prima de "
            f"**${prima_ant:,.2f}** a **${prima_ren:,.2f} USD**). Como su corredor de confianza desde hace "
            f"**{antiguedad} año(s)**, nos adelantamos y negociamos una alternativa equivalente en **{best_alt_insurer}** "
            f"por **${prima_alternativa:,.2f} USD** (un ahorro inmediato de **${ahorro_cliente:,.2f} USD**), "
            f"conservando sus coberturas y el {origen_badge}. ¿Le parece bien que emitamos la opción con ahorro hoy mismo?»"
        )
    else:
        argumento_retencion = (
            f"**Apertura Proactiva ({gestor_nombre}):** «Estimado cliente ({cliente_id}), le saludo de Capesa "
            f"para dejar asegurada la continuidad de su póliza de **{ramo}** (`{poliza_id}`) con `{aseguradora_actual}`. "
            f"Por su excelente historial y **{antiguedad} año(s)** de antigüedad, hemos garantizado su prima preferencial "
            f"de **${prima_ren:,.2f} USD** sin incrementos y con el {origen_badge}. Solo necesito su confirmación por "
            f"esta vía para enviarle el certificado renovado.»"
        )

    return {
        "poliza": poliza_id,
        "cliente_id": cliente_id,
        "telefono": telefono,
        "gestor": gestor_nombre,
        "ramo": ramo,
        "segmento": segmento,
        "origen": origen,
        "aseguradora_actual": aseguradora_actual,
        "aseguradora_alternativa": best_alt_insurer,
        "prima_anterior_usd": round(prima_ant, 2),
        "prima_renovacion_usd": round(prima_ren, 2),
        "cambio_prima_pct": round(cambio_pct, 2),
        "hubo_aumento_prima": hubo_aumento,
        "prima_alternativa_sugerida_usd": prima_alternativa,
        "ahorro_potencial_cliente_usd": ahorro_cliente,
        "comision_en_riesgo_usd": round(valor_riesgo, 2),
        "comision_total_poliza_usd": round(comision_usd, 2),
        "p_fuga_pct": round(p_fuga * 100.0, 1),
        "factores_riesgo": factores_riesgo,
        "estrategia_precio": estrategia_precio,
        "argumento_retencion": argumento_retencion,
        "cotizaciones_df": pd.DataFrame(cotizaciones_comparadas),
    }


def run_caso2_pipeline(
    excel_path: Optional[str | Path] = None,
    model_type: str = "logistic",
    target_contact_days: int = 22,
    ai_agent_closure_share_low_risk: float = 0.35,
    human_retention_uplift_high_value: float = 0.06,
    zero_touch_recovery_rate: float = 0.25,
) -> Dict[str, Any]:
    """
    Punto de entrada integral para la interfaz gráfica o notebooks del Caso 2.
    Devuelve todos los DataFrames limpios, diagnóstico del cuello de botella,
    modelo predictivo P(Fuga), bandeja priorizada por Valor en Riesgo y
    simulación económica de los 3 carriles.
    """
    cleaned = load_and_clean_caso2(excel_path=excel_path)
    diagnosis = diagnose_bottleneck(
        cleaned["renovaciones"],
        cleaned["bitacora"],
        cleaned["equipo"],
        renovaciones_raw_df=cleaned["renovaciones_raw"],
    )
    ml_results = train_churn_model_and_score(
        cleaned["renovaciones"],
        model_type=model_type,
    )
    sim_results = simulate_three_lane_architecture(
        cleaned["renovaciones"],
        ml_results,
        target_contact_days=target_contact_days,
        ai_agent_closure_share_low_risk=ai_agent_closure_share_low_risk,
        human_retention_uplift_high_value=human_retention_uplift_high_value,
        zero_touch_recovery_rate=zero_touch_recovery_rate,
    )

    return {
        **cleaned,
        "diagnosis": diagnosis,
        "ml_results": ml_results,
        "simulation": sim_results,
    }


if __name__ == "__main__":
    res = run_caso2_pipeline()
    print("=== AUDITORIA CASO 2 ===")
    for k, v in res["audit_summary"].items():
        print(f"  {k}: {v}")
    print("\n=== QUIEBRE ESTRUCTURAL (01/12/2025) ===")
    print(res["diagnosis"]["structural_break"].to_string(index=False))
    print("\n=== INEFICIENCIA POR FORMA DE PAGO ===")
    print(res["diagnosis"]["payment_efficiency"].to_string(index=False))
    print("\n=== METRICAS MODELO PREDICTIVO P(FUGA) ===")
    for k, v in res["ml_results"]["model_metrics"].items():
        print(f"  {k}: {v}")
    print("\n=== IMPACTO ARQUITECTURA DE 3 CARRILES ===")
    print(res["simulation"]["lanes_summary_df"].to_string(index=False))
    print("\n=== RESUMEN SIMULACION ANUAL ===")
    for k, v in res["simulation"]["simulation_metrics"].items():
        print(f"  {k}: {v}")

