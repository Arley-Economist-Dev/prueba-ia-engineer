/**
 * Cliente SPA de Alto Rendimiento — Casa Pellas · AI Executive Decision Suite
 * Renderiza en cliente (60fps) con ApexCharts y Plotly.js en paleta corporativa oficial (Light Theme).
 */

let caso1State = null;
let caso2DiagState = null;
let caso2PrioState = null;

// Instancias de ApexCharts
let chartC1Bars = null;
let chartC1Donut = null;
let chartC2Anticipation = null;
let chartC2Payment = null;
let chartC2Break = null;
let chartC2RoiBars = null;

const fmtUSD = (n, decimals = 0) =>
  "$" +
  Number(n || 0).toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

const fmtInt = (n) => Number(n || 0).toLocaleString("en-US");

// ---------------------------------------------------------------------------
// Navegación entre Pestañas (Caso 1 / Caso 2)
// ---------------------------------------------------------------------------

function switchTab(tabName) {
  const v1 = document.getElementById("view-caso1");
  const v2 = document.getElementById("view-caso2");
  const b1 = document.getElementById("tab-btn-caso1");
  const b2 = document.getElementById("tab-btn-caso2");

  if (tabName === "caso1") {
    v1.classList.remove("hidden");
    v2.classList.add("hidden");
    b1.classList.add("active");
    b2.classList.remove("active");
    window.dispatchEvent(new Event("resize"));
  } else {
    v1.classList.add("hidden");
    v2.classList.remove("hidden");
    b2.classList.add("active");
    b1.classList.remove("active");
    if (!caso2DiagState) {
      initCaso2();
    } else {
      window.dispatchEvent(new Event("resize"));
    }
  }
}

// ---------------------------------------------------------------------------
// CASO 1 · PEDIDOS INTELIGENTES TOYOTA
// ---------------------------------------------------------------------------

function onCaso1ControlInput() {
  const safetyDays = document.getElementById("c1-safety-days").value;
  const crmPct = document.getElementById("c1-crm-capture").value;
  document.getElementById("c1-safety-days-val").textContent = `${safetyDays} días (${(safetyDays / 30).toFixed(1)}M)`;
  document.getElementById("c1-crm-capture-val").textContent = `${crmPct}%`;
}

function resetCaso1Params() {
  document.getElementById("c1-safety-days").value = 30;
  document.getElementById("c1-crm-capture").value = 50;
  document.getElementById("c1-rav4-toggle").checked = true;
  onCaso1ControlInput();
  fetchCaso1Data();
}

async function fetchCaso1Data() {
  const safetyDays = document.getElementById("c1-safety-days").value;
  const crmPct = document.getElementById("c1-crm-capture").value;
  const rav4Toggle = document.getElementById("c1-rav4-toggle").checked;
  const badge = document.getElementById("c1-loading-badge");

  badge.classList.remove("hidden");
  try {
    const url = `/api/caso1/pedidos?safety_days=${safetyDays}&crm_capture_pct=${crmPct}&rav4_phaseout=${rav4Toggle}`;
    const res = await fetch(url);
    const data = await res.json();
    caso1State = data;
    renderCaso1Dashboard(data);
  } catch (err) {
    console.error("Error cargando Caso 1:", err);
  } finally {
    badge.classList.add("hidden");
  }
}

