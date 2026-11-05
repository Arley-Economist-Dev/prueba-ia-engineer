/**
 * Cliente SPA de Alto Rendimiento — Casa Pellas · AI Executive Decision Suite
 * Renderiza en cliente (60fps) con ApexCharts y Plotly.js en paleta corporativa oficial (Light Theme).
 */

let caso1State = null;
let caso2DiagState = null;
let caso2PrioState = null;

// Instancias de ApexCharts (Skill: data-visualization)
let chartC1Bars = null;
let chartC1Donut = null;
let chartC1Trajectory = null;
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
  // Regla Tufte Data-to-Ink: Ordenar de mayor a menor según Pedido Sugerido
  const sorted = [...models].sort(
    (a, b) => b.Pedido_Sugerido_Oct26 - a.Pedido_Sugerido_Oct26
  );
  const categories = sorted.map((m) => m.Modelo);

  const sPedidoData = sorted.map((m) => {
    let minLot = 0;
    if (m.Lote_Min_Mult) {
      const parts = String(m.Lote_Min_Mult).split("/");
      minLot = parseInt(parts[0], 10) || 0;
    }
    return {
      x: m.Modelo,
      y: m.Pedido_Sugerido_Oct26,
      goals:
        minLot > 0
          ? [
              {
                name: "Lote Mínimo",
                value: minLot,
                strokeWidth: 4,
                strokeHeight: 12,
                strokeColor: "#FF7C5C", // Resaltado ámbar/coral para límites críticos
              },
            ]
          : [],
    };
  });

  const sInv = sorted.map((m) => m.Inv_30Sep);
  const sTrans = sorted.map((m) => m.Transito_Oct26_Ene27);

  const options = {
    chart: {
      type: "bar",
      height: 375,
      toolbar: { show: false },
      background: "transparent",
      foreColor: "#FFFFFFB3",
      animations: {
        enabled: true,
        easing: "easeinout",
        speed: 400,
        dynamicAnimation: { enabled: false },
      },
    },
    theme: { mode: "dark" },
    plotOptions: {
      bar: {
        horizontal: true,
        barHeight: "72%",
        borderRadius: 3,
      },
    },
    dataLabels: {
      enabled: true,
      style: { fontSize: "10px", colors: ["#FFFFFF"], fontFamily: "Inter, sans-serif" },
      formatter: (val) => (val > 0 ? `${val}` : ""),
    },
    stroke: { show: true, width: 1, colors: ["#1C376C"] },
    colors: ["#18489B", "#FFFFFF", "#38BDF8"],
    series: [
      { name: "Pedido Recomendado Oct-26", data: sPedidoData },
      { name: "Inventario Actual (30/Sep)", data: sInv },
      { name: "En Tránsito (Oct26–Ene27)", data: sTrans },
    ],
    xaxis: {
      categories: categories,
      labels: {
        style: { colors: "#FFFFFFB3", fontSize: "11px", fontFamily: "Inter, sans-serif" },
      },
      axisBorder: { color: "rgba(255, 255, 255, 0.08)" },
      axisTicks: { color: "rgba(255, 255, 255, 0.08)" },
    },
    yaxis: {
      labels: {
        style: { colors: "#FFFFFF", fontSize: "11px", fontWeight: 600, fontFamily: "Inter, sans-serif" },
      },
    },
    grid: {
      borderColor: "rgba(255, 255, 255, 0.08)",
      xaxis: { lines: { show: false } }, // Cero líneas verticales superfluas
      yaxis: { lines: { show: true } },
    },
    legend: {
      position: "top",
      horizontalAlign: "left",
      labels: { colors: "#FFFFFFB3" },
      fontFamily: "Inter, sans-serif",
    },
    tooltip: {
      theme: "dark",
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
  // Regla Tufte Estricta: Cero gráficos de pastel con más de 4 categorías
  const activeModels = [...models]
    .filter((m) => m.Margen_Bruto_Esperado_USD > 0)
    .sort((a, b) => b.Margen_Bruto_Esperado_USD - a.Margen_Bruto_Esperado_USD);

  const top3 = activeModels.slice(0, 3);
  const others = activeModels.slice(3);

  const labels = top3.map((m) => m.Modelo);
  const series = top3.map((m) => Math.round(m.Margen_Bruto_Esperado_USD));

  if (others.length > 0) {
    labels.push("Otros Modelos");
    const otherSum = others.reduce((acc, m) => acc + Math.round(m.Margen_Bruto_Esperado_USD), 0);
    series.push(otherSum);
  }

  const totalMargen = series.reduce((a, b) => a + b, 0);

  const options = {
    chart: {
      type: "donut",
      height: 375,
      background: "transparent",
      foreColor: "#FFFFFFB3",
      animations: {
        enabled: true,
        easing: "easeinout",
        speed: 400,
        dynamicAnimation: { enabled: false },
      },
    },
    theme: { mode: "dark" },
    labels: labels,
    series: series,
    colors: ["#FFFFFF", "#18489B", "#38BDF8", "#E0A96D"],
    stroke: { colors: ["#17217D"], width: 2 },
    dataLabels: {
      enabled: true,
      formatter: (val) => `${val.toFixed(1)}%`,
      style: { fontSize: "11px", fontWeight: "bold", fontFamily: "Inter, sans-serif" },
    },
    plotOptions: {
      pie: {
        donut: {
          size: "68%",
          labels: {
            show: true,
            name: { show: true, color: "#FFFFFFB3", fontSize: "12px", fontFamily: "Inter, sans-serif" },
            value: {
              show: true,
              color: "#FFFFFF",
              fontSize: "18px",
              fontWeight: 800,
              fontFamily: "Inter, sans-serif",
              formatter: (v) => fmtUSD(v, 0),
            },
            total: {
              show: true,
              label: "Margen Bruto Total",
              color: "#FFFFFFB3",
              fontFamily: "Inter, sans-serif",
              formatter: () => fmtUSD(totalMargen, 0),
            },
          },
        },
      },
    },
    legend: { position: "bottom", labels: { colors: "#FFFFFFB3" }, fontFamily: "Inter, sans-serif" },
    tooltip: {
      theme: "dark",
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
  let safetyStockTarget = 0;

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
    safetyStockTarget = Math.round(
      caso1State.models.reduce((acc, m) => acc + (m.Stock_Seguridad_Objetivo || 0), 0)
    );
  } else {
    rows = raw.filter((r) => r.Modelo === sel).sort((a, b) => a.Orden_Mes - b.Orden_Mes);
    const mFound = caso1State.models.find((m) => m.Modelo === sel);
    safetyStockTarget = mFound ? Math.round(mFound.Stock_Seguridad_Objetivo) : 0;
  }

  const xLabels = rows.map((r) => {
    const raw = r.Etiqueta_Mes || "";
    if (raw.includes("Sep 2026")) return "Sep-26";
    if (raw.includes("Oct 2026")) return "Oct-26";
    if (raw.includes("Nov 2026")) return "Nov-26";
    if (raw.includes("Dic 2026")) return "Dic-26";
    if (raw.includes("Ene 2027")) return "Ene-27";
    if (raw.includes("Feb 2027")) return "Feb-27";
    if (raw.includes("Mar 2027")) return "Mar-27";
    if (raw.includes("Abr 2027")) return "Abr-27";
    return raw;
  });
  const yInv = rows.map((r) => Math.round(r.Inventario_Cierre_Uds));
  const yDem = rows.map((r) => Math.round(r.Demanda_Mensual_Uds));
  const ySafety = rows.map(() => safetyStockTarget);

  const options = {
    chart: {
      type: "area",
      height: 360,
      toolbar: { show: false },
      background: "transparent",
      foreColor: "#FFFFFFB3",
      animations: {
        enabled: true,
        easing: "easeinout",
        speed: 400,
        dynamicAnimation: { enabled: false },
      },
    },
    theme: { mode: "dark" },
    stroke: { curve: "smooth", width: [3, 2.5, 2] },
    colors: ["#FFFFFF", "#FF7C5C", "#38BDF8"],
    fill: {
      type: ["gradient", "solid", "solid"],
      gradient: {
        shade: "dark",
        type: "vertical",
        shadeIntensity: 0.5,
        opacityFrom: 0.35,
        opacityTo: 0.05,
      },
    },
    series: [
      { name: "Inventario Proyectado al Cierre", data: yInv, type: "area" },
      { name: "Línea de Stock de Seguridad Recomendada", data: ySafety, type: "line" },
      { name: "Demanda Mensual Planificada", data: yDem, type: "line" },
    ],
    markers: {
      size: [5, 0, 4],
      strokeColors: "#17217D",
      strokeWidth: 2,
    },
    xaxis: {
      categories: xLabels,
      labels: {
        rotate: 0,
        style: { colors: "#FFFFFFB3", fontSize: "11px", fontFamily: "Inter, sans-serif" },
      },
      axisBorder: { color: "rgba(255, 255, 255, 0.08)" },
      axisTicks: { color: "rgba(255, 255, 255, 0.08)" },
    },
    yaxis: {
      title: { text: "Unidades", style: { color: "#FFFFFFB3", fontSize: "11px" } },
      labels: {
        style: { colors: "#FFFFFFB3", fontSize: "11px", fontFamily: "Inter, sans-serif" },
      },
    },
    grid: {
      borderColor: "rgba(255, 255, 255, 0.08)",
      xaxis: { lines: { show: false } },
      padding: { left: 15, right: 15 },
    },
    legend: {
      position: "top",
      horizontalAlign: "left",
      labels: { colors: "#FFFFFFB3" },
      fontFamily: "Inter, sans-serif",
    },
    tooltip: {
      theme: "dark",
      y: { formatter: (val) => `${val} unidades` },
    },
  };

  if (chartC1Trajectory) {
    chartC1Trajectory.updateOptions(options);
  } else {
    chartC1Trajectory = new ApexCharts(document.querySelector("#chart-c1-trajectory"), options);
    chartC1Trajectory.render();
  }
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

  const palette = ["#FFFFFF", "#18489B", "#38BDF8", "#FF7C5C", "#E0A96D", "#94A3B8"];
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
    paper_bgcolor: "transparent",
    plot_bgcolor: "transparent",
    font: { color: "#FFFFFFB3", family: "Inter, sans-serif", size: 11 },
    margin: { l: 45, r: 20, t: 25, b: 55 },
    legend: { orientation: "h", y: 1.15, x: 0 },
    xaxis: { gridcolor: "rgba(255, 255, 255, 0.08)", color: "#FFFFFFB3" },
    yaxis: { gridcolor: "rgba(255, 255, 255, 0.08)", color: "#FFFFFFB3", title: yAxisTitle },
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

function formatMonthStr(isoStr) {
  if (!isoStr) return "";
  const parts = String(isoStr).split("-");
  if (parts.length < 2) return isoStr;
  const monthIdx = parseInt(parts[1], 10) - 1;
  const shortMonths = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
  const mName = shortMonths[monthIdx] || parts[1];
  const yr = parts[0].slice(-2);
  return `${mName}-${yr}`;
}

function renderCaso2DiagnosticCharts(diag) {
  // 1. Curva de Retención según Anticipación de Contacto
  const manualCurve = diag.anticipation_curve.filter(
    (r) => r["Forma de pago"] === "Manual"
  );
  
  const cleanAntCategory = (cat) => {
    if (!cat) return "";
    if (cat.includes("Sin contacto")) return "Sin contacto";
    if (cat.includes("<0") || cat.includes("Post")) return "< 0 días";
    if (cat.includes("0 a 3") || cat.includes("1 - 3") || cat.includes("Crítico")) return "0 a 3 días";
    if (cat.includes("4 a 9") || cat.includes("Tardío")) return "4 a 9 días";
    if (cat.includes("10 a 19") || cat.includes("Moderado")) return "10 a 19 días";
    if (cat.includes(">=20") || cat.includes("20") || cat.includes("meta")) return "≥ 20 días";
    return cat.replace(/^\d+\.\s*/, "");
  };

  const antCategories = manualCurve.map((r) => cleanAntCategory(r.Tramo_Anticipacion));
  const antValues = manualCurve.map((r) => r.Tasa_Renovacion_Pct);

  const idxMeta = antCategories.findIndex((c) => c.includes("≥ 20"));
  const idxCrit = antCategories.findIndex((c) => c.includes("0 a 3"));

  const antOptions = {
    chart: {
      type: "line",
      height: 300,
      toolbar: { show: false },
      background: "transparent",
      foreColor: "#FFFFFFB3",
      animations: {
        enabled: true,
        easing: "easeinout",
        speed: 400,
        dynamicAnimation: { enabled: false },
      },
    },
    theme: { mode: "dark" },
    stroke: { curve: "smooth", width: 3.5 },
    colors: ["#38BDF8"],
    series: [
      {
        name: "Tasa de Renovación Manual (%)",
        data: antValues,
      },
    ],
    markers: {
      size: 5,
      strokeColors: "#17217D",
      strokeWidth: 2,
    },
    annotations: {
      points: [
        idxMeta >= 0
          ? {
              x: antCategories[idxMeta],
              y: antValues[idxMeta],
              marker: {
                size: 7,
                fillColor: "#10B981",
                strokeColor: "#FFFFFF",
                radius: 2,
              },
              label: {
                borderColor: "#10B981",
                offsetY: -10,
                style: {
                  color: "#FFFFFF",
                  background: "#065F46",
                  fontSize: "10px",
                  fontWeight: 700,
                  fontFamily: "Inter, sans-serif",
                },
                text: `Meta T-20d: ${antValues[idxMeta].toFixed(1)}%`,
              },
            }
          : null,
        idxCrit >= 0
          ? {
              x: antCategories[idxCrit],
              y: antValues[idxCrit],
              marker: {
                size: 7,
                fillColor: "#FF7C5C",
                strokeColor: "#FFFFFF",
              },
              label: {
                borderColor: "#FF7C5C",
                offsetY: 22,
                style: {
                  color: "#FFFFFF",
                  background: "#7C2D12",
                  fontSize: "10px",
                  fontWeight: 700,
                  fontFamily: "Inter, sans-serif",
                },
                text: `Crítico (0-3d): ${antValues[idxCrit].toFixed(1)}%`,
              },
            }
          : null,
      ].filter(Boolean),
    },
    xaxis: {
      categories: antCategories,
      labels: {
        style: { colors: "#FFFFFFB3", fontSize: "10px", fontFamily: "Inter, sans-serif" },
        rotate: 0,
      },
      axisBorder: { color: "rgba(255, 255, 255, 0.08)" },
      axisTicks: { color: "rgba(255, 255, 255, 0.08)" },
    },
    yaxis: {
      max: 85,
      min: 0,
      title: { text: "% Renovación", style: { color: "#FFFFFFB3", fontSize: "11px" } },
      labels: {
        style: { colors: "#FFFFFFB3", fontSize: "10px", fontFamily: "Inter, sans-serif" },
        formatter: (v) => `${v.toFixed(0)}%`,
      },
    },
    grid: {
      borderColor: "rgba(255, 255, 255, 0.08)",
      xaxis: { lines: { show: false } },
      padding: { left: 10, right: 10 },
    },
    legend: { show: false },
    tooltip: {
      theme: "dark",
      y: { formatter: (v) => `${v.toFixed(1)}% de Renovación` },
    },
  };
  if (chartC2Anticipation) chartC2Anticipation.destroy();
  chartC2Anticipation = new ApexCharts(
    document.querySelector("#chart-c2-anticipation"),
    antOptions
  );
  chartC2Anticipation.render();

  // 2. Distribución de Carga Operativa (Donut de una Sola Capa: 12.6% Domiciliado/Financiado vs 87.4% Manual)
  const pay = diag.payment_efficiency;
  const autoCalls = pay
    .filter((r) => r["Forma de pago"] === "Domiciliado" || r["Forma de pago"] === "Financiado")
    .reduce((sum, r) => sum + r.Llamadas_Bitacora, 0);
  const manualCalls = pay
    .filter((r) => r["Forma de pago"] === "Manual")
    .reduce((sum, r) => sum + r.Llamadas_Bitacora, 0);
  const totalCalls = autoCalls + manualCalls;
  const autoPct = (autoCalls / totalCalls) * 100.0;

  const payOptions = {
    chart: {
      height: 300,
      type: "donut",
      toolbar: { show: false },
      background: "transparent",
      foreColor: "#FFFFFFB3",
      animations: {
        enabled: true,
        easing: "easeinout",
        speed: 400,
        dynamicAnimation: { enabled: false },
      },
    },
    theme: { mode: "dark" },
    labels: [
      `Cobro Automático (${autoPct.toFixed(1)}% Ineficiente)`,
      `Manual (${(100 - autoPct).toFixed(1)}% Gestión Real)`,
    ],
    series: [autoCalls, manualCalls],
    colors: ["#FF7C5C", "#18489B"], // Resaltado coral para el 12.6% ineficiente vs azul corporativo
    stroke: { colors: ["#17217D"], width: 2 },
    dataLabels: {
      enabled: true,
      formatter: (v) => `${v.toFixed(1)}%`,
      style: { fontSize: "11px", fontWeight: "bold", fontFamily: "Inter, sans-serif" },
    },
    plotOptions: {
      pie: {
        donut: {
          size: "68%",
          labels: {
            show: true,
            name: { show: true, color: "#FFFFFFB3", fontSize: "11px", fontFamily: "Inter, sans-serif" },
            value: {
              show: true,
              color: "#FF7C5C",
              fontSize: "20px",
              fontWeight: 800,
              fontFamily: "Inter, sans-serif",
              formatter: () => `${autoPct.toFixed(1)}%`,
            },
            total: {
              show: true,
              label: "Llamadas Ineficientes",
              color: "#FFFFFFB3",
              fontFamily: "Inter, sans-serif",
              formatter: () => `${fmtInt(autoCalls)} llamadas`,
            },
          },
        },
      },
    },
    legend: { position: "bottom", labels: { colors: "#FFFFFFB3" }, fontFamily: "Inter, sans-serif" },
    tooltip: {
      theme: "dark",
      y: { formatter: (v) => `${fmtInt(v)} llamadas` },
    },
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
      foreColor: "#FFFFFFB3",
      animations: {
        enabled: true,
        easing: "easeinout",
        speed: 400,
        dynamicAnimation: { enabled: false },
      },
    },
    theme: { mode: "dark" },
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
    colors: ["#18489B", "#FFFFFF", "#FF7C5C"],
    stroke: { width: [0, 3, 2.5], dashArray: [0, 0, 4], curve: "smooth" },
    annotations: {
      xaxis: [
        {
          x: "2025-12",
          borderColor: "#FF7C5C",
          strokeDashArray: 3,
          label: {
            borderColor: "#FF7C5C",
            offsetY: 0,
            style: {
              color: "#FFFFFF",
              background: "#7C2D12",
              fontSize: "10px",
              fontWeight: "bold",
              fontFamily: "Inter, sans-serif",
            },
            text: "Salida G06/G07 (Dic-25)",
          },
        },
      ],
    },
    xaxis: {
      type: "category",
      categories: evol.map((r) => r.Mes_Str),
      labels: {
        rotate: 0,
        style: {
          fontSize: "10px",
          colors: "#FFFFFFB3",
          fontFamily: "Inter, sans-serif",
        },
        formatter: function (val) {
          const map = {
            "2025-09": "Sep-25",
            "2025-11": "Nov-25",
            "2026-01": "Ene-26",
            "2026-03": "Mar-26",
            "2026-05": "May-26",
            "2026-07": "Jul-26",
            "2026-09": "Sep-26",
          };
          return map[val] || "";
        },
      },
      axisBorder: { color: "rgba(255, 255, 255, 0.08)" },
      axisTicks: { color: "rgba(255, 255, 255, 0.08)" },
    },
    yaxis: [
      {
        title: { text: "Pólizas / Gestor", style: { color: "#FFFFFFB3", fontSize: "10px" } },
        min: 0,
        max: 480,
        labels: { style: { colors: "#FFFFFFB3", fontSize: "10px" } },
      },
      {
        opposite: true,
        title: { text: "Porcentaje (%)", style: { color: "#FFFFFF", fontSize: "10px" } },
        min: 0,
        max: 75,
        labels: { style: { colors: "#FFFFFFB3", fontSize: "10px" }, formatter: (v) => `${v.toFixed(0)}%` },
      },
      {
        opposite: true,
        show: false,
        min: 0,
        max: 75,
      },
    ],
    grid: {
      borderColor: "rgba(255, 255, 255, 0.08)",
      xaxis: { lines: { show: false } },
      padding: { left: 10, right: 15 },
    },
    legend: { position: "top", labels: { colors: "#FFFFFFB3" }, fontFamily: "Inter, sans-serif" },
    tooltip: {
      theme: "dark",
      x: {
        formatter: function (val) {
          const full = {
            "2025-09": "Sep 2025",
            "2025-10": "Oct 2025",
            "2025-11": "Nov 2025",
            "2025-12": "Dic 2025 (Salida G06/G07)",
            "2026-01": "Ene 2026",
            "2026-02": "Feb 2026",
            "2026-03": "Mar 2026",
            "2026-04": "Abr 2026",
            "2026-05": "May 2026",
            "2026-06": "Jun 2026",
            "2026-07": "Jul 2026",
            "2026-08": "Ago 2026",
            "2026-09": "Sep 2026",
          };
          return full[val] || val;
        },
      },
    },
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
  // Ordenado de mayor a menor con destaque en TOTAL RESCATADO ANUAL
  const items = [
    { name: "TOTAL RESCATADO ANUAL", value: Math.round(sm.impacto_economico_anual_usd || 0), isTotal: true },
    { name: "Carril 2: Bot IA (T-25 días)", value: Math.round(lanes[1]?.Impacto_Comisiones_Anual_USD || 0) },
    { name: "Carril 3: Gestores + Copiloto", value: Math.round(lanes[2]?.Impacto_Comisiones_Anual_USD || 0) },
    { name: "Carril 1: Zero-Touch Digital", value: Math.round(lanes[0]?.Impacto_Comisiones_Anual_USD || 0) },
  ].sort((a, b) => b.value - a.value);

  const categories = items.map((i) => i.name);
  const values = items.map((i) => i.value);
  const colors = items.map((i) =>
    i.isTotal
      ? "#FFFFFF"
      : i.name.includes("Carril 2")
      ? "#18489B"
      : i.name.includes("Carril 3")
      ? "#38BDF8"
      : "#E0A96D"
  );

  const options = {
    chart: {
      type: "bar",
      height: 285,
      toolbar: { show: false },
      background: "transparent",
      foreColor: "#FFFFFFB3",
      animations: {
        enabled: true,
        easing: "easeinout",
        speed: 400,
        dynamicAnimation: { enabled: false },
      },
    },
    theme: { mode: "dark" },
    plotOptions: {
      bar: {
        horizontal: true,
        borderRadius: 4,
        barHeight: "65%",
        distributed: true,
      },
    },
    colors: colors,
    dataLabels: {
      enabled: true,
      formatter: (v) => `+${fmtUSD(v, 0)} USD`,
      style: {
        fontSize: "11px",
        fontWeight: "bold",
        colors: ["#17217D"],
        fontFamily: "Inter, sans-serif",
      },
    },
    series: [{ name: "Comisiones Rescatadas (USD/año)", data: values }],
    xaxis: {
      categories: categories,
      labels: {
        formatter: (v) => fmtUSD(v, 0),
        style: { colors: "#FFFFFFB3", fontSize: "10px", fontFamily: "Inter, sans-serif" },
      },
      axisBorder: { color: "rgba(255, 255, 255, 0.08)" },
      axisTicks: { color: "rgba(255, 255, 255, 0.08)" },
    },
    yaxis: {
      labels: {
        style: {
          colors: "#FFFFFF",
          fontSize: "11px",
          fontWeight: 700,
          fontFamily: "Inter, sans-serif",
        },
      },
    },
    grid: {
      borderColor: "rgba(255, 255, 255, 0.08)",
      xaxis: { lines: { show: false } },
      padding: { left: 10, right: 15 },
    },
    legend: { show: false },
    tooltip: {
      theme: "dark",
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
