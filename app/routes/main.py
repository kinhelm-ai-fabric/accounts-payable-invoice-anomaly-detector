import logging

from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user

from app import db
from app.models import Invoice, Anomaly, Vendor

logger = logging.getLogger(__name__)

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def dashboard():
    try:
        total_invoices = Invoice.query.count()
        flagged_invoices = Invoice.query.filter_by(status="flagged").count()
        pending_invoices = Invoice.query.filter_by(status="pending").count()
        total_anomalies = Anomaly.query.filter_by(resolved=False).count()

        recent_anomalies = (
            Anomaly.query
            .filter_by(resolved=False)
            .order_by(Anomaly.created_at.desc())
            .limit(10)
            .all()
        )

        recent_invoices = (
            Invoice.query
            .order_by(Invoice.created_at.desc())
            .limit(10)
            .all()
        )

        severity_counts = {
            "critical": Anomaly.query.filter_by(severity="critical", resolved=False).count(),
            "high": Anomaly.query.filter_by(severity="high", resolved=False).count(),
            "medium": Anomaly.query.filter_by(severity="medium", resolved=False).count(),
            "low": Anomaly.query.filter_by(severity="low", resolved=False).count(),
        }
    except Exception as exc:
        logger.exception("dashboard: service error -- %s", exc)
        return render_template("errors/500.html"), 500

    return render_template(
        "main/dashboard.html",
        total_invoices=total_invoices,
        flagged_invoices=flagged_invoices,
        pending_invoices=pending_invoices,
        total_anomalies=total_anomalies,
        recent_anomalies=recent_anomalies,
        recent_invoices=recent_invoices,
        severity_counts=severity_counts,
    )


@main_bp.route("/getting-started")
@login_required
def getting_started():
    return render_template("main/getting_started.html")


@main_bp.route("/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "ok"}), 200
    except Exception as exc:
        logger.exception("health: database check failed -- %s", exc)
        return jsonify({"status": "unhealthy", "database": str(exc)}), 503


@main_bp.route("/api/theme", methods=["POST"])
@login_required
def set_theme():
    try:
        data = request.get_json(silent=True) or {}
        theme = data.get("theme", "light")
        if theme not in ("light", "dark"):
            theme = "light"
        current_user.theme = theme
        db.session.commit()
        return jsonify({"ok": True, "theme": theme})
    except Exception as exc:
        logger.exception("set_theme: error -- %s", exc)
        db.session.rollback()
        return jsonify({"error": "Failed to set theme"}), 500
