from flask import Blueprint, request, jsonify
from services.sales_service import sales_service, SalesError
from services.google_sheets import GoogleSheetsError

sales_bp = Blueprint("sales", __name__)


def _error(code, message, status=400):
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status


@sales_bp.route("/api/sales", methods=["GET"])
def list_sales():
    try:
        sales = sales_service.list_sales()
        sales.sort(key=lambda s: s["data"], reverse=True)
        return jsonify({"success": True, "data": sales, "message": ""})
    except GoogleSheetsError as exc:
        return _error("SHEETS_UNAVAILABLE", str(exc), 503)


@sales_bp.route("/api/sales", methods=["POST"])
def create_sale():
    payload = request.get_json(force=True) or {}
    try:
        sale = sales_service.register_sale(
            product_id=payload.get("produto_id"),
            quantidade=payload.get("quantidade"),
            usuario=payload.get("usuario", "sistema"),
        )
        return jsonify({"success": True, "data": sale, "message": "Venda registrada com sucesso"}), 201
    except SalesError as exc:
        code = "INSUFFICIENT_STOCK" if "insuficiente" in str(exc).lower() else "INVALID_SALE"
        return _error(code, str(exc))
    except GoogleSheetsError as exc:
        return _error("SHEETS_UNAVAILABLE", str(exc), 503)
