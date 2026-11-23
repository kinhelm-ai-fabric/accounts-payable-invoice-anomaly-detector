import os
import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()
login_manager = LoginManager()

logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)

    # --- Core config ---
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(32).hex())
    app.config["SESSION_COOKIE_NAME"] = "ap_anomaly_session"
    app.config["SESSION_COOKIE_PATH"] = os.environ.get("SESSION_COOKIE_PATH", "/")
    app.config["SESSION_COOKIE_SECURE"] = os.environ.get(
        "SESSION_COOKIE_SECURE", "false"
    ).lower() in ("true", "1", "yes")
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # --- Database ---
    data_dir = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(os.path.abspath(data_dir), "app.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --- Proxy ---
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # --- Extensions ---
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # --- Blueprints ---
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.invoices import invoices_bp
    from app.routes.analysis import analysis_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(analysis_bp)

    # --- Create tables ---
    with app.app_context():
        from app import models  # noqa: F401
        db.create_all()
        _seed_demo_data(app)

    return app


def _seed_demo_data(app):
    """Seed demo data idempotently -- safe with multiple workers."""
    from app.models import User, Vendor
    from werkzeug.security import generate_password_hash

    try:
        if User.query.filter_by(username="admin").first():
            return

        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("admin"),
            is_admin=True,
        )
        db.session.add(admin)

        demo_vendors = [
            Vendor(name="Acme Corp", code="ACME-001"),
            Vendor(name="Globex Inc", code="GLOB-002"),
            Vendor(name="Initech LLC", code="INIT-003"),
            Vendor(name="Umbrella Co", code="UMBR-004"),
            Vendor(name="Stark Industries", code="STRK-005"),
        ]
        for v in demo_vendors:
            if not Vendor.query.filter_by(code=v.code).first():
                db.session.add(v)

        db.session.commit()
        logger.info("Demo data seeded successfully.")
    except Exception:
        db.session.rollback()
        logger.debug("Seed skipped -- data may already exist.")
