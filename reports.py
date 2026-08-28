import csv
import io
from flask import Blueprint, request, jsonify, Response
from services.analytics_service import analytics_service
from services.sales_service import sales_service
from services.google_sheets import GoogleSheetsError

reports_bp = Blueprint("reports", __name__)


def _period_args():
    return {
        "periodo": request.args.get("periodo", "30dias"),
        "data_inicio": request.args.get("data_inicio"),
        "data_fim": request.args.get("data_fim"),
    }


@reports_bp.route("/api/reports", methods=["GET"])
def get_reports():
    try:
        args = _period_args()
        data = analytics_service.profitability_report(**args)
        return jsonify({"success": True, "data": data, "message": ""})
    except GoogleSheetsError as exc:
        return jsonify({"success": False, "error": {"code": "SHEETS_UNAVAILABLE", "message": str(exc)}}), 503


@reports_bp.route("/api/reports/export", methods=["GET"])
def export_csv():
    try:
        args = _period_args()
        sales = sales_service.list_sales()
        # aplica mesmo filtro de período usado no dashboard
        filtered = analytics_service._filter_sales(**args)
        ids = {s["id_venda"] for s in filtered}
        rows = [s for s in sales if s["id_venda"] in ids]

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["ID Venda", "Data", "Produto", "Quantidade", "Valor Unitário", "Total", "Lucro"])
        for r in rows:
            writer.writerow([r["id_venda"], r["data"], r["produto"], r["quantidade"],
                              r["valor_unitario"], r["total"], r["lucro"]])

        return Response(
            buffer.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=relatorio_vendas.csv"},
        )
    except GoogleSheetsError as exc:
        return jsonify({"success": False, "error": {"code": "SHEETS_UNAVAILABLE", "message": str(exc)}}), 503
