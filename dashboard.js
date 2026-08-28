/* ==========================================================================
   dashboard.js — carrega /api/dashboard e renderiza KPIs, gráficos e
   as listas de produtos mais vendidos / estoque baixo.
   ========================================================================== */
App.pages.dashboard = {
  lastData: null,

  onEnter() { this.load(); },
  onPeriodChange() { if (App.currentPage === "dashboard") this.load(); },

  async load() {
    this._renderKpiSkeleton();
    try {
      const data = await App.api(`/api/dashboard?${App.periodQuery()}`);
      this.lastData = data;
      this._renderKpis(data);
      AppCharts.revenueChart("chartRevenue", data.revenue_series.labels, data.revenue_series.faturamento, data.revenue_series.lucro);
      AppCharts.categoryChart("chartCategory", data.category_distribution.labels, data.category_distribution.valores);
      this._renderTopProducts(data.top_products);
      this._renderLowStock(data.estoque_baixo);
    } catch {
      document.getElementById("kpiGrid").innerHTML =
        `<div class="state-block field-full">Não foi possível carregar o dashboard.</div>`;
    }
  },

  refreshChartsTheme() { if (this.lastData) this.load(); },

  _renderKpiSkeleton() {
    document.getElementById("kpiGrid").innerHTML = Array(6).fill(
      `<div class="kpi-card"><div class="skeleton" style="height:11px;width:60%;margin-bottom:10px;"></div><div class="skeleton" style="height:22px;width:80%;"></div></div>`
    ).join("");
  },

  _renderKpis(d) {
    const cards = [
      { label: "Faturamento", value: App.fmtMoney(d.faturamento), sub: `${d.num_vendas} vendas` },
      { label: "Lucro", value: App.fmtMoney(d.lucro), sub: `Margem média ${d.margem_media.toFixed(1)}%` },
      { label: "Ticket médio", value: App.fmtMoney(d.ticket_medio), sub: `${d.unidades_vendidas} unidades vendidas` },
      { label: "Estoque atual", value: d.estoque_total, sub: App.fmtMoney(d.valor_estoque_custo) + " em custo" },
      { label: "Estoque baixo", value: d.estoque_baixo_qtd, sub: "produtos abaixo do mínimo", cls: d.estoque_baixo_qtd ? "warn" : "" },
      { label: "Sem estoque", value: d.sem_estoque_qtd, sub: "produtos zerados", cls: d.sem_estoque_qtd ? "danger" : "" },
    ];
    document.getElementById("kpiGrid").innerHTML = cards.map((c) => `
      <div class="kpi-card ${c.cls || ""}">
        <div class="kpi-label">${c.label}</div>
        <div class="kpi-value">${c.value}</div>
        <div class="kpi-sub">${c.sub}</div>
      </div>`).join("");
  },

  _renderTopProducts(items) {
    const el = document.getElementById("topProductsList");
    if (!items.length) {
      el.innerHTML = `<div class="state-block"><span class="state-title">Nenhuma venda no período</span></div>`;
      return;
    }
    el.innerHTML = `<table><thead><tr><th>Produto</th><th class="num">Qtd</th><th class="num">Faturamento</th></tr></thead><tbody>` +
      items.map((p) => `
        <tr>
          <td>${App.escapeHtml(p.produto)}</td>
          <td class="num">${p.quantidade}</td>
          <td class="num">${App.fmtMoney(p.faturamento)}</td>
        </tr>`).join("") + `</tbody></table>`;
  },

  _renderLowStock(items) {
    const el = document.getElementById("lowStockList");
    if (!items.length) {
      el.innerHTML = `<div class="state-block"><span class="state-title">Estoque saudável</span>Nenhum produto abaixo do mínimo.</div>`;
      return;
    }
    el.innerHTML = `<table><thead><tr><th>Produto</th><th class="num">Estoque</th><th class="num">Mínimo</th></tr></thead><tbody>` +
      items.map((p) => `
        <tr>
          <td>${App.escapeHtml(p.nome)}</td>
          <td class="num">${p.estoque_atual}</td>
          <td class="num">${p.estoque_minimo}</td>
        </tr>`).join("") + `</tbody></table>`;
  },
};

// ---------------------------------------------------------------------- //
// Relatórios (produtos mais rentáveis) reaproveita o filtro de período
// ---------------------------------------------------------------------- //
App.pages.relatorios = {
  onEnter() { this.load(); },
  onPeriodChange() { if (App.currentPage === "relatorios") this.load(); },

  async load() {
    try {
      const data = await App.api(`/api/reports?${App.periodQuery()}`);
      this._renderHighlights(data);
      this._renderTable(data.itens || []);
    } catch { /* toast já disparado pelo App.api */ }
  },

  _renderHighlights(d) {
    const el = document.getElementById("profitabilityHighlights");
    if (!d.itens || !d.itens.length) {
      el.innerHTML = `<div class="state-block field-full"><span class="state-title">Sem vendas no período</span></div>`;
      return;
    }
    const items = [
      ["Mais vendido", d.mais_vendido], ["Mais lucrativo", d.mais_lucrativo],
      ["Maior margem", d.maior_margem], ["Menor margem", d.menor_margem],
      ["Maior faturamento", d.maior_faturamento], ["Maior giro de estoque", d.maior_giro],
    ];
    el.innerHTML = items.map(([label, val]) => `
      <div class="kpi-card">
        <div class="kpi-label">${label}</div>
        <div class="kpi-value" style="font-size:16px;">${App.escapeHtml(val || "—")}</div>
      </div>`).join("");
  },

  _renderTable(items) {
    const body = document.getElementById("reportsTableBody");
    if (!items.length) {
      body.innerHTML = `<tr><td colspan="6"><div class="state-block">Nenhum dado para o período selecionado.</div></td></tr>`;
      return;
    }
    body.innerHTML = items.map((i) => `
      <tr>
        <td>${App.escapeHtml(i.produto)}</td>
        <td class="num">${i.quantidade}</td>
        <td class="num">${App.fmtMoney(i.faturamento)}</td>
        <td class="num">${App.fmtMoney(i.lucro)}</td>
        <td class="num">${i.margem.toFixed(1)}%</td>
        <td class="num">${i.giro_estoque}</td>
      </tr>`).join("");
  },
};

document.getElementById("exportCsvBtn")?.addEventListener("click", () => {
  window.location.href = `/api/reports/export?${App.periodQuery()}`;
});
