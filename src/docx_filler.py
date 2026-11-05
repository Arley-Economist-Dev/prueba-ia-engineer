"""
Generador Automatizado del Informe Ejecutivo en Word (python-docx)
Lee 'Prueba Ingeniero IA.docx', inyecta el análisis exhaustivo de Caso 1, Caso 2
y la Sección Transversal de Metodología de IA utilizando los resultados exactos de
src/caso1_engine.py y src/caso2_engine.py, y guarda el archivo resultante como:
'Prueba Ingeniero IA - Entregable Final.docx'.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Inches, Pt, RGBColor

from src.caso1_engine import run_caso1_pipeline
from src.caso2_engine import run_caso2_pipeline

RENDER_URL = "https://casa-pellas-ia-suite.onrender.com/"
GITHUB_URL = "https://github.com/Arley-Economist-Dev/prueba-ia-engineer"


# ---------------------------------------------------------------------------
# Utilidades de Manipulación XML para Insertar Bloques Ordenados en python-docx
# ---------------------------------------------------------------------------

class SequentialComposer:
    """
    Permite insertar párrafos y tablas secuencialmente justo después de un
    párrafo ancla dentro de un documento Word existente, conservando la
    estructura posterior del documento.
    """

    def __init__(self, doc: Document, anchor_paragraph):
        self.doc = doc
        self.cursor_elm = anchor_paragraph._p

    def add_heading(self, text: str, level: int = 3):
        p = self.doc.add_paragraph()
        style_name = f"Heading {level}" if f"Heading {level}" in self.doc.styles else "Heading 2"
        p.style = style_name
        run = p.add_run(text)
        if level == 3:
            run.font.size = Pt(12)
            run.font.bold = True
            run.font.color.rgb = RGBColor(15, 23, 42)
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        self.cursor_elm.addnext(p._p)
        self.cursor_elm = p._p
        return p

    def add_paragraph(
        self,
        text: str = "",
        bold_prefix: Optional[str] = None,
        italic: bool = False,
        space_after: int = 5,
    ):
        p = self.doc.add_paragraph()
        p.style = "Normal"
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15

        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.bold = True
            r_pre.font.size = Pt(10)
            r_pre.font.color.rgb = RGBColor(15, 23, 42)

        if text:
            r_txt = p.add_run(text)
            r_txt.italic = italic
            r_txt.font.size = Pt(10)
            r_txt.font.color.rgb = RGBColor(30, 41, 59)

        self.cursor_elm.addnext(p._p)
        self.cursor_elm = p._p
        return p

    def add_callout_box(self, title: str, lines: List[str], fill_hex: str = "F1F5F9"):
        """Crea un cuadro destacado de 1x1 con borde izquierdo corporativo."""
        tbl = self.doc.add_table(rows=1, cols=1)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = tbl.cell(0, 0)
        _set_cell_background(cell, fill_hex)
        _set_callout_borders(cell, border_color="1D4ED8")
        _set_cell_margins(cell, top=120, bottom=120, left=180, right=160)

        p0 = cell.paragraphs[0]
        p0.paragraph_format.space_before = Pt(2)
        p0.paragraph_format.space_after = Pt(3)
        r_title = p0.add_run(title)
        r_title.bold = True
        r_title.font.size = Pt(10)
        r_title.font.color.rgb = RGBColor(15, 23, 42)

        for line in lines:
            p = cell.add_paragraph()
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(line)
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(30, 41, 59)

        self.cursor_elm.addnext(tbl._tbl)
        self.cursor_elm = tbl._tbl
        self.add_paragraph("", space_after=3)
        return tbl

    def add_bullet(self, bold_prefix: str, text: str):
        p = self.doc.add_paragraph()
        p.style = "List Bullet" if "List Bullet" in self.doc.styles else "Normal"
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.12

        if bold_prefix:
            r_b = p.add_run(bold_prefix)
            r_b.bold = True
            r_b.font.size = Pt(10)
            r_b.font.color.rgb = RGBColor(15, 23, 42)

        r_t = p.add_run(text)
        r_t.font.size = Pt(10)
        r_t.font.color.rgb = RGBColor(30, 41, 59)

        self.cursor_elm.addnext(p._p)
        self.cursor_elm = p._p
        return p

    def add_table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[Any]],
        col_alignments: Optional[Sequence[str]] = None,
        highlight_last_row: bool = False,
        header_bg: str = "0F172A",
    ):
        tbl = self.doc.add_table(rows=len(rows) + 1, cols=len(headers))
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(tbl)

        # Fila de encabezados
        hdr_cells = tbl.rows[0].cells
        for j, h_text in enumerate(headers):
            c = hdr_cells[j]
            _set_cell_background(c, header_bg)
            _set_cell_margins(c, top=70, bottom=70, left=80, right=80)
            c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            run = p.add_run(str(h_text))
            run.bold = True
            run.font.size = Pt(8.5)
            run.font.color.rgb = RGBColor(255, 255, 255)

        # Filas de datos
        for i, row_vals in enumerate(rows):
            row_cells = tbl.rows[i + 1].cells
            is_last = highlight_last_row and (i == len(rows) - 1)
            bg_color = "E2E8F0" if is_last else ("F8FAFC" if i % 2 == 1 else "FFFFFF")

            for j, val in enumerate(row_vals):
                c = row_cells[j]
                _set_cell_background(c, bg_color)
                _set_cell_margins(c, top=55, bottom=55, left=75, right=75)
                c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
                p = c.paragraphs[0]
                p.paragraph_format.space_before = Pt(1)
                p.paragraph_format.space_after = Pt(1)

                align = "left"
                if col_alignments and j < len(col_alignments):
                    align = col_alignments[j]
                if align == "right":
                    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                elif align == "center":
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT

                run = p.add_run(str(val))
                run.font.size = Pt(8.5)
                run.bold = is_last or (j == 0)
                run.font.color.rgb = RGBColor(15, 23, 42)

        self.cursor_elm.addnext(tbl._tbl)
        self.cursor_elm = tbl._tbl
        self.add_paragraph("", space_after=4)
        return tbl


def _set_cell_background(cell, fill_hex: str):
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shd)


def _set_cell_margins(cell, top=60, bottom=60, left=90, right=90):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m_name, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{m_name}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def _set_callout_borders(cell, border_color="1D4ED8"):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{border_color}"/>'
        f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        f'<w:right w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        f"</w:tcBorders>"
    )
    tcPr.append(tcBorders)


def _set_table_borders(table):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'<w:top w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>'
        f'<w:left w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>'
        f'<w:bottom w:val="single" w:sz="8" w:space="0" w:color="0F172A"/>'
        f'<w:right w:val="single" w:sz="6" w:space="0" w:color="94A3B8"/>'
        f'<w:insideH w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        f'<w:insideV w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        f"</w:tblBorders>"
    )
    tblPr.append(borders)


# ---------------------------------------------------------------------------
# Construcción de la Sección «Tu respuesta» — CASO 1 (Vehículos Nuevos Toyota)
# ---------------------------------------------------------------------------

def populate_caso1_response(composer: SequentialComposer, res1: Dict[str, Any]):
    order_df = res1["order_recommendations"]
    totals = res1["order_totals"]
    audit = res1["audit_summary"]
    version_sum = res1["version_mix_summary"]

    composer.add_callout_box(
        "🔗 ACCESO DIRECTO A LA APLICACIÓN WEB EN PRODUCCIÓN Y REPOSITORIO (CASO 1)",
        [
            f"• Aplicación Web Interactiva S&OP en Producción (Render): {RENDER_URL}",
            f"• Repositorio Oficial de Código y Pipelines (GitHub): {GITHUB_URL}",
            "• Nota de Carga en Render (Cold Start): Al abrir el enlace web por primera vez tras inactividad, por favor espere ~30 a 50 segundos mientras el contenedor en la nube despierta y pre-carga los modelos en memoria RAM. Una vez activo, todos los simuladores responden en <25 ms.",
            "• Arquitectura: FastAPI + Uvicorn (main.py, src/api.py) | Motor S&OP: src/caso1_engine.py | Suite QA: test_pipeline.py",
            "• Libro Excel Consolidado de Soporte: outputs/Pedido_Recomendado_Octubre_2026.xlsx (descargable también desde la aplicación web).",
        ],
        fill_hex="EFF6FF",
    )

    # 1.1 Recomendación Definitiva de Pedidos
    composer.add_heading(
        "1.1 Recomendación Ejecutiva de Pedido a Fábrica — Ventana Octubre 2026",
        level=3,
    )
    composer.add_paragraph(
        bold_prefix="A la Gerencia Comercial Toyota (Grupo Casa Pellas): ",
        text=(
            f"Con base en el análisis integral de los 36 meses de operación comercial (octubre 2023 – septiembre 2026), "
            f"el inventario en patio al corte del 30/09/2026 ({totals['total_inv_30sep']} unidades), el pipeline en tránsito "
            f"confirmado ({totals['total_transito_oct_ene']} unidades con arribo entre octubre 2026 y enero 2027) y la demanda "
            f"latente no capturada en el CRM, se recomienda confirmar para la ventana del 30 de octubre de 2026 un pedido "
            f"total de {totals['total_unidades_pedidas']} unidades distribuidas en 10 modelos (con 0 unidades en RAV4 por "
            f"liquidación controlada de cambio de generación). Esta decisión compromete un capital de compra de "
            f"${totals['total_capital_comprometido_usd']:,.2f} USD, proyecta ingresos por ${totals['total_ingreso_esperado_usd']:,.2f} USD "
            f"y genera un margen bruto esperado de ${totals['total_margen_bruto_esperado_usd']:,.2f} USD "
            f"({totals['margen_bruto_ponderado_pct']*100:.2f}% sobre ingresos), con un costo financiero mensual de plan piso "
            f"(0.9%) de ${totals['total_costo_plan_piso_mensual_usd']:,.2f} USD/mes."
        ),
    )

    headers_c1 = [
        "Modelo Oficial",
        "Regla Lote\n(Mín/Múlt)",
        "Inv.\n30-Sep",
        "Tránsito\nOct-Ene",
        "Demanda\nMensual",
        "Stock Proy.\n31-Ene-27",
        "Nec. Neta\nFeb-Abr+SS",
        "Pedido Final\nOct-26 (Uds)",
        "Capital Compra\n(USD)",
        "Margen Bruto\nProy. (USD)",
        "Plan Piso\n0.9%/mes (USD)",
        "Cobertura\n30-Abr (M)",
    ]
    rows_c1 = []
    for _, r in order_df.iterrows():
        rows_c1.append(
            [
                r["Modelo"],
                r["Lote_Min_Mult"],
                f"{int(r['Inv_30Sep']):,}",
                f"{int(r['Transito_Oct26_Ene27']):,}",
                f"{r['Demanda_Mensual_Planificada']:.2f}",
                f"{r['Inv_Proyectado_31Ene27']:.1f}",
                f"{r['Necesidad_Neta_Feb_Abr']:.1f}",
                f"{int(r['Pedido_Sugerido_Oct26']):,}",
                f"${r['Capital_Comprometido_USD']:,.0f}",
                f"${r['Margen_Bruto_Esperado_USD']:,.0f}",
                f"${r['Costo_Plan_Piso_Mensual_USD']:,.2f}",
                f"{r['Meses_Cobertura_30Abr27']:.2f} m",
            ]
        )
    rows_c1.append(
        [
            "TOTAL CONSOLIDADO",
            "100% Cumplido",
            f"{totals['total_inv_30sep']:,}",
            f"{totals['total_transito_oct_ene']:,}",
            f"{order_df['Demanda_Mensual_Planificada'].sum():.2f}",
            f"{order_df['Inv_Proyectado_31Ene27'].sum():.1f}",
            f"{order_df['Necesidad_Neta_Feb_Abr'].sum():.1f}",
            f"{totals['total_unidades_pedidas']:,}",
            f"${totals['total_capital_comprometido_usd']:,.0f}",
            f"${totals['total_margen_bruto_esperado_usd']:,.0f}",
            f"${totals['total_costo_plan_piso_mensual_usd']:,.2f}",
            "1.12 m",
        ]
    )
    align_c1 = [
        "left",
        "center",
        "right",
        "right",
        "right",
        "right",
        "right",
        "right",
        "right",
        "right",
        "right",
        "right",
    ]
    composer.add_table(
        headers_c1, rows_c1, col_alignments=align_c1, highlight_last_row=True
    )

    # 1.2 Sustento Cuantitativo
    composer.add_heading(
        "1.2 Sustento Cuantitativo: Auditoría de Datos, Demanda Insatisfecha y Horizonte Operativo",
        level=3,
    )
    composer.add_bullet(
        "1. Limpieza de Catálogo y Neteo de Notas de Crédito: ",
        (
            f"La auditoría técnica de las bases reveló {audit['modelos_originales_sucios']} variantes tipográficas de modelos en Ventas "
            f"(y 63 en Leads, incluyendo espacios dobles, minúsculas y prefijos como 'Toyota ') y {audit['sucursales_originales_sucias']} "
            f"variantes de sucursales (como 'Mga Sur', 'MANAGUA CENTRAL', 'Leon'). Todas se normalizaron hacia los 11 modelos oficiales "
            f"y las 7 sucursales. Asimismo, se identificaron y netearon {audit['notas_credito_filas']} Notas de Crédito (facturas con prefijo "
            f"'NC-' y Unidades = -1: 5 en Hilux, 2 en RAV4, 1 en Corolla Cross y 1 en Yaris Cross), ajustando el volumen facturado de "
            f"{audit['unidades_brutas_facturadas']:,} unidades brutas a {audit['unidades_netas_reales']:,} unidades netas reales. "
            f"Adicionalmente, se aislaron dos ventas institucionales extraordinarias gestionadas fuera de ventana trimestral "
            f"(FAC-883958 por 60 Hilux y FAC-884287 por 45 Yaris = {audit['unidades_flota_especial']} unidades) para evitar sobreestimar "
            f"la demanda orgánica mensual de patio ({audit['unidades_netas_regulares']:,} unidades regulares)."
        ),
    )
    composer.add_bullet(
        "2. Cuantificación de la Demanda Insatisfecha en el CRM: ",
        (
            "Al analizar las 12,132 oportunidades del CRM (4,532 ganadas y 7,600 perdidas), se agruparon los 8 motivos de pérdida "
            "atribuibles directamente a desabastecimiento ('Sin disponibilidad / sin inventario', 'Sin disponibilidad', 'Sin inventario', "
            "'No hay unidades disponibles', 'Sin stock', 'Sin disponibilidad de versión/color', 'Color no disponible' y 'Versión no disponible'). "
            "Estos motivos explican 535 oportunidades perdidas equivalentes a 646 unidades no capturadas en 36 meses (315 unidades tan solo en "
            "los últimos 12 meses). La pérdida de ventas por falta de producto se concentra en Corolla Cross (74 uds perdidas en 12M y 0 uds hoy "
            "en patio), Hilux (67 uds en 12M), Yaris Cross (43 uds en 12M y 0 uds en patio), Rush (34 uds en 12M y 0 uds en patio), "
            "Corolla (23 uds), Yaris (23 uds) y Hiace (24 uds). El modelo incorpora un factor prudente del 50% de captura sobre esta demanda "
            "latente (para descontar cotizaciones duplicadas de un mismo cliente entre sucursales) y pondera en 65% el ritmo de los últimos 12 meses "
            "y 35% el promedio de 36 meses."
        ),
    )
    composer.add_bullet(
        "3. Dinámica del Lead Time de 4 Meses y Ventana de Cobertura Real (Febrero – Abril 2027): ",
        (
            "Conforme al Comunicado del 12/02/2024, el lead time desde el cierre del pedido (30 de octubre de 2026) hasta la llegada al patio en "
            "Managua es de 4 meses (arribo a inicios de febrero de 2027). En consecuencia, el pedido de octubre NO puede abastecer la demanda de "
            "octubre 2026 a enero 2027; dicho cuatrimestre se cubre estrictamente con las 272 unidades en patio al 30/09/2026 más las 370 unidades "
            "en tránsito (182 líneas de pedido: 23 uds que llegan en oct-26, 290 en nov-26, 42 en dic-26 y 15 en ene-27). Proyectando el balance "
            "al 31 de enero de 2027 [Inv_31Ene = max(0, Inv_30Sep + Tránsito_Oct_Ene - Demanda_4M)], el pedido de octubre se dimensiona para "
            "cubrir los 3 meses del ciclo febrero–abril 2027 más 1.0 mes (30 días) de stock de seguridad al cierre del 30 de abril de 2027, justo "
            "antes del arribo del pedido de la ventana de enero 2027 en mayo 2027."
        ),
    )

    # Mezcla recomendada por versión y color (resumen de las versiones líderes)
    composer.add_paragraph(
        bold_prefix="Mezcla Óptima Sugerida por Versión y Color: ",
        text=(
            "Dado que fábrica exige múltiplos por modelo pero otorga libertad en la combinación interna de versiones y colores "
            "(Comunicado 03/06/2025), se aplicó el algoritmo de asignación entera de Restos Mayores (Hamilton) ponderando las ventas "
            "netas históricas con los quiebres de versión del CRM. A continuación se detalla la asignación por versión para los 426 vehículos:"
        ),
    )

    headers_ver = [
        "Modelo",
        "Versión Recomendada",
        "Ventas Hist. (Uds)",
        "Stockout CRM (Uds)",
        "Peso Óptimo (%)",
        "Unidades a Pedir (Oct-26)",
        "Colores Principales Sugeridos",
    ]
    rows_ver = []
    mix_full = res1["version_color_mix"]
    for _, vr in version_sum.iterrows():
        m_name = vr["Modelo"]
        v_name = vr["Versión"]
        sub_c = mix_full[
            (mix_full["Modelo"] == m_name) & (mix_full["Versión"] == v_name)
        ].sort_values(["Unidades_Sugeridas", "Ventas_Hist_Uds"], ascending=False)
        if int(vr["Unidades_Sugeridas"]) > 0:
            top_colors = ", ".join(
                f"{r_c['Color']} ({int(r_c['Unidades_Sugeridas'])})"
                for _, r_c in sub_c[sub_c["Unidades_Sugeridas"] > 0].head(3).iterrows()
            )
        else:
            top_colors = "En liquidación controlada (0 uds)"
        rows_ver.append(
            [
                m_name,
                v_name,
                f"{int(vr['Ventas_Hist_Uds']):,}",
                f"{int(vr['Leads_Stockout_Uds']):,}",
                f"{vr['Share_Optimo_Pct']:.1f}%",
                f"{int(vr['Unidades_Sugeridas']):,}",
                top_colors,
            ]
        )
    composer.add_table(
        headers_ver,
        rows_ver,
        col_alignments=["left", "left", "right", "right", "right", "right", "left"],
    )

    # 1.3 Decisión Estratégica RAV4
    composer.add_heading(
        "1.3 Decisión Estratégica Crítica: Liquidación Controlada de RAV4 (Comunicado 15/09/2026)",
        level=3,
    )
    composer.add_paragraph(
        bold_prefix="Justificación Técnica y Financiera (Pedido Octubre 2026 = 0 Unidades): ",
        text=(
            "El Comunicado de Fábrica del 15/09/2026 informa que la nueva generación de RAV4 (versiones híbrida e híbrida enchufable) "
            "se solicitará en la ventana de enero 2027 y arribará a Nicaragua en mayo 2027, advirtiendo expresamente que las unidades "
            "remanentes de la generación actual no tendrán apoyo ni subsidio de fábrica para su liquidación. Al analizar la posición "
            "física de Casa Pellas al 30/09/2026, existen 9 unidades en patio más 47 unidades en tránsito (compuestas por las 44 unidades "
            "del pedido PF-41141 confirmado el 20/07/2026 con llegada entre noviembre y diciembre de 2026, más 3 unidades rezagadas del "
            "pedido PF-41130 con llegada en octubre de 2026). Esto totaliza 56 unidades disponibles de la generación saliente para cubrir "
            "los 7 meses comprendidos entre octubre 2026 y abril 2027."
        ),
    )
    composer.add_paragraph(
        text=(
            "Con un ritmo requerido de evacuación de exactamente 8.0 unidades/mes (frente a la venta promedio histórica de 7.64 uds/mes en "
            "36M y 9.02 uds/mes de demanda planificada reciente), el inventario actual + tránsito basta para abastecer toda la ventana previa "
            "al cambio de línea y converger a un stock remanente cercano a 0 unidades al 30 de abril de 2027. Si no se aplicara esta restricción "
            "y se pidieran 8 o 12 unidades adicionales en octubre (que llegarían en febrero 2027), Casa Pellas llegaría a mayo 2027 con un "
            "sobrestock de $307,360 a $461,040 USD en costo de unidades obsoletas, viéndose forzada a otorgar descuentos de liquidación del "
            "7% al 10% sobre precio que eliminarían por completo el margen bruto del modelo (10.0%). La estrategia óptima es pedir 0 unidades "
            "en octubre 2026, ejecutar un plan comercial de evacuación de las 56 unidades entre octubre y abril, y reservar el capital para "
            "solicitar con fuerza la Nueva Generación RAV4 en la ventana de enero 2027."
        ),
    )

    # 1.4 Matriz de Riesgos Financieros
    composer.add_heading(
        "1.4 Matriz de Riesgos Financieros: Costo de Plan Piso (0.9%) y Castigos por Antigüedad",
        level=3,
    )
    composer.add_paragraph(
        text=(
            "Cada unidad en inventario devenga un costo financiero de plan piso del 0.9% mensual sobre su costo unitario y está sujeta a la "
            "política comercial de descuentos por antigüedad sobre el precio de venta: >180 días (4%), >270 días (7%) y >365 días (10%). "
            "Dado que los márgenes brutos oscilan entre el 7.0% (Yaris y Raize) y el 13.0% (Hilux), retener una unidad más de 180 días sumando "
            "6 meses de plan piso (~4.8% a 5.0% del precio) más un descuento del 4% destruye la totalidad de la utilidad unitaria:"
        ),
    )

    headers_risk = [
        "Riesgo Identificado",
        "Modelos Expuestos",
        "Impacto Financiero / Cuantificación",
        "Mitigación Incorporada en el Motor S&OP",
    ]
    rows_risk = [
        [
            "1. Erosión de margen por antigüedad (>180 / >270 / >365 días)",
            "Yaris (7%), Raize (7%), Rush (8%), Corolla (9%)",
            "Un descuento de 4% (>180d) + 6 meses de plan piso (0.9%/mes s/costo = ~5.0% s/precio) consume 9.0% del precio, generando pérdida neta en modelos de margen <=9%.",
            "Cobertura acotada a 3M + 1M de stock de seguridad; rotación objetivo <60 días en patio y alerta temprana a los 120 días.",
        ],
        [
            "2. Obsolescencia tecnológica por cambio de generación",
            "RAV4 (56 uds entre patio y tránsito)",
            "Riesgo sobre $2.15M USD en inventario + tránsito actual (56 x $38,420). Sin bloqueo en Oct-26, quedarían 8–12 uds sin subsidio en mayo 2027.",
            "Bloqueo automático de pedido en Oct-26 (0 uds) y meta comercial de 8.0 uds/mes entre Oct-26 y Abr-27 para llegar con stock 0 a mayo 2027.",
        ],
        [
            "3. Quiebre de stock durante el Lead Time (Oct 2026 – Ene 2027)",
            "Corolla Cross (0 patio, 30 tráns.), Yaris Cross (0 patio, 24 tráns.), Rush (0 patio, 12 tráns.)",
            "El pedido de julio 2026 fue insuficiente frente a la demanda de 4 meses, proyectando un déficit pre-arribo de ~58 uds en Corolla Cross y ~34 uds en Yaris Cross antes de febrero 2027.",
            "Pre-venta con reserva sobre unidades en tránsito que arriban en noviembre 2026 y pedido robusto en Oct-26 (90 Corolla Cross, 60 Yaris Cross, 40 Rush) para normalizar patio en febrero 2027.",
        ],
        [
            "4. Costo Financiero de Plan Piso (0.9% mensual)",
            "Cartera total solicitada (426 uds = $13.34M USD)",
            "El lote completo genera un cargo financiero máximo de $120,063 USD el primer mes de arribo, descendiendo a ~$60,031 USD/mes promedio conforme rota el inventario.",
            "Ajuste exacto a múltiplos de contenedor y priorización de versiones/colores de alta velocidad de salida para minimizar los días de estancia en patio.",
        ],
    ]
    composer.add_table(
        headers_risk,
        rows_risk,
        col_alignments=["left", "left", "left", "left"],
    )

    # 1.5 Supuestos explícitos, arquitectura IA y mejora continua
    composer.add_heading(
        "1.5 Supuestos Explícitos, Funcionamiento del Sistema IA y Mejora Continua",
        level=3,
    )
    composer.add_bullet(
        "Supuestos Explícitos Adoptados: ",
        (
            "(a) Fábrica confirma el 100% del pedido de octubre 2026 cumpliendo mínimos y múltiplos (Comunicado 20/08/2026); "
            "(b) Los pedidos en tránsito arriban en el mes de su fecha estimada de llegada sin siniestros marítimos; "
            "(c) El 50% de las oportunidades perdidas por falta de inventario en el CRM representa demanda neta incremental genuina "
            "(descontando cotizaciones cruzadas del mismo cliente); (d) Las licitaciones institucionales mayores a 15 unidades se "
            "gestionan como pedidos especiales fuera de ventana trimestral (Comunicado 12/02/2024)."
        ),
    )
    composer.add_bullet(
        "Información Adicional que se Solicitaría para Próximos Ciclos: ",
        (
            "(1) Reservas activas con anticipo de clientes sobre las 370 unidades en tránsito para separar tránsito libre vs tránsito ya comprometido; "
            "(2) Pipeline de licitaciones de Flota / Estado previstas para 2027; (3) Costos de transferencia inter-sucursal (Managua hacia León, "
            "Chinandega, Estelí, Matagalpa y Juigalpa) para optimizar la asignación física por patio."
        ),
    )
    composer.add_bullet(
        "Cómo Funciona el Prototipo S&OP con IA y Cómo se Mide: ",
        (
            "El motor matemático src/caso1_engine.py, expuesto mediante la API asíncrona en FastAPI (main.py y src/api.py) y la Single Page Application (SPA) "
            "interactiva con ApexCharts y Plotly.js, automatizan en cada trimestre el flujo completo: ingesta del Excel bruto -> "
            "normalización automática de texto -> neteo de Notas de Crédito -> estimación de demanda híbrida (Ventas + CRM Stockout) -> proyección de "
            "balance a 4 meses -> optimización entera por lotes -> desglose de versiones/colores y exportación directa a Excel. El desempeño del sistema se "
            "mide con 4 KPIs trimestrales: (1) Tasa de Ventas Perdidas por Desabastecimiento en CRM (meta: reducir del 4.4% actual a <1.5% de los leads); "
            "(2) Días Promedio de Rotación en Patio (meta: <65 días, con 0 unidades >180 días); (3) Precisión del Pronóstico de Demanda (WMAPE <12%); y "
            "(4) ROIC Comercial Neto después de Plan Piso."
        ),
    )


# ---------------------------------------------------------------------------
# Construcción de la Sección «Tu respuesta» — CASO 2 (Renovaciones Capesa)
# ---------------------------------------------------------------------------

def populate_caso2_response(composer: SequentialComposer, res2: Dict[str, Any]):
    audit = res2["audit_summary"]
    diag = res2["diagnosis"]
    ml = res2["ml_results"]
    sim = res2["simulation"]
    kf = diag["key_findings"]
    sb_df = diag["structural_break"]
    pay_df = diag["payment_efficiency"]
    lanes_df = sim["lanes_summary_df"]
    sim_m = sim["simulation_metrics"]

    composer.add_callout_box(
        "🔗 ACCESO DIRECTO AL ORQUESTADOR DE RENOVACIONES Y COPILOTO IA EN PRODUCCIÓN (CASO 2)",
        [
            f"• Aplicación Web Interactiva y Simulador ROI en Producción (Render): {RENDER_URL} (Pestaña: Caso 2 · Renovaciones Capesa)",
            f"• Repositorio Oficial de Código y Modelos Predictivos (GitHub): {GITHUB_URL}",
            "• Nota de Carga en Render (Cold Start): Al ingresar por primera vez tras un periodo de inactividad, aguarde ~30 a 50 segundos mientras el servidor en Render inicia y entrena/carga en memoria el modelo predictivo P(Fuga). Posteriormente, los filtros, el simulador ROI y el Copiloto IA operan en tiempo real (<25 ms).",
            "• Arquitectura: FastAPI + Uvicorn (main.py, src/api.py) | Motor ML (Scikit-Learn): src/caso2_engine.py | Suite QA: test_pipeline.py",
            "• Bandeja Priorizada Exportada: outputs/Bandeja_Priorizada_Capesa.xlsx (descargable también en vivo desde la plataforma).",
        ],
        fill_hex="F0FDF4",
    )

    # 2.1 Diagnóstico Operativo
    composer.add_heading(
        "2.1 Diagnóstico Cuantitativo del Cuello de Botella Operativo (Dirigido al Comité de Capesa)",
        level=3,
    )
    composer.add_paragraph(
        bold_prefix="Al Comité Directivo de Capesa (Gerente General, Gerente Comercial y Jefe de Renovaciones): ",
        text=(
            f"La auditoría integral de los últimos 13 meses de operación (septiembre 2025 – septiembre 2026) —tras depurar exactamente "
            f"{audit['polizas_duplicadas_eliminadas']} registros duplicados de las {audit['filas_originales']:,} filas originales para consolidar "
            f"{audit['polizas_unicas_limpias']:,} pólizas únicas y {kf['llamadas_totales_bitacora']:,} llamadas en bitácora— demuestra que la "
            f"caída en la retención de Capesa (tasa global actual de {audit['tasa_renovacion_global_pct']:.2f}%, con ${audit['comision_perdida_13m_usd']:,.2f} USD "
            f"en comisiones no renovadas durante los 13 meses) NO obedece a un deterioro del producto asegurador, sino a un cuello de botella "
            f"estructural de capacidad y a una asignación ineficiente del esfuerzo telefónico humano."
        ),
    )

    composer.add_bullet(
        "Hallazgo 1 — El Quiebre Estructural del 01/12/2025 tras la Salida de G06 y G07: ",
        (
            "Al cruzar la base de Renovaciones con la hoja Equipo, se evidencia que entre septiembre y noviembre de 2025 el área operó con "
            "dotación completa de 7 gestores (G01 a G07), manejando 291.9 pólizas/gestor/mes, logrando una mediana de anticipación de 13.0 días "
            "y una tasa de renovación global del 62.00% (54.98% en pago Manual). Tras el retiro de los gestores G06 (Roberto Carlos Membreño) y "
            "G07 (Silvia Patricia Obando) el 30/11/2025 sin reemplazo, las carteras se redistribuyeron entre solo 5 gestores (G01 a G05). "
            "Esto elevó la carga individual en +30.7% (a 381.4 pólizas/gestor/mes), colapsó la mediana de anticipación a 3.0 días (mediana global "
            "de 4.0 días en los 13 meses vs la meta de 20 días; 84.59% contactadas fuera de plazo, 577 contactadas post-vencimiento en la base "
            "bruta [574 en la base única] y 151 sin ningún contacto), y derrumbó la tasa de renovación global en -11.38 puntos porcentuales "
            "(de 62.00% a 50.62%), mientras que la renovación de pólizas Manuales cayó en -13.84 puntos porcentuales (de 54.98% a 41.14%)."
        ),
    )

    headers_sb = [
        "Periodo Operativo",
        "Gestores\nActivos",
        "Pólizas\nÚnicas",
        "Cartera Mensual\npor Gestor",
        "Mediana Días\nAnticipación",
        "% En Meta\n(>=20 días)",
        "Renovación\nGlobal (%)",
        "Renovación\nManual (%)",
        "Comisión Perdida\nMensual (USD)",
    ]
    rows_sb = []
    for _, r in sb_df.iterrows():
        rows_sb.append(
            [
                r["Periodo_Operativo"],
                f"{int(r['Gestores_Activos'])}",
                f"{int(r['Polizas_Totales']):,}",
                f"{r['Cartera_Mensual_Por_Gestor']:.1f} pól/mes",
                f"{r['Mediana_Dias_Anticipacion']:.1f} días",
                f"{r['Pct_Contactado_En_Meta_20d']:.2f}%",
                f"{r['Tasa_Renovacion_Global_Pct']:.2f}%",
                f"{r['Tasa_Renovacion_Manual_Pct']:.2f}%",
                f"${r['Comision_Perdida_Mensual_USD']:,.0f}/mes",
            ]
        )
    rows_sb.append(
        [
            "Impacto del Quiebre (Dic-25 vs Sep-Nov 25)",
            "-2 gestores (-28.6%)",
            "25,200 total",
            "+89.5 pól/gestor (+30.7%)",
            "-10.0 días",
            "-28.93 pp",
            "-11.38 pp",
            "-13.84 pp",
            "+$35,445/mes (+34.4%)",
        ]
    )
    composer.add_table(
        headers_sb,
        rows_sb,
        col_alignments=[
            "left",
            "center",
            "right",
            "right",
            "right",
            "right",
            "right",
            "right",
            "right",
        ],
        highlight_last_row=True,
    )

    composer.add_bullet(
        "Hallazgo 2 — Ineficiencia Crítica por Forma de Pago (12.6% de las Llamadas Desperdiciadas): ",
        (
            f"El cruce entre Renovaciones y las {kf['llamadas_totales_bitacora']:,} llamadas de Bitacora_Llamadas revela que los gestores "
            f"destinaron {kf['llamadas_domiciliado_financiado']:,} llamadas ({kf['pct_llamadas_domiciliado_financiado']:.2f}% de toda la bitácora: "
            f"{kf['llamadas_domiciliado']:,} en Domiciliado y {kf['llamadas_financiado']:,} en Financiado) a perseguir pólizas que se renuevan "
            f"de forma casi automática por cargo bancario o exigencia crediticia (94.55% bruta / 94.61% única en Domiciliado y 91.02% bruta / "
            f"91.09% única en Financiado). En contraste, la cartera de pago Manual (20,571 pólizas únicas; 81.63% del volumen) apenas logra "
            f"un 44.51% bruta / 44.49% única de renovación y concentra el 96.86% de todas las comisiones perdidas por Capesa ($1,656,645 USD). "
            f"Debido a que los gestores llegan tarde al contacto Manual, Capesa perdió 4,205 pólizas en base bruta (4,183 únicas) porque el cliente "
            f"'Ya renovó con otro corredor / aseguradora', 2,852 (2,750 en Manual única) por 'Precio / aumento de prima' sin tiempo de recotizar, "
            f"y 1,125 pólizas en base bruta (1,121 únicas / 1,113 en Manual única) porque 'No se logró contactar antes del vencimiento'."
        ),
    )

    headers_pay = [
        "Forma de Pago",
        "Pólizas Únicas\n(13 Meses)",
        "% Cartera",
        "Llamadas en\nBitácora",
        "% Llamadas\nBitácora",
        "Renovación\nBase Bruta",
        "Renovación\nBase Única",
        "Comisión Capturada\n(USD)",
        "Comisión Perdida\n(USD)",
    ]
    rows_pay = []
    for _, r in pay_df.iterrows():
        rows_pay.append(
            [
                r["Forma de pago"],
                f"{int(r['Polizas_Unicas']):,}",
                f"{r['Share_Polizas_Pct']:.2f}%",
                f"{int(r['Llamadas_Bitacora']):,}",
                f"{r['Share_Llamadas_Pct']:.2f}%",
                f"{r['Tasa_Renovacion_Raw_Pct']:.2f}%",
                f"{r['Tasa_Renovacion_Dedup_Pct']:.2f}%",
                f"${r['Comision_Capturada_USD']:,.0f}",
                f"${r['Comision_Perdida_USD']:,.0f}",
            ]
        )
    rows_pay.append(
        [
            "TOTAL / PROMEDIO",
            f"{audit['polizas_unicas_limpias']:,}",
            "100.00%",
            f"{kf['llamadas_totales_bitacora']:,}",
            "100.00%",
            "53.38%",
            f"{audit['tasa_renovacion_global_pct']:.2f}%",
            f"${audit['comision_capturada_13m_usd']:,.0f}",
            f"${audit['comision_perdida_13m_usd']:,.0f}",
        ]
    )
    composer.add_table(
        headers_pay,
        rows_pay,
        col_alignments=[
            "left",
            "right",
            "right",
            "right",
            "right",
            "right",
            "right",
            "right",
            "right",
        ],
        highlight_last_row=True,
    )

    composer.add_bullet(
        "Hallazgo 3 — Sensibilidad Empírica de la Renovación al Plazo de Contacto: ",
        (
            "En la cartera Manual, cuando el primer contacto ocurre cumpliendo la meta corporativa (>=20 días de anticipación), la tasa de "
            "renovación alcanza el 69.67%. Cuando ocurre entre 10 y 19 días baja al 61.96%; entre 4 y 9 días cae al 46.23%; entre 0 y 3 días "
            "se desploma al 31.32%; y cuando se contacta post-vencimiento (<0 días) es de apenas 16.05% (y 0.00% cuando no se logra contacto). "
            "Cada día de retraso le cuesta directamente a Capesa puntos de retención frente a corredores competidores."
        ),
    )

    # 2.2 Propuesta de Transformación con IA y Automatización: Arquitectura de 3 Carriles
    composer.add_heading(
        "2.2 Propuesta de Transformación con IA: Arquitectura Operativa de 3 Carriles y Modelo P(Fuga)",
        level=3,
    )
    composer.add_paragraph(
        text=(
            "Para resolver el cuello de botella sin incrementar la planilla fija de gestores, se diseñó e implementó en src/caso2_engine.py, "
            "src/api.py y main.py una Arquitectura de Orquestación Inteligente en 3 Carriles impulsada por un modelo de Machine Learning interpretable "
            "(Regresión Logística calibrada con ROC-AUC = 0.7101 y Gradient Boosting con ROC-AUC = 0.7509 validados mediante Stratified 5-Fold CV) "
            "que estima la probabilidad de no renovación P(Fuga) de cada póliza Manual y calcula el índice de priorización económico:"
        ),
    )
    composer.add_paragraph(
        bold_prefix="Fórmula de Priorización Comercial: ",
        text="Valor_En_Riesgo_USD = Prima_Renovación (USD) × %_Comisión × P(Fuga). El análisis de concentración demuestra que el Top 30% de las pólizas Manuales ordenadas por este índice concentra el 56.54% de todo el valor económico en riesgo de la correduría ($940,815 USD de $1,663,981 USD en 13 meses).",
    )

    composer.add_bullet(
        "Carril 1 — Zero-Touch Digital para Domiciliado y Financiado (T-30 días): ",
        (
            "Se eliminan las llamadas manuales en frío a las 4,629 pólizas de pago Domiciliado y Financiado (~356 pólizas/mes), liberando "
            "de inmediato 9,808 llamadas (9,054 llamadas/año = 12.6% del tiempo de los gestores). El sistema envía automáticamente a T-30 días "
            "el certificado y aviso de cargo por correo/WhatsApp y valida la transacción con el banco/aseguradora; únicamente las incidencias "
            "de tarjeta vencida o fin de crédito (~5%–8% de los casos) generan un ticket de excepción para gestión."
        ),
    )
    composer.add_bullet(
        "Carril 2 — Agente Conversacional IA Omnicanal de Pre-Contacto a T-25 Días (100% Cartera Manual): ",
        (
            "A exactamente 25 días del vencimiento, un Bot Conversacional (WhatsApp Business API + Voz IA) contacta al 100% de las pólizas "
            "Manuales (~1,582 pólizas/mes), garantizando que ninguna póliza vuelva a ser contactada fuera de la ventana meta de >=20 días. "
            "El Agente IA entrega la cotización de renovación, valida o actualiza teléfonos erróneos (71 nulos y 1,653 números equivocados "
            "en bitácora), envía enlace de pago digital para cierre automático en pólizas de bajo riesgo/sin aumento de prima, y agenda llamada "
            "con el gestor humano para los clientes que solicitan negociación o presentan objeción de precio."
        ),
    )
    composer.add_bullet(
        "Carril 3 — Bandeja de los 5 Gestores Humanos (G01 a G05) Ordenada por Valor en Riesgo a T-20 Días + Copiloto IA: ",
        (
            "Los 5 gestores activos reciben cada mañana en su Bandeja Inteligente únicamente las pólizas Manuales que requieren intervención "
            "humana, ordenadas de mayor a menor Valor_En_Riesgo_USD dentro de la ventana de 20 días. Al abrir una póliza, el Módulo Copiloto IA "
            "le muestra al gestor los factores de riesgo del cliente, el guion de retención personalizado y, si hubo incremento de prima "
            "(principal causa controlable con 2,852 fugas), genera automáticamente una matriz de recotización defensiva comparando aseguradoras "
            "alternativas del portafolio de Capesa (Seguros del Lago, Aseguradora Pacífico Central, Protecta, Mutual Volcán, Cordillera) para "
            "retener al cliente dentro de la correduría antes de que cotice con la competencia."
        ),
    )

    # 2.3 Impacto Financiero Esperado
    composer.add_heading(
        "2.3 Impacto Financiero y Operativo Esperado (Simulación Anualizada a 12 Meses)",
        level=3,
    )
    composer.add_paragraph(
        text=(
            f"Evaluando el contrafactual causal sobre las 25,200 pólizas únicas (y anualizando los 13 meses de datos mediante el factor 12/13), "
            f"la migración a la Arquitectura de 3 Carriles rescata +{sim_m['polizas_recuperadas_anual']:,} pólizas adicionales por año, "
            f"incrementa la tasa de renovación de la cartera Manual en +{sim_m['puntos_retencion_manual_ganados_pp']:.2f} puntos porcentuales "
            f"(de {sim_m['tasa_renovacion_manual_actual_pct']:.2f}% a {sim_m['tasa_renovacion_manual_simulada_pct']:.2f}%), eleva la tasa de "
            f"renovación global de Capesa en +{sim_m['puntos_retencion_global_ganados_pp']:.2f} puntos porcentuales "
            f"(de {sim_m['tasa_renovacion_global_actual_pct']:.2f}% a {sim_m['tasa_renovacion_global_simulada_pct']:.2f}%) y genera un "
            f"impacto económico directo de +${sim_m['impacto_economico_anual_usd']:,.2f} USD anuales en comisiones recuperadas "
            f"(+${sim_m['impacto_economico_13m_usd']:,.2f} USD en el equivalente de 13 meses), llevando los ingresos anuales por comisiones "
            f"de ${sim_m['comision_actual_anual_usd']:,.2f} USD a ${sim_m['comision_simulada_anual_usd']:,.2f} USD (+21.9%). "
            f"Simultáneamente, la ocupación telefónica de los 5 gestores pasa del colapso actual al {sim_m['utilizacion_capacidad_humana_pct']:.1f}% "
            f"de su capacidad ({sim_m['llamadas_humanas_requeridas_mes_3carriles']:,} de {sim_m['capacidad_mensual_5_gestores_llamadas']:,} llamadas/mes)."
        ),
    )

    headers_lanes = [
        "Carril Operativo",
        "Universo Objetivo",
        "Mecanismo de IA y Automatización",
        "Llamadas Humanas\nLiberadas / Año",
        "Pólizas Adicionales\nRetenidas / Año",
        "Comisiones Anuales\nRescatadas (USD)",
    ]
    rows_lanes = []
    for _, r in lanes_df.iterrows():
        rows_lanes.append(
            [
                r["Carril"],
                r["Segmento_Objetivo"],
                r["Mecanismo_IA_Automatizacion"],
                f"{int(r['Llamadas_Humanas_Liberadas_Anual']):,}",
                f"+{int(r['Polizas_Adicionales_Retenidas_Anual']):,}",
                f"+${r['Impacto_Comisiones_Anual_USD']:,.2f}",
            ]
        )
    rows_lanes.append(
        [
            "IMPACTO TOTAL ANUAL (3 CARRILES)",
            "25,200 pólizas (13M) / ~23,262 pólizas/año",
            "Orquestación integral Zero-Touch + Bot T-25 + Bandeja Valor en Riesgo",
            f"{int(lanes_df['Llamadas_Humanas_Liberadas_Anual'].sum()):,}",
            f"+{sim_m['polizas_recuperadas_anual']:,}",
            f"+${sim_m['impacto_economico_anual_usd']:,.2f}",
        ]
    )
    composer.add_table(
        headers_lanes,
        rows_lanes,
        col_alignments=["left", "left", "left", "right", "right", "right"],
        highlight_last_row=True,
    )

    # 2.4 Hoja de Ruta 30-60-90 días, KPIs y Supuestos
    composer.add_heading(
        "2.4 Hoja de Ruta de Puesta en Marcha (30, 60 y 90 Días), KPIs y Supuestos Explícitos",
        level=3,
    )

    headers_road = [
        "Fase / Horizonte",
        "Hitos de Implementación Técnica y Operativa",
        "Entregable / Quick Win",
        "KPI Meta de Éxito",
    ]
    rows_road = [
        [
            "Fase 1: Días 1 a 30\n(Quick Wins & Higiene)",
            "1. Apagado inmediato de llamadas en frío a Domiciliado y Financiado (activación Carril 1 Zero-Touch).\n2. Despliegue de la Bandeja Priorizada por Valor en Riesgo para G01–G05.\n3. Regla de validación de unicidad de póliza y teléfono obligatorio en CRM.",
            "Liberación instantánea del 12.6% de capacidad telefónica (~755 llamadas/mes) y foco humano en el Top 30% de mayor comisión.",
            "0 llamadas manuales sin excepción en Domiciliado/Financiado; mediana de anticipación sube de 4 a >=12 días.",
        ],
        [
            "Fase 2: Días 31 a 60\n(Agente IA T-25)",
            "1. Integración del Bot Conversacional (WhatsApp Business API + Voz IA) disparado automáticamente a T-25 días con PDF de cotización.\n2. Habilitación de pasarela de confirmación digital para renovaciones sin aumento de prima.",
            "Pre-contacto del 100% de la cartera Manual antes del día T-20 y cierre digital del tramo de baja complejidad.",
            ">=92% de pólizas Manuales contactadas a >=20 días; >=30% de cierres simples vía Bot sin intervención humana.",
        ],
        [
            "Fase 3: Días 61 a 90\n(Copiloto Multi-Cotizador y Escala)",
            "1. Activación del Copiloto IA con recotización automática multi-aseguradora cuando % cambio de prima > 5%.\n2. Reentrenamiento mensual del modelo P(Fuga) y monitoreo A/B de scripts de retención por ramo y segmento.",
            "Reducción drástica de fugas por precio y competencia en Flota Corporativa, Pyme e Individual de alto valor.",
            "Tasa de renovación global >=68% (+15 pp vs línea base) y rescate anualizado >=$550,000 USD en comisiones.",
        ],
    ]
    composer.add_table(
        headers_road,
        rows_road,
        col_alignments=["left", "left", "left", "left"],
    )

    composer.add_bullet(
        "Supuestos Explícitos del Caso 2: ",
        (
            "(a) Los 5 gestores activos trabajan ~21.5 días hábiles/mes con una capacidad estándar de 50 llamadas/día (5,375 llamadas/mes en total); "
            "(b) El efecto causal de adelantar el contacto de una mediana de 4 días a >=20 días se estima controlando por Ramo, Aseguradora, Segmento, "
            "Origen, % cambio de prima, Antigüedad y Siniestralidad mediante el modelo logístico entrenado; (c) En el Carril 1 se recupera conservadoramente "
            "el 25% de los rechazos operativos de cobro mediante alertas digitales tempranas; (d) En el Carril 3 la recotización defensiva multi-aseguradora "
            "reduce en un 6% relativo adicional la probabilidad remanente de fuga en los deciles de prioridad humana."
        ),
    )
    composer.add_bullet(
        "Información Adicional que se Solicitaría al Comité de Capesa: ",
        (
            "(1) Tarifarios API o matrices de suscripción de las 5 aseguradoras (Pacífico Central, Seguros del Lago, Protecta, Mutual Volcán y Cordillera) "
            "para automatizar en tiempo real la cotización comparativa a T-26 días; (2) Costo unitario de mensajería WhatsApp Business API y minuto de Voz IA "
            "(estimado en <$0.08 USD por póliza gestionada, lo que representa menos del 0.4% de las comisiones rescatadas); y (3) Histórico de motivos de "
            "siniestro para personalizar el acompañamiento post-reclamo."
        ),
    )

    # -----------------------------------------------------------------------
    # 3. Sección Transversal de Metodología de IA y Validación Humana
    # -----------------------------------------------------------------------
    composer.add_heading(
        "3. Declaración Transversal: Metodología de Uso de IA y Protocolos de Validación Humana",
        level=3,
    )
    composer.add_paragraph(
        text=(
            "En cumplimiento de las consideraciones generales de la prueba técnica, a continuación se detalla cómo se integraron "
            "las herramientas de Inteligencia Artificial durante la resolución de ambos casos y qué protocolos de verificación "
            "humana y determinística garantizaron la exactitud matemática de cada hallazgo:"
        ),
    )
    composer.add_bullet(
        "1. Rol de los Agentes de IA en el Desarrollo (Antigravity Pair-Programming): ",
        (
            "Se utilizaron agentes de IA en Antigravity para acelerar la exploración programática inicial de los esquemas de ambos archivos Excel, "
            "estructurar la arquitectura modular en Python (src/caso1_engine.py y src/caso2_engine.py), construir la aplicación web Full-Stack "
            "en FastAPI + Uvicorn (main.py, src/api.py) con interfaz Single Page Application (SPA) en HTML5, Tailwind CSS, ApexCharts y Plotly.js, "
            "y automatizar la composición tipográfica de este entregable mediante python-docx (src/docx_filler.py)."
        ),
    )
    composer.add_bullet(
        "2. Protocolo de Validación Humana sobre Datos Sucios y Sumas Algebraicas: ",
        (
            "Ningún número ni conclusión fue aceptado de un modelo generativo sin verificación determinística en código: "
            "(i) En el Caso 1, se verificó manualmente mediante expresiones regulares y tablas dinámicas de control que las 52 variantes de nombres de "
            "modelos en Ventas, 42 en Inventario, 63 en Leads y 37 en Pedidos mapearan con 0 pérdidas a los 11 modelos oficiales; se comprobaron una a una "
            "las 9 Notas de Crédito (NC-880383 a NC-884397) verificando sus facturas de referencia y el cuadre exacto de 5,213 brutas - 9 NCs = 5,204 unidades "
            "netas; y se auditó el desglose de los pedidos en tránsito de RAV4 (confirmando que las 47 unidades totales en tránsito se componen de las "
            "44 unidades del pedido de julio PF-41141 más 3 unidades rezagadas del pedido de abril PF-41130). "
            "(ii) En el Caso 2, se verificó que las 151 filas repetidas en Renovaciones fueran duplicados exactos de póliza (25,351 -> 25,200 pólizas únicas), "
            "se contrastaron todas las métricas tanto en base bruta como en base deduplicada (577 vs 574 contactos post-vencimiento; 4,205 vs 4,183 fugas "
            "a competencia; 1,125 vs 1,121 sin contacto a tiempo), y se validó que la suma de intentos de llamada por forma de pago cuadrara exactamente "
            "con los 78,058 registros de Bitacora_Llamadas (5,053 Domiciliado + 4,755 Financiado = 9,808 llamadas [12.57%] + 68,250 Manual = 78,058)."
        ),
    )
    composer.add_bullet(
        "3. Validación Estadística y Pruebas Automatizadas de Regresión (test_pipeline.py): ",
        (
            "Los modelos predictivos de fuga se evaluaron con validación cruzada estratificada de 5 particiones (StratifiedKFold) fuera de muestra "
            "para evitar sobreajuste, verificando tanto el poder discriminante (ROC-AUC) como la calibración probabilística (Brier Score = 0.2161). "
            "Finalmente, se construyó el script test_pipeline.py con aserciones automatizadas (assert) sobre cada suma de control, garantizando "
            "100% de reproducibilidad técnica en cualquier entorno local o en la nube."
        ),
    )


# ---------------------------------------------------------------------------
# Ejecución Principal del Generador de Documento Entregable
# ---------------------------------------------------------------------------

def build_final_deliverable_docx(
    input_docx: str | Path = "Prueba Ingeniero IA.docx",
    output_docx: str | Path = "Prueba Ingeniero IA - Entregable Final.docx",
) -> Path:
    print("Ejecutando motores analíticos de Caso 1 y Caso 2...")
    res1 = run_caso1_pipeline()
    res2 = run_caso2_pipeline()

    doc = Document(str(input_docx))

    # Localizar los dos párrafos marcadores «Escribe aquí tu respuesta.»
    placeholder_paragraphs = [
        p for p in doc.paragraphs if "Escribe aquí tu respuesta" in p.text
    ]
    if len(placeholder_paragraphs) < 2:
        raise RuntimeError(
            f"Se esperaban 2 secciones 'Escribe aquí tu respuesta.', se encontraron {len(placeholder_paragraphs)}."
        )

    p_caso1, p_caso2 = placeholder_paragraphs[0], placeholder_paragraphs[1]

    # Reemplazar el texto del párrafo ancla del Caso 1 por la introducción ejecutiva y añadir los bloques
    p_caso1.text = ""
    r1_intro = p_caso1.add_run(
        "MEMORÁNDUM EJECUTIVO — PROPUESTA DE PEDIDO A FÁBRICA (VENTANA OCTUBRE 2026) Y SISTEMA S&OP INTELIGENTE"
    )
    r1_intro.bold = True
    r1_intro.font.size = Pt(11)
    r1_intro.font.color.rgb = RGBColor(185, 28, 28)

    comp1 = SequentialComposer(doc, p_caso1)
    populate_caso1_response(comp1, res1)

    # Reemplazar el texto del párrafo ancla del Caso 2 por la introducción ejecutiva y añadir los bloques
    p_caso2.text = ""
    r2_intro = p_caso2.add_run(
        "MEMORÁNDUM AL COMITÉ DIRECTIVO DE CAPESA — DIAGNÓSTICO OPERATIVO Y ARQUITECTURA DE RENOVACIONES CON IA"
    )
    r2_intro.bold = True
    r2_intro.font.size = Pt(11)
    r2_intro.font.color.rgb = RGBColor(21, 128, 61)

    comp2 = SequentialComposer(doc, p_caso2)
    populate_caso2_response(comp2, res2)

    out_path = Path(output_docx)
    doc.save(str(out_path))
    print(f"Documento generado exitosamente: {out_path.resolve()} ({out_path.stat().st_size:,} bytes)")
    return out_path


if __name__ == "__main__":
    build_final_deliverable_docx()

