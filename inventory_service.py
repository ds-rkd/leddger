"""
InventoryService
-----------------
Regras de negócio de estoque: leitura de produtos, ajustes manuais,
verificação de disponibilidade e histórico de movimentações.
Toda escrita passa pelo GoogleSheetsService.
"""
import uuid
from datetime import datetime
from typing import List, Dict, Any

from config.settings import settings
from services.google_sheets import sheets_service, GoogleSheetsError


class InventoryError(Exception):
    pass


def _to_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", ".")) if value not in ("", None) else 0.0
    except ValueError:
        return 0.0


def _to_int(value: Any) -> int:
    try:
        return int(float(value)) if value not in ("", None) else 0
    except ValueError:
        return 0


class InventoryService:
    def list_products(self, only_active: bool = True) -> List[Dict[str, Any]]:
        raw = sheets_service.read_sheet(settings.SHEET_PRODUTOS)
        products = []
        for r in raw:
            if only_active and str(r.get("Ativo", "TRUE")).upper() == "FALSE":
                continue
            products.append({
                "id": r.get("ID"),
                "nome": r.get("Produto"),
                "categoria": r.get("Categoria"),
                "custo": _to_float(r.get("Custo")),
                "preco_venda": _to_float(r.get("PrecoVenda")),
                "estoque_inicial": _to_int(r.get("EstoqueInicial")),
                "estoque_atual": _to_int(r.get("EstoqueAtual")),
                "estoque_minimo": _to_int(r.get("EstoqueMinimo")),
                "ativo": str(r.get("Ativo", "TRUE")).upper() != "FALSE",
                "_row": r.get("_row"),
            })
        return products

    def get_product(self, product_id: str) -> Dict[str, Any]:
        for p in self.list_products(only_active=False):
            if str(p["id"]) == str(product_id):
                return p
        raise InventoryError(f"Produto '{product_id}' não encontrado.")

    def create_product(self, data: Dict[str, Any]) -> Dict[str, Any]:
        nome = (data.get("nome") or "").strip()
        if not nome:
            raise InventoryError("Nome do produto é obrigatório.")
        custo = _to_float(data.get("custo"))
        preco_venda = _to_float(data.get("preco_venda"))
        if custo < 0 or preco_venda < 0:
            raise InventoryError("Custo e preço de venda não podem ser negativos.")
        estoque_inicial = _to_int(data.get("estoque_inicial"))
        if estoque_inicial < 0:
            raise InventoryError("Estoque inicial não pode ser negativo.")

        product_id = data.get("id") or uuid.uuid4().hex[:8].upper()
        row = [
            product_id,
            nome,
            data.get("categoria", ""),
            custo,
            preco_venda,
            estoque_inicial,
            estoque_inicial,  # estoque atual = inicial na criação
            _to_int(data.get("estoque_minimo", 0)),
            "TRUE" if data.get("ativo", True) else "FALSE",
        ]
        sheets_service.append_row(settings.SHEET_PRODUTOS, row)
        return self.get_product(product_id)

    def update_product(self, product_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        product = self.get_product(product_id)
        custo = _to_float(data.get("custo", product["custo"]))
        preco_venda = _to_float(data.get("preco_venda", product["preco_venda"]))
        if custo < 0 or preco_venda < 0:
            raise InventoryError("Custo e preço de venda não podem ser negativos.")

        row = [
            product["id"],
            data.get("nome", product["nome"]),
            data.get("categoria", product["categoria"]),
            custo,
            preco_venda,
            data.get("estoque_inicial", product["estoque_inicial"]),
            product["estoque_atual"],  # estoque atual só muda via venda/ajuste
            _to_int(data.get("estoque_minimo", product["estoque_minimo"])),
            "TRUE" if data.get("ativo", product["ativo"]) else "FALSE",
        ]
        sheets_service.update_row(settings.SHEET_PRODUTOS, product["_row"], row)
        return self.get_product(product_id)

    def deactivate_product(self, product_id: str) -> None:
        product = self.get_product(product_id)
        self.update_product(product_id, {**product, "ativo": False})

    # ------------------------------------------------------------------ #
    # Estoque
    # ------------------------------------------------------------------ #
    def adjust_stock(self, product_id: str, quantidade: int, motivo: str,
                      tipo: str = "ajuste", usuario: str = "sistema") -> Dict[str, Any]:
        """
        tipo: 'entrada' | 'saida' | 'ajuste' | 'venda'
        quantidade: sempre positiva; o sinal é definido pelo tipo.
        """
        if quantidade == 0:
            raise InventoryError("Quantidade de ajuste deve ser diferente de zero.")

        product = self.get_product(product_id)
        delta = quantidade if tipo in ("entrada", "ajuste_positivo") else -abs(quantidade)
        if tipo == "ajuste":
            delta = quantidade  # já vem com sinal correto do chamador

        novo_estoque = product["estoque_atual"] + delta
        if novo_estoque < 0:
            raise InventoryError("Estoque insuficiente.")

        row = [
            product["id"], product["nome"], product["categoria"],
            product["custo"], product["preco_venda"], product["estoque_inicial"],
            novo_estoque, product["estoque_minimo"],
            "TRUE" if product["ativo"] else "FALSE",
        ]
        sheets_service.update_row(settings.SHEET_PRODUTOS, product["_row"], row)
        self._log_movement(product_id, tipo, abs(delta), motivo, usuario)
        return self.get_product(product_id)

    def _log_movement(self, product_id: str, tipo: str, quantidade: int, motivo: str, usuario: str) -> None:
        row = [
            uuid.uuid4().hex[:10],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            product_id, tipo, quantidade, motivo, usuario,
        ]
        sheets_service.append_row(settings.SHEET_MOVIMENTACOES, row)

    def movements(self) -> List[Dict[str, Any]]:
        return sheets_service.read_sheet(settings.SHEET_MOVIMENTACOES)

    def low_stock(self) -> List[Dict[str, Any]]:
        return [p for p in self.list_products() if p["estoque_atual"] <= p["estoque_minimo"]]

    def out_of_stock(self) -> List[Dict[str, Any]]:
        return [p for p in self.list_products() if p["estoque_atual"] <= 0]


inventory_service = InventoryService()
