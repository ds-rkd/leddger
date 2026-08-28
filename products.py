from flask import Blueprint, request, jsonify
from services.inventory_service import inventory_service, InventoryError
from services.google_sheets import GoogleSheetsError

products_bp = Blueprint("products", __name__)


def _error(code, message, status=400):
    return jsonify({"success": False, "error": {"code": code, "message": message}}), status


@products_bp.route("/api/products", methods=["GET"])
def list_products():
    try:
        only_active = request.args.get("apenas_ativos", "true").lower() != "false"
        products = inventory_service.list_products(only_active=only_active)
        return jsonify({"success": True, "data": products, "message": ""})
    except GoogleSheetsError as exc:
        return _error("SHEETS_UNAVAILABLE", str(exc), 503)


@products_bp.route("/api/products", methods=["POST"])
def create_product():
    try:
        product = inventory_service.create_product(request.get_json(force=True) or {})
        return jsonify({"success": True, "data": product, "message": "Produto cadastrado com sucesso"}), 201
    except InventoryError as exc:
        return _error("INVALID_PRODUCT", str(exc))
    except GoogleSheetsError as exc:
        return _error("SHEETS_UNAVAILABLE", str(exc), 503)


@products_bp.route("/api/products/<product_id>", methods=["PUT"])
def update_product(product_id):
    try:
        product = inventory_service.update_product(product_id, request.get_json(force=True) or {})
        return jsonify({"success": True, "data": product, "message": "Produto atualizado com sucesso"})
    except InventoryError as exc:
        return _error("INVALID_PRODUCT", str(exc), 404 if "não encontrado" in str(exc) else 400)
    except GoogleSheetsError as exc:
        return _error("SHEETS_UNAVAILABLE", str(exc), 503)


@products_bp.route("/api/products/<product_id>", methods=["DELETE"])
def delete_product(product_id):
    try:
        inventory_service.deactivate_product(product_id)
        return jsonify({"success": True, "data": {}, "message": "Produto desativado com sucesso"})
    except InventoryError as exc:
        return _error("INVALID_PRODUCT", str(exc), 404 if "não encontrado" in str(exc) else 400)
    except GoogleSheetsError as exc:
        return _error("SHEETS_UNAVAILABLE", str(exc), 503)
