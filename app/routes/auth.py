import logging

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash

from app import db
from app.models import User

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        try:
            user = User.query.filter_by(username=username).first()
        except Exception as exc:
            logger.exception("login: database error -- %s", exc)
            flash("An error occurred. Please try again.", "danger")
            return render_template("auth/login.html"), 500

        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html")

        login_user(user)
        next_page = request.args.get("next") or request.form.get("next") or url_for("main.dashboard")
        return redirect(next_page)

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("auth/register.html")

        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("auth/register.html")

        try:
            if User.query.filter_by(username=username).first():
                flash("Username already exists.", "danger")
                return render_template("auth/register.html")
            if User.query.filter_by(email=email).first():
                flash("Email already registered.", "danger")
                return render_template("auth/register.html")

            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            logger.exception("register: error -- %s", exc)
            flash("An error occurred. Please try again.", "danger")
            return render_template("auth/register.html"), 500

        flash("Account created. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "info")
    return redirect(url_for("auth.login"))