function renderCaso1Dashboard(data) {
  const t = data.totals;
  const rav4Active = data.parameters.rav4_phaseout;

  // 1. KPIs Ejecutivos
  document.getElementById("kpi-c1-unidades").textContent = `${fmtInt(t.total_unidades_pedidas)} uds`;
  document.getElementById("kpi-c1-unidades-sub").textContent = `Patio actual: ${fmtInt(t.total_inv_30sep)} uds · En tránsito: ${fmtInt(t.total_transito_oct_ene)} uds`;

  document.getElementById("kpi-c1-capital").textContent = fmtUSD(t.total_capital_comprometido_usd, 0);
  document.getElementById("kpi-c1-planpiso").textContent = `Plan Piso (0.9%/mes): ${fmtUSD(t.total_costo_plan_piso_mensual_usd, 0)} / mes`;

  document.getElementById("kpi-c1-margen").textContent = fmtUSD(t.total_margen_bruto_esperado_usd, 0);
  document.getElementById("kpi-c1-margen-pct").textContent = `${(t.margen_bruto_ponderado_pct * 100).toFixed(2)}% s/ Venta`;
  document.getElementById("kpi-c1-ingreso").textContent = `Ingreso proyectado: ${fmtUSD(t.total_ingreso_esperado_usd, 0)} USD`;

  const riskCard = document.getElementById("kpi-c1-risk-card");
  const riskBadge = document.getElementById("kpi-c1-risk-badge");
  const riskTitle = document.getElementById("kpi-c1-risk-title");
  const riskSub = document.getElementById("kpi-c1-risk-sub");
  const rav4Note = document.getElementById("c1-rav4-status-note");

  if (rav4Active) {
    riskCard.className = "cp-kpi-card p-5";
    riskBadge.textContent = "CONTROLADO";
    riskBadge.className = "px-2 py-0.5 text-[11px] font-bold rounded bg-emerald-50 text-emerald-700 border border-emerald-200";
    riskTitle.textContent = "RAV4: Pedido 0 uds";
    riskSub.textContent = `${t.rav4_unidades_a_liquidar_oct_abr} uds actuales se liquidan a 0 antes de May-2027`;
    riskSub.className = "text-xs text-emerald-700 mt-1 font-semibold";
    rav4Note.textContent = "Activo: 9 patio + 47 tránsito (44 pedido Jul-26) = 56 uds cubren Oct26–Abr27 sin pedir más unidades.";
    rav4Note.className = "text-[11px] text-emerald-700 font-medium mt-2";
  } else {
    riskCard.className = "cp-kpi-card p-5 kpi-accent-red";
    riskBadge.textContent = "ALERTA CRÍTICA";
    riskBadge.className = "px-2 py-0.5 text-[11px] font-bold rounded bg-red-50 text-red-700 border border-red-200";
    riskTitle.textContent = `RAV4: +${t.rav4_order_qty} uds pedidas`;
    riskSub.textContent = `Sobrestock May-27: ${t.rav4_end_stock_abr27.toFixed(0)} uds (${fmtUSD(t.rav4_obsolescence_exposure_usd, 0)})`;
    riskSub.className = "text-xs text-red-600 mt-1 font-bold";
    rav4Note.textContent = "Atención: Se están pidiendo unidades adicionales de generación saliente sin subsidio de fábrica.";
    rav4Note.className = "text-[11px] text-red-600 font-semibold mt-2";
  }

  // 2. Poblar Selectores de Modelo si aún no están poblados
  const curveSelect = document.getElementById("c1-curve-model-select");
  const mixSelect = document.getElementById("c1-mix-model-select");
  if (curveSelect.options.length <= 1) {
    data.official_models.forEach((m) => {
      const opt1 = document.createElement("option");
      opt1.value = m;
      opt1.textContent = m;
      curveSelect.appendChild(opt1);

      const opt2 = document.createElement("option");
      opt2.value = m;
      opt2.textContent = m;
      mixSelect.appendChild(opt2);
    });
    mixSelect.value = "Hilux";
  }

  // 3. Renderizar Tabla Maestra de los 11 Modelos
  renderCaso1Table(data.models, t);

  // 4. Renderizar Gráficos ApexCharts y Plotly
  renderCaso1ApexBars(data.models);
  renderCaso1ApexDonut(data.models);
  renderCaso1TrajectoryChart();
  renderCaso1MixChart();
}

