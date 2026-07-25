"""Application factory: wires config, extensions, blueprints and error handlers."""
from flask import Flask, jsonify

from .config import Config
from .extensions import cors, db, jwt, limiter


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # --- Extensions ---------------------------------------------------------
    db.init_app(app)
    jwt.init_app(app)
    limiter.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    # --- Blueprints ---------------------------------------------------------
    from .routes.auth import auth_bp
    from .routes.deploy import deploy_bp
    from .routes.paste import paste_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(paste_bp, url_prefix="/api/paste")
    app.register_blueprint(deploy_bp, url_prefix="/api/deploy")

    # --- Health check + friendly root --------------------------------------
    @app.get("/")
    def index():
        return jsonify(service="PasteMaster API", status="ok")

    @app.get("/api/health")
    def health():
        return jsonify(status="ok")

    # --- Error handlers (always JSON) --------------------------------------
    @app.errorhandler(400)
    def bad_request(e):
        return jsonify(error=getattr(e, "description", "Bad request")), 400

    @app.errorhandler(404)
    def not_found(e):
        return jsonify(error="Not found"), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify(error="Content too large"), 413

    @app.errorhandler(429)
    def rate_limited(e):
        return jsonify(error="Too many requests, slow down"), 429

    @app.errorhandler(500)
    def server_error(e):
        return jsonify(error="Internal server error"), 500

    # Create tables on first boot (safe: no-op if they already exist).
    with app.app_context():
        db.create_all()

    return app
