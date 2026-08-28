/* ==========================================================================
   products.js — CRUD de produtos e gestão de estoque (ajustes + movimentações)
   ========================================================================== */
App.pages.produtos = {
  items: [],
  onEnter() { this.load(); },

  async load() {
    document.getElementById("productsTableBody").innerHTML =
      `<tr><td colspan="7"><div class="skeleton" style="height:36px;"></div></td></tr>`;
    try {
      this.items = await App.api("/api/products?apenas_ativos=false");
      App.productsCache = this.items;
      this._render();
    } catch { /* toast já disparado */ }
  },

  _render() {
    const body = document.getElementById("productsTableBody");
    if (!this.items.length) {
      body.innerHTML = `<tr><td colspan="7"><div class="state-block">
        <span class="state-title">Nenhum produto cadastrado</span>
        Cadastre o primeiro produto para começar a vender.
      </div></td></tr>`;
      return;
    }
    body.innerHTML = this.items.map((p) => {
      const margem = p.preco_venda ? (((p.preco_venda - p.custo) / p.preco_venda) * 100).toFixed(1) : "0.0";
      return `
        <tr>
          <td>${App.escapeHtml(p.nome)} ${!p.ativo ? '<span class="badge neutral">Inativo</span>' : ""}</td>
          <td>${App.escapeHtml(p.categoria || "—")}</td>
          <td class="num">${App.fmtMoney(p.custo)}</td>
          <td class="num">${App.fmtMoney(p.preco_venda)}</td>
          <td class="num">${margem}%</td>
          <td class="num">${p.estoque_atual}</td>
          <td>
            <button class="btn btn-secondary btn-sm" data-edit-product="${p.id}">Editar</button>
          </td>
        </tr>`;
    }).join("");

    body.querySelectorAll("[data-edit-product]").forEach((btn) => {
      btn.addEventListener("click", () => this.openEdit(btn.dataset.editProduct));
    });
  },

  openNew() {
    document.getElementById("productModalTitle").textContent = "Novo produto";
    document.getElementById("productForm").reset();
    document.getElementById("productId").value = "";
    App.openModal("productModal");
  },

  openEdit(id) {
    const p = this.items.find((x) => String(x.id) === String(id));
    if (!p) return;
    document.getElementById("productModalTitle").textContent = "Editar produto";
    document.getElementById("productId").value = p.id;
    document.getElementById("productNome").value = p.nome;
    document.getElementById("productCategoria").value = p.categoria || "";
    document.getElementById("productAtivo").value = String(p.ativo);
    document.getElementById("productCusto").value = p.custo;
    document.getElementById("productPreco").value = p.preco_venda;
    document.getElementById("productEstoqueInicial").value = p.estoque_inicial;
    document.getElementById("productEstoqueMinimo").value = p.estoque_minimo;
    App.openModal("productModal");
  },

  async submit(e) {
    e.preventDefault();
    const id = document.getElementById("productId").value;
    const payload = {
      nome: document.getElementById("productNome").value.trim(),
      categoria: document.getElementById("productCategoria").value.trim(),
      ativo: document.getElementById("productAtivo").value === "true",
      custo: parseFloat(document.getElementById("productCusto").value),
      preco_venda: parseFloat(document.getElementById("productPreco").value),
      estoque_inicial: parseInt(document.getElementById("productEstoqueInicial").value, 10),
      estoque_minimo: parseInt(document.getElementById("productEstoqueMinimo").value, 10),
    };
    try {
      if (id) {
        await App.api(`/api/products/${id}`, { method: "PUT", body: JSON.stringify(payload) });
        App.toast("Produto atualizado com sucesso");
      } else {
        await App.api("/api/products", { method: "POST", body: JSON.stringify(payload) });
        App.toast("Produto cadastrado com sucesso");
      }
      App.closeModal("productModal");
      this.load();
    } catch { /* toast já disparado */ }
  },
};

document.getElementById("newProductBtn").addEventListener("click", () => App.pages.produtos.openNew());
document.getElementById("productForm").addEventListener("submit", (e) => App.pages.produtos.submit(e));

/* ==========================================================================
   Estoque
   ========================================================================== */
App.pages.estoque = {
  items: [],
  onEnter() { this.load(); },

  async load() {
    const invBody = document.getElementById("inventoryTableBody");
    invBody.innerHTML = `<tr><td colspan="5"><div class="skeleton" style="height:36px;"></div></td></tr>`;
    try {
      const [inventory, movements] = await Promise.all([
        App.api("/api/inventory"),
        App.api("/api/inventory/movements"),
      ]);
      this.items = inventory;
      this._renderInventory(inventory);
      this._renderMovements(movements.slice(0, 30));
    } catch { /* toast já disparado */ }
  },

  _statusBadge(status) {
    if (status === "sem_estoque") return '<span class="badge danger">Sem estoque</span>';
    if (status === "estoque_baixo") return '<span class="badge warn">Estoque baixo</span>';
    return '<span class="badge">Normal</span>';
  },

  _renderInventory(items) {
    const body = document.getElementById("inventoryTableBody");
    if (!items.length) {
      body.innerHTML = `<tr><td colspan="5"><div class="state-block">Nenhum produto cadastrado ainda.</div></td></tr>`;
      return;
    }
    body.innerHTML = items.map((p) => `
      <tr>
        <td>${App.escapeHtml(p.nome)}</td>
        <td class="num">${p.estoque_atual}</td>
        <td class="num">${p.estoque_minimo}</td>
        <td>${this._statusBadge(p.status)}</td>
        <td><button class="btn btn-secondary btn-sm" data-adjust="${p.id}">Ajustar estoque</button></td>
      </tr>`).join("");

    body.querySelectorAll("[data-adjust]").forEach((btn) => {
      btn.addEventListener("click", () => this.openAdjust(btn.dataset.adjust));
    });
  },

  _renderMovements(items) {
    const body = document.getElementById("movementsTableBody");
    if (!items.length) {
      body.innerHTML = `<tr><td colspan="5"><div class="state-block">Nenhuma movimentação registrada.</div></td></tr>`;
      return;
    }
    body.innerHTML = items.map((m) => `
      <tr>
        <td>${App.fmtDate(m.Data)}</td>
        <td>${App.escapeHtml(m.ProdutoID)}</td>
        <td>${App.escapeHtml(m.Tipo)}</td>
        <td class="num">${App.escapeHtml(m.Quantidade)}</td>
        <td>${App.escapeHtml(m.Motivo)}</td>
      </tr>`).join("");
  },

  openAdjust(productId) {
    const p = this.items.find((x) => String(x.id) === String(productId));
    if (!p) return;
    document.getElementById("stockProductId").value = p.id;
    document.getElementById("stockProductLabel").textContent = `${p.nome} — estoque atual: ${p.estoque_atual}`;
    document.getElementById("stockForm").reset();
    App.openModal("stockModal");
  },

  async submitAdjust(e) {
    e.preventDefault();
    const payload = {
      produto_id: document.getElementById("stockProductId").value,
      tipo: document.getElementById("stockTipo").value,
      quantidade: parseInt(document.getElementById("stockQtd").value, 10),
      motivo: document.getElementById("stockMotivo").value.trim(),
    };
    try {
      await App.api("/api/inventory/adjust", { method: "POST", body: JSON.stringify(payload) });
      App.toast("Estoque atualizado com sucesso");
      App.closeModal("stockModal");
      this.load();
    } catch { /* toast já disparado */ }
  },
};

document.getElementById("stockForm").addEventListener("submit", (e) => App.pages.estoque.submitAdjust(e));
