/* ==========================================================================
   charts.js — helpers para criar/atualizar gráficos Chart.js com cores
   que respeitam o tema (claro/escuro) via CSS variables.
   ========================================================================== */
const AppCharts = {
  instances: {},

  _cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  },

  revenueChart(canvasId, labels, faturamento, lucro) {
    const ctx = document.getElementById(canvasId).getContext("2d");
    if (this.instances[canvasId]) this.instances[canvasId].destroy();

    this.instances[canvasId] = new Chart(ctx, {
      type: "line",
      data: {
        labels: labels.map((l) => App.fmtDate(l + " 00:00:00").slice(0, 5)),
        datasets: [
          {
            label: "Faturamento",
            data: faturamento,
            borderColor: this._cssVar("--accent"),
            backgroundColor: this._cssVar("--accent-soft"),
            tension: 0.3, fill: true, pointRadius: 2,
          },
          {
            label: "Lucro",
            data: lucro,
            borderColor: this._cssVar("--ink-faint"),
            borderDash: [4, 4],
            tension: 0.3, fill: false, pointRadius: 2,
          },
        ],
      },
      options: this._baseOptions(),
    });
  },

  categoryChart(canvasId, labels, valores) {
    const ctx = document.getElementById(canvasId).getContext("2d");
    if (this.instances[canvasId]) this.instances[canvasId].destroy();

    const palette = [
      this._cssVar("--accent"), this._cssVar("--warn"),
      this._cssVar("--danger"), this._cssVar("--ink-faint"),
      this._cssVar("--accent-strong"),
    ];

    this.instances[canvasId] = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: labels.length ? labels : ["Sem dados"],
        datasets: [{
          data: valores.length ? valores : [1],
          backgroundColor: labels.length ? palette : [this._cssVar("--border")],
          borderWidth: 0,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: "bottom", labels: { color: this._cssVar("--ink-soft"), font: { size: 11 }, boxWidth: 10 } } },
      },
    });
  },

  _baseOptions() {
    return {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { position: "bottom", labels: { color: this._cssVar("--ink-soft"), font: { size: 11 }, boxWidth: 10 } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: this._cssVar("--ink-faint"), font: { size: 10.5 } } },
        y: { grid: { color: this._cssVar("--border") }, ticks: { color: this._cssVar("--ink-faint"), font: { size: 10.5 } } },
      },
    };
  },
};
