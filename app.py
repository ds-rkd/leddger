"""
Ponto de entrada da aplicação.
Cria o app Flask, registra os blueprints e serve o frontend (SPA).
"""
import logging
from flask import Flask, render_template, jsonify

from config.settings import settings
from routes.dashboard import dashboard_bp
from routes.products import products_bp
from routes.sales import sales_bp
from routes.inventory import inventory_bp
from routes.reports import reports_bp

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = settings.SECRET_KEY
    app.config["JSON_AS_ASCII"] = False

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(reports_bp)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"success": False, "error": {"code": "NOT_FOUND", "message": "Recurso não encontrado."}}), 404

    @app.errorhandler(500)
    def server_error(e):
        logging.getLogger("app").error("Erro interno: %s", e)
        return jsonify({
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": "Não foi possível processar a solicitação. Tente novamente."},
        }), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=settings.DEBUG, host="0.0.0.0", port=5000)
