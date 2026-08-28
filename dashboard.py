from flask import Blueprint, request, jsonify
from services.analytics_service import analytics_service
from services.google_sheets import sheets_service

dashboard_bp = Blueprint("dashboard", __name__)


def _period_args():
    return {
        "periodo": request.args.get("periodo", "30dias"),
        "data_inicio": request.args.get("data_inicio"),
        "data_fim": request.args.get("data_fim"),
    }


@dashboard_bp.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    args = _period_args()
    data = analytics_service.dashboard(**args)
    data["revenue_series"] = analytics_service.revenue_series(**args)
    data["top_products"] = analytics_service.top_products(**args)
    data["category_distribution"] = analytics_service.category_distribution(**args)
    return jsonify({"success": True, "data": data, "message": "Dashboard carregado com sucesso"})


@dashboard_bp.route("/api/status/google-sheets", methods=["GET"])
def sheets_status():
    return jsonify({"success": True, "data": sheets_service.status(), "message": ""})
