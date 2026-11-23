from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash

from app import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    theme = db.Column(db.String(10), default="light")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Vendor(db.Model):
    __tablename__ = "vendors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    invoices = db.relationship("Invoice", backref="vendor", lazy="dynamic")


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(100), unique=True, nullable=False, index=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey("vendors.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default="USD")
    invoice_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="pending")  # pending, approved, flagged, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    anomalies = db.relationship("Anomaly", backref="invoice", lazy="dynamic")


class Anomaly(db.Model):
    __tablename__ = "anomalies"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    anomaly_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # low, medium, high, critical
    description = db.Column(db.Text, nullable=False)
    confidence = db.Column(db.Float, nullable=True)
    recommendation = db.Column(db.Text, nullable=True)
    resolved = db.Column(db.Boolean, default=False)
    resolved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
