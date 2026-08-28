/* ==========================================================================
   app.js — núcleo da aplicação: navegação, cliente de API, toasts, tema.
   Cada página (dashboard.js, products.js, sales.js) se registra em
   App.pages e é chamada quando o usuário navega até ela.
   ========================================================================== */
const App = {
  pages: {},          // { pageId: { onEnter(), onPeriodChange() } }
  currentPage: "dashboard",
  currentPeriod: { periodo: "30dias", data_inicio: null, data_fim: null },
  productsCache: [],  // cache leve para evitar refetch em cada modal

  init() {
    this._initTheme();
    this._initNav();
    this._initPeriodControls();
    this._initMobileMenu();
    this._initModals();
    this.checkSheetsStatus();
    this.navigate("dashboard");
  },

  // ------------------------------------------------------------------ //
  // Navegação entre páginas
  // ------------------------------------------------------------------ //
  _initNav() {
    document.querySelectorAll(".nav-item[data-page]").forEach((btn) => {
      btn.addEventListener("click", () => this.navigate(btn.dataset.page));
    });
  },

  navigate(pageId) {
    this.currentPage = pageId;
    document.querySelectorAll(".nav-item[data-page]").forEach((b) => {
      b.classList.toggle("active", b.dataset.page === pageId);
    });
    document.querySelectorAll("[data-page-content]").forEach((section) => {
      section.classList.toggle("page-hidden", section.dataset.pageContent !== pageId);
    });
    const titles = {
      dashboard: "Dashboard", vendas: "Vendas", produtos: "Produtos",
      estoque: "Estoque", relatorios: "Relatórios", configuracoes: "Configurações",
    };
    document.getElementById("pageTitle").textContent = titles[pageId] || "";
    document.getElementById("periodControls").style.visibility =
      ["dashboard", "relatorios"].includes(pageId) ? "visible" : "hidden";

    this._closeMobileSidebar();
    if (this.pages[pageId] && this.pages[pageId].onEnter) {
      this.pages[pageId].onEnter();
    }
  },

  // ------------------------------------------------------------------ //
  // Filtro de período (compartilhado entre Dashboard e Relatórios)
  // ------------------------------------------------------------------ //
  _initPeriodControls() {
    const select = document.getElementById("periodSelect");
    const start = document.getElementById("dateStart");
    const end = document.getElementById("dateEnd");

    select.addEventListener("change", () => {
      const custom = select.value === "personalizado";
      start.style.display = custom ? "inline-block" : "none";
      end.style.display = custom ? "inline-block" : "none";
      if (!custom) this._applyPeriod(select.value);
    });
    [start, end].forEach((el) => el.addEventListener("change", () => {
      if (start.value && end.value) this._applyPeriod("personalizado", start.value, end.value);
    }));
  },

  _applyPeriod(periodo, data_inicio = null, data_fim = null) {
    this.currentPeriod = { periodo, data_inicio, data_fim };
    Object.values(this.pages).forEach((p) => p.onPeriodChange && p.onPeriodChange());
  },

  periodQuery() {
    const p = this.currentPeriod;
    let qs = `periodo=${encodeURIComponent(p.periodo)}`;
    if (p.data_inicio) qs += `&data_inicio=${p.data_inicio}`;
    if (p.data_fim) qs += `&data_fim=${p.data_fim}`;
    return qs;
  },

  // ------------------------------------------------------------------ //
  // Tema claro/escuro
  // ------------------------------------------------------------------ //
  _initTheme() {
    const saved = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", saved);
    this._reflectTheme(saved);
    document.getElementById("themeToggleBtn").addEventListener("click", () => {
      const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("theme", next);
      this._reflectTheme(next);
      if (this.pages.dashboard && this.pages.dashboard.refreshChartsTheme) {
        this.pages.dashboard.refreshChartsTheme();
      }
    });
  },
  _reflectTheme(theme) {
    document.getElementById("themeLabel").textContent = theme === "dark" ? "Modo escuro" : "Modo claro";
  },

  // ------------------------------------------------------------------ //
  // Menu mobile
  // ------------------------------------------------------------------ //
  _initMobileMenu() {
    const sidebar = document.getElementById("sidebar");
    const scrim = document.getElementById("sidebarScrim");
    document.getElementById("mobileMenuBtn").addEventListener("click", () => {
      sidebar.classList.add("open");
      scrim.classList.add("show");
    });
    scrim.addEventListener("click", () => this._closeMobileSidebar());
  },
  _closeMobileSidebar() {
    document.getElementById("sidebar").classList.remove("open");
    document.getElementById("sidebarScrim").classList.remove("show");
  },

  // ------------------------------------------------------------------ //
  // Modais genéricos
  // ------------------------------------------------------------------ //
  _initModals() {
    document.querySelectorAll("[data-close-modal]").forEach((el) => {
      el.addEventListener("click", (e) => this.closeModal(e.target.closest(".modal-overlay").id));
    });
    document.querySelectorAll(".modal-overlay").forEach((overlay) => {
      overlay.addEventListener("click", (e) => { if (e.target === overlay) this.closeModal(overlay.id); });
    });
  },
  openModal(id) { document.getElementById(id).classList.remove("hidden"); },
  closeModal(id) { document.getElementById(id).classList.add("hidden"); },

  // ------------------------------------------------------------------ //
  // Toasts
  // ------------------------------------------------------------------ //
  toast(message, type = "success") {
    const stack = document.getElementById("toastStack");
    const el = document.createElement("div");
    el.className = `toast ${type === "success" ? "" : type}`;
    el.textContent = message;
    stack.appendChild(el);
    setTimeout(() => el.remove(), 4500);
  },

  // ------------------------------------------------------------------ //
  // Cliente de API — camada única de comunicação com o backend
  // ------------------------------------------------------------------ //
  async api(path, options = {}) {
    try {
      const res = await fetch(path, {
        headers: { "Content-Type": "application/json" },
        ...options,
      });
      const body = await res.json().catch(() => null);
      if (!res.ok || !body || body.success === false) {
        const msg = (body && body.error && body.error.message) ||
          "Não foi possível sincronizar os dados. Verifique sua conexão e tente novamente.";
        throw new Error(msg);
      }
      return body.data;
    } catch (err) {
      this.toast(err.message || "Erro inesperado.", "error");
      throw err;
    }
  },

  async checkSheetsStatus() {
    try {
      const status = await this.api("/api/status/google-sheets");
      this._paintSheetsStatus(status.connected);
    } catch {
      this._paintSheetsStatus(false);
    }
  },
  _paintSheetsStatus(connected) {
    const dot = document.getElementById("sheetsStatusDot");
    const text = document.getElementById("sheetsStatusText");
    dot.className = `status-dot ${connected ? "on" : "off"}`;
    text.textContent = connected ? "Google Sheets · Conectado" : "Google Sheets · Desconectado";

    const settingsDot = document.querySelector("#settingsSheetsStatus .status-dot");
    const settingsText = document.querySelector("#settingsSheetsStatus span:last-child");
    if (settingsDot) {
      settingsDot.className = `status-dot ${connected ? "on" : "off"}`;
      settingsText.textContent = connected ? "Conectado" : "Desconectado — verifique o .env";
    }
  },

  // ------------------------------------------------------------------ //
  // Formatação
  // ------------------------------------------------------------------ //
  fmtMoney(v) {
    return (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  },
  fmtDate(isoLike) {
    if (!isoLike) return "—";
    const [datePart, timePart] = isoLike.split(" ");
    if (!datePart) return isoLike;
    const [y, m, d] = datePart.split("-");
    return `${d}/${m}/${y}${timePart ? " " + timePart.slice(0, 5) : ""}`;
  },
  escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str ?? "";
    return div.innerHTML;
  },
};

document.addEventListener("DOMContentLoaded", () => App.init());
