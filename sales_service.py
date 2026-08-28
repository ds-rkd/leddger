"""
SalesService
------------
Trata cada venda como uma operação lógica única: valida estoque,
calcula valores no backend (nunca confia no frontend) e só então
registra a venda e atualiza o estoque. Se a atualização de estoque
falhar após a venda ser gravada, a inconsistência é sinalizada para
correção manual (o Google Sheets não é transacional).
"""
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any

from config.settings import settings
from services.google_sheets import sheets_service, GoogleSheetsError
from services.inventory_service import inventory_service, InventoryError

logger = logging.getLogger("sales_service")


class SalesError(Exception):
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


class SalesService:
    def register_sale(self, product_id: str, quantidade: int, usuario: str = "sistema") -> Dict[str, Any]:
        quantidade = _to_int(quantidade)
        if quantidade <= 0:
            raise SalesError("Quantidade deve ser maior que zero.")

        product = inventory_service.get_product(product_id)
        if not product["ativo"]:
            raise SalesError("Produto inativo não pode ser vendido.")
        if product["estoque_atual"] < quantidade:
            raise SalesError(
                f"Estoque insuficiente. Disponível: {product['estoque_atual']}, solicitado: {quantidade}."
            )

        valor_unitario = product["preco_venda"]
        custo_unitario = product["custo"]
        total = round(valor_unitario * quantidade, 2)
        custo_total = round(custo_unitario * quantidade, 2)
        lucro = round(total - custo_total, 2)
        venda_id = uuid.uuid4().hex[:10]

        row = [
            venda_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            product["id"], product["nome"], quantidade,
            valor_unitario, total, custo_unitario, lucro,
        ]

        # 1) Grava a venda primeiro
        sheets_service.append_row(settings.SHEET_VENDAS, row)

        # 2) Atualiza o estoque. Se falhar, sinaliza inconsistência explicitamente
        try:
            inventory_service.adjust_stock(
                product_id, quantidade, motivo=f"Venda {venda_id}",
                tipo="saida", usuario=usuario,
            )
        except (InventoryError, GoogleSheetsError) as exc:
            logger.error(
                "INCONSISTÊNCIA: venda %s registrada mas estoque NÃO foi atualizado: %s",
                venda_id, exc,
            )
            raise SalesError(
                "Venda registrada, mas houve falha ao atualizar o estoque. "
                "Verifique manualmente o produto e ajuste o estoque se necessário. "
                f"(ID da venda: {venda_id})"
            ) from exc

        return {
            "id_venda": venda_id, "produto_id": product["id"], "produto": product["nome"],
            "quantidade": quantidade, "valor_unitario": valor_unitario, "total": total,
            "custo_unitario": custo_unitario, "lucro": lucro,
        }

    def list_sales(self) -> List[Dict[str, Any]]:
        raw = sheets_service.read_sheet(settings.SHEET_VENDAS)
        sales = []
        for r in raw:
            sales.append({
                "id_venda": r.get("IDVenda"),
                "data": r.get("Data"),
                "produto_id": r.get("ProdutoID"),
                "produto": r.get("Produto"),
                "quantidade": _to_int(r.get("Quantidade")),
                "valor_unitario": _to_float(r.get("ValorUnitario")),
                "total": _to_float(r.get("Total")),
                "custo_unitario": _to_float(r.get("CustoUnitario")),
                "lucro": _to_float(r.get("Lucro")),
            })
        return sales


sales_service = SalesService()
