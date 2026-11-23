import csv
import io
import logging
from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app import db
from app.models import Invoice, Vendor, Anomaly

logger = logging.getLogger(__name__)

invoices_bp = Blueprint("invoices", __name__, url_prefix="/invoices")


@invoices_bp.route("/")
@login_required
def list_invoices():
    try:
        page = request.args.get("page", 1, type=int)
        status_filter = request.args.get("status", "")
        query = Invoice.query.order_by(Invoice.created_at.desc())
        if status_filter:
            query = query.filter_by(status=status_filter)
        pagination = query.paginate(page=page, per_page=20, error_out=False)
        invoices = pagination.items
    except Exception as exc:
        logger.exception("list_invoices: error -- %s", exc)
        return render_template("errors/500.html"), 500

    return render_template(
        "invoices/list.html",
        invoices=invoices,
        pagination=pagination,
        status_filter=status_filter,
    )


@invoices_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_invoice():
    try:
        vendors = Vendor.query.order_by(Vendor.name).all()
    except Exception as exc:
        logger.exception("create_invoice: vendor load error -- %s", exc)
        return render_template("errors/500.html"), 500

    if request.method == "POST":
        try:
            invoice_number = request.form.get("invoice_number", "").strip()
            vendor_id = request.form.get("vendor_id", type=int)
            amount = request.form.get("amount", type=float)
            currency = request.form.get("currency", "USD").strip().upper()
            invoice_date_str = request.form.get("invoice_date", "")
            due_date_str = request.form.get("due_date", "")
            description = request.form.get("description", "").strip()

            if not invoice_number or not vendor_id or amount is None or not invoice_date_str:
                flash("Invoice number, vendor, amount, and date are required.", "danger")
                return render_template("invoices/form.html", vendors=vendors, invoice=None)

            if Invoice.query.filter_by(invoice_number=invoice_number).first():
                flash("Invoice number already exists.", "danger")
                return render_template("invoices/form.html", vendors=vendors, invoice=None)

            invoice_date = datetime.strptime(invoice_date_str, "%Y-%m-%d").date()
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date() if due_date_str else None

            invoice = Invoice(
                invoice_number=invoice_number,
                vendor_id=vendor_id,
                amount=amount,
                currency=currency,
                invoice_date=invoice_date,
                due_date=due_date,
                description=description,
                status="pending",
                created_by=current_user.id,
            )
            db.session.add(invoice)
            db.session.commit()

            flash("Invoice created.", "success")
            return redirect(url_for("invoices.view_invoice", invoice_id=invoice.id))
        except Exception as exc:
            db.session.rollback()
            logger.exception("create_invoice: error -- %s", exc)
            flash("Failed to create invoice.", "danger")
            return render_template("invoices/form.html", vendors=vendors, invoice=None)

    return render_template("invoices/form.html", vendors=vendors, invoice=None)


@invoices_bp.route("/<int:invoice_id>")
@login_required
def view_invoice(invoice_id):
    try:
        invoice = db.session.get(Invoice, invoice_id)
    except Exception as exc:
        logger.exception("view_invoice: error -- %s", exc)
        return render_template("errors/500.html"), 500

    if invoice is None:
        flash("Invoice not found.", "warning")
        return redirect(url_for("invoices.list_invoices"))

    try:
        anomalies = Anomaly.query.filter_by(invoice_id=invoice.id).order_by(Anomaly.severity.desc()).all()
    except Exception as exc:
        logger.exception("view_invoice: anomaly load error -- %s", exc)
        anomalies = []

    return render_template("invoices/detail.html", invoice=invoice, anomalies=anomalies)


@invoices_bp.route("/upload", methods=["GET", "POST"])
@login_required
def upload_csv():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename.endswith(".csv"):
            flash("Please upload a valid CSV file.", "danger")
            return render_template("invoices/upload.html")

        try:
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
            reader = csv.DictReader(stream)
            count = 0
            skipped = 0

            for row in reader:
                inv_num = row.get("invoice_number", "").strip()
                if not inv_num:
                    skipped += 1
                    continue
                if Invoice.query.filter_by(invoice_number=inv_num).first():
                    skipped += 1
                    continue

                vendor_code = row.get("vendor_code", "").strip()
                vendor = Vendor.query.filter_by(code=vendor_code).first()
                if not vendor:
                    vendor = Vendor(name=row.get("vendor_name", vendor_code), code=vendor_code or f"AUTO-{inv_num}")
                    db.session.add(vendor)
                    db.session.flush()

                try:
                    amount = float(row.get("amount", 0))
                except (ValueError, TypeError):
                    amount = 0.0

                try:
                    inv_date = datetime.strptime(row.get("invoice_date", ""), "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    inv_date = datetime.utcnow().date()

                due_date = None
                if row.get("due_date"):
                    try:
                        due_date = datetime.strptime(row["due_date"], "%Y-%m-%d").date()
                    except (ValueError, TypeError):
                        pass

                invoice = Invoice(
                    invoice_number=inv_num,
                    vendor_id=vendor.id,
                    amount=amount,
                    currency=row.get("currency", "USD").strip().upper() or "USD",
                    invoice_date=inv_date,
                    due_date=due_date,
                    description=row.get("description", ""),
                    status="pending",
                    created_by=current_user.id,
                )
                db.session.add(invoice)
                count += 1

            db.session.commit()
            flash(f"Imported {count} invoices ({skipped} skipped).", "success")
            return redirect(url_for("invoices.list_invoices"))
        except Exception as exc:
            db.session.rollback()
            logger.exception("upload_csv: error -- %s", exc)
            flash(f"Import failed: {exc}", "danger")

    return render_template("invoices/upload.html")


@invoices_bp.route("/<int:invoice_id>/status", methods=["POST"])
@login_required
def update_status(invoice_id):
    try:
        invoice = db.session.get(Invoice, invoice_id)
    except Exception as exc:
        logger.exception("update_status: error -- %s", exc)
        return jsonify({"error": "Database error"}), 500

    if invoice is None:
        return jsonify({"error": "Invoice not found"}), 404

    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in ("pending", "approved", "flagged", "rejected"):
        return jsonify({"error": "Invalid status"}), 400

    try:
        invoice.status = new_status
        db.session.commit()
        return jsonify({"ok": True, "status": new_status})
    except Exception as exc:
        db.session.rollback()
        logger.exception("update_status: commit error -- %s", exc)
        return jsonify({"error": "Failed to update status"}), 500
