from flask import Blueprint, request, jsonify
from services.inventory_service import inventory_service, InventoryError
from services.google_sheets import GoogleSheetsError

inventory_bp = Blueprint("inventory", __name__)


def _error(code, message, status=400):
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status


@inventory_bp.route("/api/inventory", methods=["GET"])
def get_inventory():
    try:
        products = inventory_service.list_products()
        for p in products:
            if p["estoque_atual"] <= 0:
                p["status"] = "sem_estoque"
            elif p["estoque_atual"] <= p["estoque_minimo"]:
                p["status"] = "estoque_baixo"
            else:
                p["status"] = "normal"
        return jsonify({"success": True, "data": products, "message": ""})
    except GoogleSheetsError as exc:
        return _error("SHEETS_UNAVAILABLE", str(exc), 503)


@inventory_bp.route("/api/inventory/movements", methods=["GET"])
def get_movements():
    try:
        movements = inventory_service.movements()
        movements.sort(key=lambda m: m.get("Data", ""), reverse=True)
        return jsonify({"success": True, "data": movements, "message": ""})
    except GoogleSheetsError as exc:
        return _error("SHEETS_UNAVAILABLE", str(exc), 503)


@inventory_bp.route("/api/inventory/adjust", methods=["POST"])
def adjust_inventory():
    payload = request.get_json(force=True) or {}
    try:
        quantidade = int(payload.get("quantidade", 0))
        tipo = payload.get("tipo", "ajuste")  # entrada | saida | ajuste
        if tipo == "saida" and quantidade > 0:
            quantidade = -quantidade
        elif tipo == "entrada":
            quantidade = abs(quantidade)

        product = inventory_service.adjust_stock(
            product_id=payload.get("produto_id"),
            quantidade=quantidade,
            motivo=payload.get("motivo", "Ajuste manual"),
            tipo="ajuste",
            usuario=payload.get("usuario", "sistema"),
        )
        return jsonify({"success": True, "data": product, "message": "Estoque atualizado com sucesso"})
    except InventoryError as exc:
        code = "INSUFFICIENT_STOCK" if "insuficiente" in str(exc).lower() else "INVALID_ADJUSTMENT"
        return _error(code, str(exc))
    except GoogleSheetsError as exc:
        return _error("SHEETS_UNAVAILABLE", str(exc), 503)