function renderCaso1Table(models, totals) {
  const tbody = document.getElementById("table-c1-models-body");
  const tfoot = document.getElementById("table-c1-models-foot");
  tbody.innerHTML = "";

  let sumDem4M = 0;
  let sumProyEne = 0;
  let sumDem3M = 0;
  let sumSS = 0;
  let sumBruto = 0;

  models.forEach((r) => {
    sumDem4M += r.Demanda_Oct26_Ene27_4M;
    sumProyEne += r.Inv_Proyectado_31Ene27;
    sumDem3M += r.Demanda_Feb27_Abr27_3M;
    sumSS += r.Stock_Seguridad_Objetivo;
    sumBruto += r.Necesidad_Neta_Feb_Abr;

    const isRav4Zero = r.Modelo === "RAV4" && r.Pedido_Sugerido_Oct26 === 0;
    const isStockoutPre = r.Deficit_Oct26_Ene27 > 0;

    let badgeHtml = `<span class="cp-pill cp-pill-blue">Lote Óptimo</span>`;
    if (isRav4Zero) {
      badgeHtml = `<span class="cp-pill cp-pill-amber">Liquidación Gen. Actual</span>`;
    } else if (isStockoutPre) {
      badgeHtml = `<span class="cp-pill cp-pill-rose">Reposición Urgente</span>`;
    }

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td class="font-bold text-[#002D62]">${r.Modelo}</td>
      <td class="text-center text-slate-600 font-mono font-semibold">${r.Lote_Min_Mult}</td>
      <td class="text-right text-slate-700 tabular-nums">${fmtInt(r.Inv_30Sep)}</td>
      <td class="text-right font-medium text-[#004899] tabular-nums">${fmtInt(r.Transito_Oct26_Ene27)}</td>
      <td class="text-right text-slate-700 tabular-nums">${r.Demanda_Oct26_Ene27_4M.toFixed(1)}</td>
      <td class="text-right font-semibold tabular-nums ${r.Inv_Proyectado_31Ene27 === 0 ? 'text-red-600 font-bold' : 'text-slate-800'}">${r.Inv_Proyectado_31Ene27.toFixed(1)}</td>
      <td class="text-right text-slate-700 tabular-nums">${r.Demanda_Feb27_Abr27_3M.toFixed(1)}</td>
      <td class="text-right text-slate-600 tabular-nums">${r.Stock_Seguridad_Objetivo.toFixed(1)}</td>
      <td class="text-right text-slate-600 tabular-nums">${r.Necesidad_Neta_Feb_Abr.toFixed(1)}</td>
      <td class="text-right font-extrabold text-sm tabular-nums ${r.Pedido_Sugerido_Oct26 === 0 ? 'text-amber-600' : 'text-[#004899]'}">${fmtInt(r.Pedido_Sugerido_Oct26)}</td>
      <td class="text-right font-semibold text-slate-900 tabular-nums">${fmtUSD(r.Capital_Comprometido_USD, 0)}</td>
      <td class="text-right font-bold text-emerald-600 tabular-nums">${fmtUSD(r.Margen_Bruto_Esperado_USD, 0)}</td>
      <td class="text-center">${badgeHtml}</td>
    `;
    tbody.appendChild(tr);
  });

  tfoot.innerHTML = `
    <tr>
      <td class="text-left py-3 px-3">TOTAL CONSOLIDADO (11 MODELOS)</td>
      <td class="text-center py-3 px-3">—</td>
      <td class="text-right py-3 px-3">${fmtInt(totals.total_inv_30sep)}</td>
      <td class="text-right py-3 px-3 text-[#004899]">${fmtInt(totals.total_transito_oct_ene)}</td>
      <td class="text-right py-3 px-3">${sumDem4M.toFixed(1)}</td>
      <td class="text-right py-3 px-3">${sumProyEne.toFixed(1)}</td>
      <td class="text-right py-3 px-3">${sumDem3M.toFixed(1)}</td>
      <td class="text-right py-3 px-3">${sumSS.toFixed(1)}</td>
      <td class="text-right py-3 px-3">${sumBruto.toFixed(1)}</td>
      <td class="text-right py-3 px-3 text-[#004899] text-base">${fmtInt(totals.total_unidades_pedidas)} uds</td>
      <td class="text-right py-3 px-3">${fmtUSD(totals.total_capital_comprometido_usd, 0)}</td>
      <td class="text-right py-3 px-3 text-emerald-600">${fmtUSD(totals.total_margen_bruto_esperado_usd, 0)}</td>
      <td class="text-center py-3 px-3 text-xs text-slate-600">Plan Piso: ${fmtUSD(totals.total_costo_plan_piso_mensual_usd, 0)}/m</td>
    </tr>
  `;
}

function renderCaso1ApexBars(models) {
  const categories = models.map((m) => m.Modelo);
  const sPedido = models.map((m) => m.Pedido_Sugerido_Oct26);
  const sInv = models.map((m) => m.Inv_30Sep);
  const sTrans = models.map((m) => m.Transito_Oct26_Ene27);

  const options = {
    chart: {
      type: "bar",
      height: 375,
      toolbar: { show: false },
      background: "transparent",
      foreColor: "#1E293B",
      animations: { enabled: true, speed: 300 },
    },
    theme: { mode: "light" },
    plotOptions: {
      bar: {
        horizontal: true,
        barHeight: "72%",
        borderRadius: 4,
      },
    },
    dataLabels: {
      enabled: true,
      style: { fontSize: "10px", colors: ["#ffffff"] },
    },
    stroke: { show: true, width: 1, colors: ["#ffffff"] },
    colors: ["#004899", "#64748B", "#0284C7"],
    series: [
      { name: "Pedido Recomendado Oct-26", data: sPedido },
      { name: "Inventario Actual (30/Sep)", data: sInv },
      { name: "En Tránsito (Oct26–Ene27)", data: sTrans },
    ],
    xaxis: {
      categories: categories,
      labels: { style: { colors: "#475569", fontSize: "11px", fontWeight: 500 } },
    },
    yaxis: {
      labels: { style: { colors: "#002D62", fontSize: "11px", fontWeight: 700 } },
    },
    grid: { borderColor: "#E2E8F0", strokeDashArray: 3 },
    legend: { position: "top", horizontalAlign: "left", labels: { colors: "#1E293B" } },
    tooltip: {
      theme: "light",
      y: { formatter: (val) => `${val} unidades` },
    },
  };

  if (chartC1Bars) {
    chartC1Bars.updateOptions(options);
  } else {
    chartC1Bars = new ApexCharts(document.querySelector("#chart-c1-bars"), options);
    chartC1Bars.render();
  }
}

function renderCaso1ApexDonut(models) {
  const activeModels = models.filter((m) => m.Margen_Bruto_Esperado_USD > 0);
  const labels = activeModels.map((m) => m.Modelo);
  const series = activeModels.map((m) => Math.round(m.Margen_Bruto_Esperado_USD));

  const options = {
    chart: {
      type: "donut",
      height: 375,
      background: "transparent",
      foreColor: "#1E293B",
    },
    theme: { mode: "light" },
    labels: labels,
    series: series,
    colors: [
      "#004899",
      "#002D62",
      "#D32F2F",
      "#0284C7",
      "#10B981",
      "#F59E0B",
      "#8B5CF6",
      "#EC4899",
      "#0D9488",
      "#6366F1",
    ],
    stroke: { colors: ["#FFFFFF"], width: 2 },
    dataLabels: {
      enabled: true,
      formatter: (val) => `${val.toFixed(1)}%`,
      style: { fontSize: "11px", fontWeight: "bold" },
    },
    plotOptions: {
      pie: {
        donut: {
          size: "62%",
          labels: {
            show: true,
            name: { show: true, color: "#64748B", fontSize: "13px" },
            value: {
              show: true,
              color: "#002D62",
              fontSize: "18px",
              fontWeight: 800,
              formatter: (v) => fmtUSD(v, 0),
            },
            total: {
              show: true,
              label: "Margen Total",
              color: "#64748B",
              formatter: (w) => {
                const total = w.globals.seriesTotals.reduce((a, b) => a + b, 0);
                return fmtUSD(total, 0);
              },
            },
          },
        },
      },
    },
    legend: { position: "bottom", labels: { colors: "#334155" } },
    tooltip: {
      theme: "light",
      y: { formatter: (val) => fmtUSD(val, 0) },
    },
  };

  if (chartC1Donut) {
    chartC1Donut.destroy();
  }
  chartC1Donut = new ApexCharts(document.querySelector("#chart-c1-donut"), options);
  chartC1Donut.render();
}

function renderCaso1TrajectoryChart() {
  if (!caso1State) return;
  const sel = document.getElementById("c1-curve-model-select").value;
  const raw = caso1State.monthly_projection;

  let rows = [];
  if (sel === "ALL") {
    const byOrder = {};
    raw.forEach((r) => {
      if (!byOrder[r.Orden_Mes]) {
        byOrder[r.Orden_Mes] = {
          Orden_Mes: r.Orden_Mes,
          Etiqueta_Mes: r.Etiqueta_Mes,
          Inventario_Cierre_Uds: 0,
          Demanda_Mensual_Uds: 0,
          Llegadas_Uds: 0,
        };
      }
      byOrder[r.Orden_Mes].Inventario_Cierre_Uds += r.Inventario_Cierre_Uds;
      byOrder[r.Orden_Mes].Demanda_Mensual_Uds += r.Demanda_Mensual_Uds;
      byOrder[r.Orden_Mes].Llegadas_Uds += r.Llegadas_Uds;
    });
    rows = Object.values(byOrder).sort((a, b) => a.Orden_Mes - b.Orden_Mes);
  } else {
    rows = raw.filter((r) => r.Modelo === sel).sort((a, b) => a.Orden_Mes - b.Orden_Mes);
  }

  const xLabels = rows.map((r) => r.Etiqueta_Mes);
  const yInv = rows.map((r) => Number(r.Inventario_Cierre_Uds.toFixed(1)));
  const yDem = rows.map((r) => Number(r.Demanda_Mensual_Uds.toFixed(1)));
  const yArr = rows.map((r) => Number(r.Llegadas_Uds.toFixed(1)));

  const traces = [
    {
      x: xLabels,
      y: yArr,
      type: "bar",
      name: "Llegadas (Tránsito / Pedido Oct)",
      marker: { color: "rgba(0, 72, 153, 0.25)" },
    },
    {
      x: xLabels,
      y: yInv,
      type: "scatter",
      mode: "lines+markers+text",
      name: "Inventario Proy. al Cierre (uds)",
      text: yInv.map((v) => `${Math.round(v)}`),
      textposition: "top center",
      textfont: { color: "#002D62", size: 11, weight: 700 },
      line: { color: "#004899", width: 3.5 },
      marker: { size: 8, color: "#002D62" },
    },
    {
      x: xLabels,
      y: yDem,
      type: "scatter",
      mode: "lines+markers",
      name: "Demanda Mensual Planificada",
      line: { color: "#D32F2F", width: 2.5, dash: "dash" },
      marker: { size: 7, color: "#D32F2F" },
    },
  ];

  const layout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#334155", family: "Inter, sans-serif", size: 11 },
    margin: { l: 45, r: 20, t: 25, b: 60 },
    legend: { orientation: "h", y: 1.15, x: 0 },
    xaxis: { gridcolor: "#E2E8F0", tickangle: -20 },
    yaxis: { gridcolor: "#E2E8F0", title: "Unidades" },
    barmode: "overlay",
  };

  Plotly.react("chart-c1-trajectory", traces, layout, {
    responsive: true,
    displayModeBar: false,
  });
}

function renderCaso1MixChart() {
  if (!caso1State) return;
  const sel = document.getElementById("c1-mix-model-select").value || "Hilux";
  const rows = caso1State.version_color_mix.filter((r) => r.Modelo === sel);
  const modelOrder =
    caso1State.models.find((m) => m.Modelo === sel)?.Pedido_Sugerido_Oct26 || 0;

  const valField = modelOrder > 0 ? "Unidades_Sugeridas" : "Share_Optimo_Pct";
  const yAxisTitle =
    modelOrder > 0
      ? `Unidades a Pedir (${modelOrder} uds)`
      : "Participación Histórica Óptima (%)";

  const colorsUnique = [...new Set(rows.map((r) => r.Color))];
  const versionsUnique = [...new Set(rows.map((r) => r.Versión))];

  const palette = ["#004899", "#D32F2F", "#0284C7", "#10B981", "#64748B", "#F59E0B"];
  const traces = colorsUnique.map((colorName, idx) => {
    const yVals = versionsUnique.map((ver) => {
      const found = rows.find((r) => r.Versión === ver && r.Color === colorName);
      return found ? found[valField] : 0;
    });
    return {
      x: versionsUnique,
      y: yVals,
      name: colorName,
      type: "bar",
      text: yVals.map((v) => (v > 0 ? (modelOrder > 0 ? `${v}` : `${v.toFixed(1)}%`) : "")),
      textposition: "inside",
      marker: { color: palette[idx % palette.length] },
    };
  });

  const layout = {
    barmode: "stack",
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#334155", family: "Inter, sans-serif", size: 11 },
    margin: { l: 45, r: 20, t: 25, b: 55 },
    legend: { orientation: "h", y: 1.15, x: 0 },
    xaxis: { gridcolor: "#E2E8F0" },
    yaxis: { gridcolor: "#E2E8F0", title: yAxisTitle },
  };

  Plotly.react("chart-c1-mix", traces, layout, {
    responsive: true,
    displayModeBar: false,
  });
}

function exportCaso1Excel() {
  const safetyDays = document.getElementById("c1-safety-days").value;
  const crmPct = document.getElementById("c1-crm-capture").value;
  const rav4Toggle = document.getElementById("c1-rav4-toggle").checked;
  window.location.href = `/api/exportar/caso1?safety_days=${safetyDays}&crm_capture_pct=${crmPct}&rav4_phaseout=${rav4Toggle}`;
}

// ---------------------------------------------------------------------------
// CASO 2 · ORQUESTADOR DE RENOVACIONES CAPESA
// ---------------------------------------------------------------------------

async function initCaso2() {
  try {
    const resDiag = await fetch("/api/caso2/diagnostico");
    caso2DiagState = await resDiag.json();
    renderCaso2DiagnosticCharts(caso2DiagState);
  } catch (err) {
    console.error("Error cargando diagnóstico Caso 2:", err);
  }
  await fetchCaso2Priorizacion();
}

function renderCaso2DiagnosticCharts(diag) {
  // 1. Curva de Renovación Manual según Días de Anticipación
  const manualCurve = diag.anticipation_curve.filter(
    (r) => r["Forma de pago"] === "Manual"
  );
  const antOptions = {
    chart: {
      type: "bar",
      height: 300,
      toolbar: { show: false },
      background: "transparent",
      foreColor: "#1E293B",
    },
    theme: { mode: "light" },
    plotOptions: {
      bar: {
        borderRadius: 4,
        columnWidth: "60%",
        distributed: true,
        dataLabels: { position: "top" },
      },
    },
    colors: ["#D32F2F", "#EA580C", "#F59E0B", "#0284C7", "#004899", "#10B981"],
    dataLabels: {
      enabled: true,
      formatter: (v) => `${v.toFixed(1)}%`,
      offsetY: -18,
      style: { fontSize: "10px", colors: ["#0F172A"], fontWeight: "bold" },
    },
    series: [
      {
        name: "Tasa de Renovación Manual (%)",
        data: manualCurve.map((r) => r.Tasa_Renovacion_Pct),
      },
    ],
    xaxis: {
      categories: manualCurve.map((r) =>
        r.Tramo_Anticipacion.replace(/^\d+\.\s*/, "")
      ),
      labels: {
        style: { colors: "#475569", fontSize: "10px" },
        rotate: -25,
      },
    },
    yaxis: {
      max: 85,
      title: { text: "% Renovación", style: { color: "#002D62" } },
    },
    grid: { borderColor: "#E2E8F0", strokeDashArray: 3 },
    legend: { show: false },
    tooltip: { theme: "light" },
  };
  if (chartC2Anticipation) chartC2Anticipation.destroy();
  chartC2Anticipation = new ApexCharts(
    document.querySelector("#chart-c2-anticipation"),
    antOptions
  );
  chartC2Anticipation.render();

  // 2. Llamadas por Forma de Pago vs Tasa de Renovación
  const pay = diag.payment_efficiency;
  const payOptions = {
    chart: {
      height: 300,
      type: "line",
      toolbar: { show: false },
      background: "transparent",
      foreColor: "#1E293B",
    },
    theme: { mode: "light" },
    series: [
      {
        name: "Llamadas en Bitácora",
        type: "column",
        data: pay.map((r) => r.Llamadas_Bitacora),
      },
      {
        name: "Tasa de Renovación (%)",
        type: "line",
        data: pay.map((r) => r.Tasa_Renovacion_Raw_Pct),
      },
    ],
    colors: ["#004899", "#10B981"],
    stroke: { width: [0, 3] },
    dataLabels: {
      enabled: true,
      enabledOnSeries: [1],
      formatter: (v) => `${v.toFixed(1)}%`,
    },
    labels: pay.map((r) => r["Forma de pago"]),
    yaxis: [
      {
        title: { text: "Llamadas", style: { color: "#002D62" } },
        labels: { formatter: (v) => fmtInt(Math.round(v)) },
      },
      {
        opposite: true,
        max: 105,
        min: 0,
        title: { text: "Renovación (%)", style: { color: "#059669" } },
        labels: { formatter: (v) => `${v.toFixed(0)}%` },
      },
    ],
    grid: { borderColor: "#E2E8F0", strokeDashArray: 3 },
    legend: { position: "top", labels: { colors: "#1E293B" } },
    tooltip: { theme: "light" },
  };
  if (chartC2Payment) chartC2Payment.destroy();
  chartC2Payment = new ApexCharts(
    document.querySelector("#chart-c2-payment"),
    payOptions
  );
  chartC2Payment.render();

  // 3. Quiebre Estructural Diciembre 2025 (Salida G06 y G07)
  const evol = diag.monthly_evolution;
  const breakOptions = {
    chart: {
      height: 300,
      type: "line",
      toolbar: { show: false },
      background: "transparent",
      foreColor: "#1E293B",
    },
    theme: { mode: "light" },
    series: [
      {
        name: "Pólizas / Gestor / Mes",
        type: "column",
        data: evol.map((r) => r.Polizas_Por_Gestor),
      },
      {
        name: "Renovación Global (%)",
        type: "line",
        data: evol.map((r) => r.Tasa_Renovacion_Global_Pct),
      },
      {
        name: "% En Meta (>=20d)",
        type: "line",
        data: evol.map((r) => r.Pct_En_Meta_20d),
      },
    ],
    colors: ["#EA580C", "#004899", "#10B981"],
    stroke: { width: [0, 3, 2.5], dashArray: [0, 0, 4] },
    labels: evol.map((r) => r.Mes_Str),
    xaxis: {
      labels: { rotate: -35, style: { fontSize: "10px", colors: "#475569" } },
    },
    yaxis: [
      {
        title: { text: "Pólizas / Gestor", style: { color: "#C2410C" } },
        min: 0,
        max: 480,
      },
      {
        opposite: true,
        title: { text: "Porcentaje (%)", style: { color: "#004899" } },
        min: 0,
        max: 75,
      },
      {
        opposite: true,
        show: false,
        min: 0,
        max: 75,
      },
    ],
    grid: { borderColor: "#E2E8F0", strokeDashArray: 3 },
    legend: { position: "top", labels: { colors: "#1E293B" } },
    tooltip: { theme: "light" },
  };
  if (chartC2Break) chartC2Break.destroy();
  chartC2Break = new ApexCharts(
    document.querySelector("#chart-c2-break"),
    breakOptions
  );
  chartC2Break.render();
}

function onCaso2SimInput() {
  document.getElementById("c2-sim-days-val").textContent = `${document.getElementById("c2-sim-days").value} días`;
  document.getElementById("c2-sim-ai-val").textContent = `${document.getElementById("c2-sim-ai").value}%`;
  document.getElementById("c2-sim-human-val").textContent = `${document.getElementById("c2-sim-human").value}%`;
}

async function fetchCaso2Priorizacion() {
  const gestor = document.getElementById("c2-filter-gestor").value;
  const ramo = document.getElementById("c2-filter-ramo").value;
  const onlyRisk = document.getElementById("c2-filter-risk").checked;
  const simDays = document.getElementById("c2-sim-days").value;
  const simAi = document.getElementById("c2-sim-ai").value;
  const simHuman = document.getElementById("c2-sim-human").value;

  const badge = document.getElementById("c2-loading-badge");
  badge.classList.remove("hidden");

  try {
    const url = `/api/caso2/priorizacion?gestor=${encodeURIComponent(gestor)}&ramo=${encodeURIComponent(ramo)}&only_at_risk=${onlyRisk}&limit=100&target_contact_days=${simDays}&ai_closure_pct=${simAi}&human_uplift_pct=${simHuman}`;
    const res = await fetch(url);
    const data = await res.json();
    caso2PrioState = data;
    renderCaso2PrioAndRoi(data);
  } catch (err) {
    console.error("Error en priorización Caso 2:", err);
  } finally {
    badge.classList.add("hidden");
  }
}

function renderCaso2PrioAndRoi(data) {
  const sm = data.simulation_metrics;
  const lanes = data.lanes_summary;

  // Actualizar KPIs ROI
  document.getElementById("kpi-c2-roi-usd").textContent = `+${fmtUSD(sm.impacto_economico_anual_usd, 0)}`;
  document.getElementById("kpi-c2-renov-global").textContent = `${sm.tasa_renovacion_global_simulada_pct.toFixed(2)}%`;
  document.getElementById("kpi-c2-renov-delta").textContent = `+${sm.puntos_retencion_global_ganados_pp.toFixed(2)} pp vs ${sm.tasa_renovacion_global_actual_pct.toFixed(2)}%`;
  document.getElementById("kpi-c2-polizas-rec").textContent = `+${fmtInt(sm.polizas_recuperadas_anual)}`;
  document.getElementById("kpi-c2-manual-rate").textContent = `Manual: ${sm.tasa_renovacion_manual_actual_pct.toFixed(1)}% → ${sm.tasa_renovacion_manual_simulada_pct.toFixed(1)}%`;
  document.getElementById("kpi-c2-cap-pct").textContent = `${sm.utilizacion_capacidad_humana_pct.toFixed(1)}%`;
  document.getElementById("kpi-c2-cap-calls").textContent = `${fmtInt(sm.llamadas_humanas_requeridas_mes_3carriles)} / ${fmtInt(sm.capacidad_mensual_5_gestores_llamadas)} llam/mes`;

  // Actualizar tarjetas de los 3 carriles
  if (lanes && lanes.length >= 3) {
    document.getElementById("lane1-roi-badge").textContent = `+${fmtUSD(lanes[0].Impacto_Comisiones_Anual_USD, 0)} USD/año`;
    document.getElementById("lane2-pol-badge").innerHTML = `Retención por timing: <strong>+${fmtInt(lanes[1].Polizas_Adicionales_Retenidas_Anual)} pól/año</strong>`;
    document.getElementById("lane2-roi-badge").textContent = `+${fmtUSD(lanes[1].Impacto_Comisiones_Anual_USD, 0)} USD/año`;
    document.getElementById("lane3-pol-badge").innerHTML = `Negociación humana: <strong>+${fmtInt(lanes[2].Polizas_Adicionales_Retenidas_Anual)} pól/año</strong>`;
    document.getElementById("lane3-roi-badge").textContent = `+${fmtUSD(lanes[2].Impacto_Comisiones_Anual_USD, 0)} USD/año`;
  }

  // Renderizar Gráfico de Barras ROI
  renderCaso2RoiBarsChart(lanes, sm);

  // Renderizar Tabla de Bandeja Priorizada
  const f = data.filters;
  document.getElementById("c2-table-summary-text").innerHTML =
    `Mostrando top <strong>${data.policies.length}</strong> de <strong>${fmtInt(f.total_matching_policies)}</strong> pólizas filtradas · Valor en Riesgo acumulado en filtro: <strong>${fmtUSD(f.total_matching_risk_usd, 2)} USD</strong>`;

  const tbody = document.getElementById("table-c2-policies-body");
  tbody.innerHTML = "";

  data.policies.forEach((p) => {
    const tr = document.createElement("tr");
    tr.className = "cursor-pointer hover:bg-slate-50 transition";
    tr.onclick = () => openCopilotModal(p.poliza);

    const changeColor =
      p.cambio_prima_pct >= 10
        ? "text-red-600 font-bold"
        : p.cambio_prima_pct > 0
        ? "text-amber-600 font-semibold"
        : "text-emerald-600 font-medium";

    tr.innerHTML = `
      <td class="text-center font-mono text-xs text-slate-500">#${p.ranking}</td>
      <td class="font-bold text-[#004899] underline decoration-blue-300">${p.poliza}</td>
      <td class="text-center"><span class="cp-pill cp-pill-blue">${p.gestor}</span></td>
      <td>
        <div class="font-semibold text-slate-800">${p.cliente_id}</div>
        <div class="text-[11px] text-slate-500 font-medium">${p.telefono}</div>
      </td>
      <td>
        <div class="font-medium text-slate-800">${p.ramo}</div>
        <div class="text-[11px] text-slate-500 font-medium">${p.segmento}</div>
      </td>
      <td class="text-xs text-slate-700">${p.aseguradora}</td>
      <td class="text-center text-xs font-mono text-slate-600 font-medium">${p.fecha_vencimiento}</td>
      <td class="text-right text-xs text-slate-600 tabular-nums">${fmtUSD(p.prima_anterior_usd, 2)}</td>
      <td class="text-right font-semibold text-slate-900 tabular-nums">${fmtUSD(p.prima_renovacion_usd, 2)}</td>
      <td class="text-right text-xs tabular-nums ${changeColor}">${p.cambio_prima_pct >= 0 ? "+" : ""}${p.cambio_prima_pct.toFixed(1)}%</td>
      <td class="text-right">
        <span class="cp-pill cp-pill-rose tabular-nums">${p.p_fuga_pct.toFixed(1)}%</span>
      </td>
      <td class="text-right font-extrabold text-[#002D62] text-sm tabular-nums">${fmtUSD(p.valor_en_riesgo_usd, 2)}</td>
      <td class="text-center">
        <button onclick="event.stopPropagation(); openCopilotModal('${p.poliza}')" class="cp-btn-primary px-2.5 py-1 text-xs">
          <svg class="w-3.5 h-3.5 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>
          </svg>
          <span>Copiloto IA</span>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderCaso2RoiBarsChart(lanes, sm) {
  const categories = [
    "Carril 1: Zero-Touch Digital",
    "Carril 2: Bot IA (T-25 días)",
    "Carril 3: Gestores + Copiloto",
    "TOTAL RESCATADO ANUAL",
  ];
  const values = [
    Math.round(lanes[0]?.Impacto_Comisiones_Anual_USD || 0),
    Math.round(lanes[1]?.Impacto_Comisiones_Anual_USD || 0),
    Math.round(lanes[2]?.Impacto_Comisiones_Anual_USD || 0),
    Math.round(sm.impacto_economico_anual_usd || 0),
  ];

  const options = {
    chart: {
      type: "bar",
      height: 285,
      toolbar: { show: false },
      background: "transparent",
      foreColor: "#1E293B",
    },
    theme: { mode: "light" },
    plotOptions: {
      bar: {
        horizontal: true,
        borderRadius: 4,
        barHeight: "65%",
        distributed: true,
      },
    },
    colors: ["#0284C7", "#10B981", "#F59E0B", "#004899"],
    dataLabels: {
      enabled: true,
      formatter: (v) => `+${fmtUSD(v, 0)} USD`,
      style: { fontSize: "11px", fontWeight: "bold", colors: ["#ffffff"] },
    },
    series: [{ name: "Comisiones Rescatadas (USD/año)", data: values }],
    xaxis: {
      categories: categories,
      labels: {
        formatter: (v) => fmtUSD(v, 0),
        style: { colors: "#475569", fontSize: "10px" },
      },
    },
    yaxis: {
      labels: { style: { colors: "#002D62", fontSize: "11px", fontWeight: 700 } },
    },
    grid: { borderColor: "#E2E8F0", strokeDashArray: 3 },
    legend: { show: false },
    tooltip: {
      theme: "light",
      y: { formatter: (v) => `+${fmtUSD(v, 2)} USD / año` },
    },
  };

  if (chartC2RoiBars) {
    chartC2RoiBars.updateOptions(options);
  } else {
    chartC2RoiBars = new ApexCharts(
      document.querySelector("#chart-c2-roi-bars"),
      options
    );
    chartC2RoiBars.render();
  }
}

// ---------------------------------------------------------------------------
// MODAL COPILOTO IA (CASO 2)
// ---------------------------------------------------------------------------

async function openCopilotModal(polizaId) {
  const modal = document.getElementById("copilot-modal");
  modal.classList.remove("hidden");

  try {
    const res = await fetch(`/api/caso2/copiloto/${encodeURIComponent(polizaId)}`);
    const data = await res.json();

    document.getElementById("cop-title").textContent = `Póliza ${data.poliza} · ${data.ramo} (${data.segmento})`;
    document.getElementById("cop-subtitle").textContent = `Cliente: ${data.cliente_id} · Tel: ${data.telefono} · Gestor: ${data.gestor}`;
    document.getElementById("cop-pfuga").textContent = `${data.p_fuga_pct.toFixed(1)}%`;
    document.getElementById("cop-risk-usd").textContent = fmtUSD(data.comision_en_riesgo_usd, 2);
    document.getElementById("cop-prima-ren").textContent = fmtUSD(data.prima_renovacion_usd, 2);
    document.getElementById("cop-cambio-pct").textContent = `${data.cambio_prima_pct >= 0 ? "+" : ""}${data.cambio_prima_pct.toFixed(1)}% (Ant: ${fmtUSD(data.prima_anterior_usd, 2)})`;
    document.getElementById("cop-prima-alt").textContent = fmtUSD(data.prima_alternativa_sugerida_usd, 2);
    document.getElementById("cop-ahorro").textContent = `Ahorro: ${fmtUSD(data.ahorro_potencial_cliente_usd, 2)} (${data.aseguradora_alternativa})`;

    const cleanScript = data.argumento_retencion
      .replace(/\*\*(.*?)\*\*/g, "<strong class='text-[#002D62]'>$1</strong>")
      .replace(/`(.*?)`/g, "<code class='bg-blue-100 text-[#004899] font-bold px-1 rounded'>$1</code>");
    document.getElementById("cop-script-text").innerHTML = cleanScript;

    const ul = document.getElementById("cop-risk-factors");
    ul.innerHTML = "";
    data.factores_riesgo.forEach((f) => {
      const li = document.createElement("li");
      li.textContent = f;
      ul.appendChild(li);
    });
    const liStrat = document.createElement("li");
    liStrat.innerHTML = `<strong class="text-[#004899]">Estrategia Recomendada:</strong> ${data.estrategia_precio}`;
    ul.appendChild(liStrat);

    const qBody = document.getElementById("cop-quotes-tbody");
    qBody.innerHTML = "";
    data.cotizaciones.forEach((q, idx) => {
      const tr = document.createElement("tr");
      if (idx === 2) {
        tr.className = "bg-emerald-50/70 font-semibold text-emerald-950";
      }
      tr.innerHTML = `
        <td class="text-slate-800">${q["Opción"]}</td>
        <td class="text-[#004899] font-medium">${q["Aseguradora"]}</td>
        <td class="text-right font-bold text-slate-900 tabular-nums">${fmtUSD(q["Prima Anual (USD)"], 2)}</td>
        <td class="text-right text-slate-600 tabular-nums">${q["Variación vs Anterior"]}</td>
        <td class="text-right font-bold text-emerald-600 tabular-nums">${fmtUSD(q["Ahorro vs Cotización Base (USD)"], 2)}</td>
        <td class="text-right text-slate-900 font-semibold tabular-nums">${fmtUSD(q["Comisión Capesa (USD)"], 2)}</td>
      `;
      qBody.appendChild(tr);
    });
  } catch (err) {
    console.error("Error abriendo Copiloto IA:", err);
  }
}

function closeCopilotModal() {
  document.getElementById("copilot-modal").classList.add("hidden");
}

function copyCopilotScript() {
  const txt = document.getElementById("cop-script-text").innerText;
  navigator.clipboard.writeText(txt);
  const btnText = document.getElementById("btn-copy-text");
  if (btnText) btnText.textContent = "¡Copiado!";
  setTimeout(() => {
    if (btnText) btnText.textContent = "Copiar Guion";
  }, 1800);
}

function exportCaso2Excel() {
  window.location.href = "/api/exportar/caso2";
}

// Cerrar modal con tecla Escape
window.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeCopilotModal();
});

// Inicializar la aplicación cargando Caso 1 al arranque
document.addEventListener("DOMContentLoaded", () => {
  fetchCaso1Data();
});
