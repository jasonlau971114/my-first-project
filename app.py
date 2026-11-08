import os
import re
import secrets
import sqlite3
from contextlib import closing
from functools import wraps
from pathlib import Path

from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
INSTANCE_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    DATABASE=os.environ.get("DATABASE_PATH", str(INSTANCE_DIR / "accounts.sqlite3")),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "").lower() in {"1", "true", "yes"},
)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(app.config["DATABASE"])) as db:
        with db:
            db.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )


init_db()


@app.before_request
def prepare_request():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    if request.method == "POST":
        supplied = request.form.get("csrf_token", "")
        if not secrets.compare_digest(supplied, session["csrf_token"]):
            abort(400, description="Your form expired. Please go back, refresh, and try again.")


@app.context_processor
def inject_csrf_token():
    return {"csrf_token": session.get("csrf_token", "")}


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "info")
            return redirect(url_for("signin"))
        return view(*args, **kwargs)

    return wrapped_view


@app.get("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("signin"))


def validate_signup(name, email, password):
    """Return validation messages for sign-up fields, or an empty list if valid."""
    errors = []
    if not name or len(name) > 80:
        errors.append("Enter your name (up to 80 characters).")
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        errors.append("Enter a valid email address.")
    if len(password) < 8:
        errors.append("Your password must be at least 8 characters.")
    if len(password) > 128:
        errors.append("Your password must be 128 characters or fewer.")
    return errors


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        errors = validate_signup(name, email, password)
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("signup.html", name=name, email=email)

        try:
            cursor = get_db().execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, generate_password_hash(password)),
            )
            get_db().commit()
        except sqlite3.IntegrityError:
            flash("An account with that email already exists. Try signing in.", "error")
            return render_template("signup.html", name=name, email=email)

        session.clear()
        session["user_id"] = cursor.lastrowid
        session["csrf_token"] = secrets.token_urlsafe(32)
        flash("Your account is ready. Welcome!", "success")
        return redirect(url_for("dashboard"))
    return render_template("signup.html", name="", email="")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("That email and password combination wasn’t recognized.", "error")
            return render_template("signin.html", email=email)
        session.clear()
        session["user_id"] = user["id"]
        session["csrf_token"] = secrets.token_urlsafe(32)
        flash(f"Welcome back, {user['name']}!", "success")
        return redirect(url_for("dashboard"))
    return render_template("signin.html", email="")


@app.get("/dashboard")
@login_required
def dashboard():
    user = get_db().execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    if user is None:
        session.clear()
        return redirect(url_for("signin"))
    return render_template("dashboard.html", user=user)


@app.post("/logout")
@login_required
def logout():
    session.clear()
    flash("You’ve been signed out.", "info")
    return redirect(url_for("signin"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"})  # pragma: no cover
