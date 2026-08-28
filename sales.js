/* ==========================================================================
   sales.js — tela de PDV (nova venda) e histórico de vendas
   ========================================================================== */
App.pages.vendas = {
  products: [],
  sales: [],

  onEnter() {
    this._loadProducts();
    this._loadSales();
  },

  async _loadProducts() {
    const select = document.getElementById("pdvProduct");
    select.innerHTML = `<option>Carregando…</option>`;
    try {
      this.products = (await App.api("/api/products")).filter((p) => p.ativo);
      if (!this.products.length) {
        select.innerHTML = `<option value="">Nenhum produto disponível</option>`;
        return;
      }
      select.innerHTML = this.products.map((p) => `<option value="${p.id}">${App.escapeHtml(p.nome)}</option>`).join("");
      this._updatePdvSummary();
    } catch { /* toast já disparado */ }
  },

  async _loadSales() {
    const body = document.getElementById("salesTableBody");
    body.innerHTML = `<tr><td colspan="5"><div class="skeleton" style="height:36px;"></div></td></tr>`;
    try {
      this.sales = await App.api("/api/sales");
      this._renderSales(this.sales);
    } catch { /* toast já disparado */ }
  },

  _renderSales(items) {
    const body = document.getElementById("salesTableBody");
    if (!items.length) {
      body.innerHTML = `<tr><td colspan="5"><div class="state-block">Nenhuma venda registrada ainda.</div></td></tr>`;
      return;
    }
    body.innerHTML = items.slice(0, 100).map((s) => `
      <tr>
        <td>${App.fmtDate(s.data)}</td>
        <td>${App.escapeHtml(s.produto)}</td>
        <td class="num">${s.quantidade}</td>
        <td class="num">${App.fmtMoney(s.total)}</td>
        <td class="num">${App.fmtMoney(s.lucro)}</td>
      </tr>`).join("");
  },

  _currentProduct() {
    const id = document.getElementById("pdvProduct").value;
    return this.products.find((p) => String(p.id) === String(id));
  },

  _updatePdvSummary() {
    const product = this._currentProduct();
    const qty = Math.max(1, parseInt(document.getElementById("pdvQty").value || "1", 10));
    document.getElementById("pdvUnitPrice").textContent = App.fmtMoney(product ? product.preco_venda : 0);
    document.getElementById("pdvTotal").textContent = App.fmtMoney(product ? product.preco_venda * qty : 0);
    document.getElementById("pdvStockAvailable").textContent = product ? `${product.estoque_atual} unidades` : "—";
  },

  async confirmSale() {
    const product = this._currentProduct();
    const qty = parseInt(document.getElementById("pdvQty").value || "0", 10);
    if (!product) { App.toast("Selecione um produto.", "error"); return; }
    if (qty <= 0) { App.toast("Informe uma quantidade válida.", "error"); return; }
    if (qty > product.estoque_atual) { App.toast("Estoque insuficiente.", "error"); return; }

    if (!confirm(`Confirmar venda de ${qty}x ${product.nome} por ${App.fmtMoney(product.preco_venda * qty)}?`)) return;

    try {
      await App.api("/api/sales", {
        method: "POST",
        body: JSON.stringify({ produto_id: product.id, quantidade: qty }),
      });
      App.toast("Venda registrada com sucesso");
      document.getElementById("pdvQty").value = 1;
      this._loadProducts();
      this._loadSales();
    } catch { /* toast já disparado */ }
  },
};

document.getElementById("pdvProduct").addEventListener("change", () => App.pages.vendas._updatePdvSummary());
document.getElementById("pdvQty").addEventListener("input", () => App.pages.vendas._updatePdvSummary());
document.getElementById("pdvConfirmBtn").addEventListener("click", () => App.pages.vendas.confirmSale());

document.getElementById("salesSearch").addEventListener("input", (e) => {
  const term = e.target.value.trim().toLowerCase();
  const filtered = App.pages.vendas.sales.filter((s) => s.produto.toLowerCase().includes(term));
  App.pages.vendas._renderSales(filtered);
});
