import logging
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app import db
from app.models import Invoice, Vendor, Anomaly
from app.services.anomaly_service import analyze_invoice

logger = logging.getLogger(__name__)

analysis_bp = Blueprint("analysis", __name__, url_prefix="/analysis")


@analysis_bp.route("/")
@login_required
def analysis_overview():
    try:
        anomalies = (
            Anomaly.query
            .order_by(Anomaly.resolved.asc(), Anomaly.created_at.desc())
            .all()
        )
        severity_counts = {
            "critical": sum(1 for a in anomalies if a.severity == "critical" and not a.resolved),
            "high": sum(1 for a in anomalies if a.severity == "high" and not a.resolved),
            "medium": sum(1 for a in anomalies if a.severity == "medium" and not a.resolved),
            "low": sum(1 for a in anomalies if a.severity == "low" and not a.resolved),
        }
    except Exception as exc:
        logger.exception("analysis_overview: error -- %s", exc)
        return render_template("errors/500.html"), 500

    return render_template(
        "analysis/overview.html",
        anomalies=anomalies,
        severity_counts=severity_counts,
    )


@analysis_bp.route("/run/<int:invoice_id>", methods=["POST"])
@login_required
def run_analysis(invoice_id):
    try:
        invoice = db.session.get(Invoice, invoice_id)
    except Exception as exc:
        logger.exception("run_analysis: db error -- %s", exc)
        if _is_ajax(request):
            return jsonify({"error": "Database error", "detail": str(exc)}), 500
        flash("Database error.", "danger")
        return redirect(url_for("invoices.list_invoices"))

    if invoice is None:
        if _is_ajax(request):
            return jsonify({"error": "Invoice not found"}), 404
        flash("Invoice not found.", "warning")
        return redirect(url_for("invoices.list_invoices"))

    try:
        vendor = db.session.get(Vendor, invoice.vendor_id)
        historical = (
            Invoice.query
            .filter_by(vendor_id=invoice.vendor_id)
            .filter(Invoice.id != invoice.id)
            .order_by(Invoice.invoice_date.desc())
            .limit(50)
            .all()
        )
        findings = analyze_invoice(invoice, vendor, historical)
    except Exception as exc:
        logger.exception("run_analysis: analysis error -- %s", exc)
        if _is_ajax(request):
            return jsonify({"error": "Analysis failed", "detail": str(exc)}), 500
        flash(f"Analysis failed: {exc}", "danger")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))

    try:
        # Clear previous unresolved anomalies for this invoice
        Anomaly.query.filter_by(invoice_id=invoice.id, resolved=False).delete()

        for f in findings:
            anomaly = Anomaly(
                invoice_id=invoice.id,
                anomaly_type=f["anomaly_type"],
                severity=f["severity"],
                description=f["description"],
                confidence=f.get("confidence"),
                recommendation=f.get("recommendation", ""),
            )
            db.session.add(anomaly)

        if findings:
            invoice.status = "flagged"
        elif invoice.status == "flagged":
            invoice.status = "pending"

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.exception("run_analysis: save error -- %s", exc)
        if _is_ajax(request):
            return jsonify({"error": "Failed to save results", "detail": str(exc)}), 500
        flash("Failed to save analysis results.", "danger")
        return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))

    if _is_ajax(request):
        return jsonify({"ok": True, "anomalies_found": len(findings)})

    if findings:
        flash(f"Analysis complete: {len(findings)} anomaly(ies) detected.", "warning")
    else:
        flash("Analysis complete: no anomalies detected.", "success")
    return redirect(url_for("invoices.view_invoice", invoice_id=invoice_id))


@analysis_bp.route("/resolve/<int:anomaly_id>", methods=["POST"])
@login_required
def resolve_anomaly(anomaly_id):
    try:
        anomaly = db.session.get(Anomaly, anomaly_id)
    except Exception as exc:
        logger.exception("resolve_anomaly: db error -- %s", exc)
        return jsonify({"error": "Database error"}), 500

    if anomaly is None:
        return jsonify({"error": "Anomaly not found"}), 404

    try:
        anomaly.resolved = True
        anomaly.resolved_by = current_user.id
        anomaly.resolved_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"ok": True})
    except Exception as exc:
        db.session.rollback()
        logger.exception("resolve_anomaly: commit error -- %s", exc)
        return jsonify({"error": "Failed to resolve anomaly"}), 500


@analysis_bp.route("/run-all", methods=["POST"])
@login_required
def run_all_analysis():
    try:
        pending = Invoice.query.filter_by(status="pending").all()
        total_findings = 0
        analyzed = 0

        for invoice in pending:
            vendor = db.session.get(Vendor, invoice.vendor_id)
            if vendor is None:
                continue
            historical = (
                Invoice.query
                .filter_by(vendor_id=invoice.vendor_id)
                .filter(Invoice.id != invoice.id)
                .order_by(Invoice.invoice_date.desc())
                .limit(50)
                .all()
            )
            findings = analyze_invoice(invoice, vendor, historical)

            Anomaly.query.filter_by(invoice_id=invoice.id, resolved=False).delete()
            for f in findings:
                db.session.add(Anomaly(
                    invoice_id=invoice.id,
                    anomaly_type=f["anomaly_type"],
                    severity=f["severity"],
                    description=f["description"],
                    confidence=f.get("confidence"),
                    recommendation=f.get("recommendation", ""),
                ))
            if findings:
                invoice.status = "flagged"
            total_findings += len(findings)
            analyzed += 1

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        logger.exception("run_all_analysis: error -- %s", exc)
        if _is_ajax(request):
            return jsonify({"error": "Batch analysis failed", "detail": str(exc)}), 500
        flash("Batch analysis failed.", "danger")
        return redirect(url_for("analysis.analysis_overview"))

    if _is_ajax(request):
        return jsonify({"ok": True, "analyzed": analyzed, "anomalies_found": total_findings})

    flash(f"Analyzed {analyzed} invoices. {total_findings} anomaly(ies) found.", "info")
    return redirect(url_for("analysis.analysis_overview"))


def _is_ajax(req):
    return (
        req.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in (req.headers.get("Accept") or "")
    )
