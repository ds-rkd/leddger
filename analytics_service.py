"""
AnalyticsService
-----------------
Centraliza TODOS os cálculos financeiros e de estoque.
O frontend nunca calcula faturamento, lucro ou margem — apenas exibe
o que este serviço retorna.
"""
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Optional

from services.sales_service import sales_service
from services.inventory_service import inventory_service


def _parse_date(value: str) -> Optional[datetime]:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return None


class AnalyticsService:
    # ------------------------------------------------------------------ #
    # Filtro de período
    # ------------------------------------------------------------------ #
    def _period_bounds(self, periodo: str, data_inicio: str = None, data_fim: str = None):
        hoje = datetime.now()
        inicio_dia = hoje.replace(hour=0, minute=0, second=0, microsecond=0)

        if periodo == "hoje":
            return inicio_dia, hoje
        if periodo == "ontem":
            ontem = inicio_dia - timedelta(days=1)
            return ontem, inicio_dia
        if periodo == "7dias":
            return inicio_dia - timedelta(days=7), hoje
        if periodo == "30dias":
            return inicio_dia - timedelta(days=30), hoje
        if periodo == "este_mes":
            return inicio_dia.replace(day=1), hoje
        if periodo == "mes_anterior":
            primeiro_dia_mes_atual = inicio_dia.replace(day=1)
            ultimo_dia_mes_anterior = primeiro_dia_mes_atual - timedelta(days=1)
            primeiro_dia_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)
            return primeiro_dia_mes_anterior, primeiro_dia_mes_atual
        if periodo == "personalizado" and data_inicio and data_fim:
            return (
                datetime.strptime(data_inicio, "%Y-%m-%d"),
                datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1),
            )
        # default: tudo
        return datetime.min, hoje + timedelta(days=1)

    def _filter_sales(self, periodo: str = "30dias", data_inicio: str = None,
                       data_fim: str = None, produto_id: str = None,
                       categoria: str = None) -> List[Dict[str, Any]]:
        inicio, fim = self._period_bounds(periodo, data_inicio, data_fim)
        sales = sales_service.list_sales()
        products_by_id = {p["id"]: p for p in inventory_service.list_products(only_active=False)}

        filtered = []
        for s in sales:
            d = _parse_date(s["data"])
            if d is None or not (inicio <= d < fim):
                continue
            if produto_id and s["produto_id"] != produto_id:
                continue
            if categoria:
                p = products_by_id.get(s["produto_id"])
                if not p or p.get("categoria") != categoria:
                    continue
            filtered.append(s)
        return filtered

    # ------------------------------------------------------------------ #
    # Dashboard
    # ------------------------------------------------------------------ #
    def dashboard(self, periodo: str = "30dias", data_inicio: str = None, data_fim: str = None) -> Dict[str, Any]:
        sales = self._filter_sales(periodo, data_inicio, data_fim)
        products = inventory_service.list_products()

        faturamento = round(sum(s["total"] for s in sales), 2)
        custo_total = round(sum(s["custo_unitario"] * s["quantidade"] for s in sales), 2)
        lucro = round(faturamento - custo_total, 2)
        margem = round((lucro / faturamento * 100), 2) if faturamento else 0.0
        num_vendas = len(sales)
        unidades_vendidas = sum(s["quantidade"] for s in sales)
        ticket_medio = round(faturamento / num_vendas, 2) if num_vendas else 0.0

        estoque_total = sum(p["estoque_atual"] for p in products)
        low_stock = inventory_service.low_stock()
        out_of_stock = inventory_service.out_of_stock()

        valor_estoque_custo = round(sum(p["estoque_atual"] * p["custo"] for p in products), 2)
        valor_estoque_potencial = round(sum(p["estoque_atual"] * p["preco_venda"] for p in products), 2)

        return {
            "faturamento": faturamento,
            "custo_total": custo_total,
            "lucro": lucro,
            "margem_media": margem,
            "num_vendas": num_vendas,
            "unidades_vendidas": unidades_vendidas,
            "ticket_medio": ticket_medio,
            "estoque_total": estoque_total,
            "estoque_baixo_qtd": len(low_stock),
            "sem_estoque_qtd": len(out_of_stock),
            "valor_estoque_custo": valor_estoque_custo,
            "valor_estoque_potencial": valor_estoque_potencial,
            "estoque_baixo": low_stock,
        }

    # ------------------------------------------------------------------ #
    # Séries para gráficos
    # ------------------------------------------------------------------ #
    def revenue_series(self, periodo: str = "30dias", data_inicio: str = None, data_fim: str = None) -> Dict[str, Any]:
        sales = self._filter_sales(periodo, data_inicio, data_fim)
        by_day = defaultdict(lambda: {"faturamento": 0.0, "lucro": 0.0})
        for s in sales:
            d = _parse_date(s["data"])
            key = d.strftime("%Y-%m-%d") if d else "desconhecido"
            by_day[key]["faturamento"] += s["total"]
            by_day[key]["lucro"] += s["total"] - (s["custo_unitario"] * s["quantidade"])

        days = sorted(by_day.keys())
        return {
            "labels": days,
            "faturamento": [round(by_day[d]["faturamento"], 2) for d in days],
            "lucro": [round(by_day[d]["lucro"], 2) for d in days],
        }

    def top_products(self, periodo: str = "30dias", data_inicio: str = None,
                      data_fim: str = None, limite: int = 5) -> List[Dict[str, Any]]:
        sales = self._filter_sales(periodo, data_inicio, data_fim)
        agg = defaultdict(lambda: {"quantidade": 0, "faturamento": 0.0, "lucro": 0.0, "produto": ""})
        for s in sales:
            a = agg[s["produto_id"]]
            a["produto"] = s["produto"]
            a["quantidade"] += s["quantidade"]
            a["faturamento"] += s["total"]
            a["lucro"] += s["total"] - (s["custo_unitario"] * s["quantidade"])

        ranking = [
            {"produto_id": pid, "produto": v["produto"], "quantidade": v["quantidade"],
             "faturamento": round(v["faturamento"], 2), "lucro": round(v["lucro"], 2)}
            for pid, v in agg.items()
        ]
        ranking.sort(key=lambda x: x["quantidade"], reverse=True)
        return ranking[:limite]

    def category_distribution(self, periodo: str = "30dias", data_inicio: str = None,
                               data_fim: str = None) -> Dict[str, Any]:
        sales = self._filter_sales(periodo, data_inicio, data_fim)
        products_by_id = {p["id"]: p for p in inventory_service.list_products(only_active=False)}
        by_cat = defaultdict(float)
        for s in sales:
            p = products_by_id.get(s["produto_id"])
            categoria = p.get("categoria", "Sem categoria") if p else "Sem categoria"
            by_cat[categoria] += s["total"]
        return {"labels": list(by_cat.keys()), "valores": [round(v, 2) for v in by_cat.values()]}

    # ------------------------------------------------------------------ #
    # Produtos mais rentáveis (seção analítica)
    # ------------------------------------------------------------------ #
    def profitability_report(self, periodo: str = "30dias", data_inicio: str = None,
                              data_fim: str = None) -> Dict[str, Any]:
        sales = self._filter_sales(periodo, data_inicio, data_fim)
        products = {p["id"]: p for p in inventory_service.list_products(only_active=False)}
        agg = defaultdict(lambda: {"quantidade": 0, "faturamento": 0.0, "lucro": 0.0, "produto": ""})
        for s in sales:
            a = agg[s["produto_id"]]
            a["produto"] = s["produto"]
            a["quantidade"] += s["quantidade"]
            a["faturamento"] += s["total"]
            a["lucro"] += s["total"] - (s["custo_unitario"] * s["quantidade"])

        rows = []
        for pid, v in agg.items():
            margem = round((v["lucro"] / v["faturamento"] * 100), 2) if v["faturamento"] else 0.0
            estoque_atual = products.get(pid, {}).get("estoque_atual", 0)
            giro = round(v["quantidade"] / estoque_atual, 2) if estoque_atual else 0.0
            rows.append({
                "produto_id": pid, "produto": v["produto"], "quantidade": v["quantidade"],
                "faturamento": round(v["faturamento"], 2), "lucro": round(v["lucro"], 2),
                "margem": margem, "giro_estoque": giro,
            })

        if not rows:
            return {"itens": []}

        def top(key):
            return max(rows, key=lambda r: r[key])["produto"]

        def bottom(key):
            return min(rows, key=lambda r: r[key])["produto"]

        return {
            "itens": rows,
            "mais_vendido": top("quantidade"),
            "mais_lucrativo": top("lucro"),
            "maior_margem": top("margem"),
            "menor_margem": bottom("margem"),
            "maior_faturamento": top("faturamento"),
            "maior_giro": top("giro_estoque"),
        }


analytics_service = AnalyticsService()
