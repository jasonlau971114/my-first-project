import sqlite3
from pathlib import Path

import pytest
from werkzeug.security import check_password_hash

import app as flask_app


def post_with_csrf(client, path, data=None):
    client.get(path)
    with client.session_transaction() as user_session:
        token = user_session["csrf_token"]
    return client.post(path, data={**(data or {}), "csrf_token": token})


def signup(client, name="Ada Lovelace", email="ada@example.com", password="correct-horse"):
    return post_with_csrf(
        client,
        "/signup",
        {"name": name, "email": email, "password": password},
    )


def test_registration_creates_hashed_account_and_starts_session(client, app):
    response = signup(client, email=" ADA@Example.com ")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    with app.app_context():
        user = flask_app.get_db().execute("SELECT * FROM users").fetchone()
    assert user["name"] == "Ada Lovelace"
    assert user["email"] == "ada@example.com"
    assert user["password_hash"] != "correct-horse"
    assert check_password_hash(user["password_hash"], "correct-horse")
    dashboard = client.get("/dashboard")
    assert b"Ada Lovelace" in dashboard.data


def test_validate_signup_returns_errors_or_empty_list():
    assert flask_app.validate_signup("Ada", "ada@example.com", "correct-horse") == []
    assert flask_app.validate_signup("", "bad-email", "short") == [
        "Enter your name (up to 80 characters).",
        "Enter a valid email address.",
        "Your password must be at least 8 characters.",
    ]


@pytest.mark.parametrize(
    ("name", "email", "password", "message"),
    [
        ("", "ada@example.com", "correct-horse", b"Enter your name"),
        ("A" * 81, "ada@example.com", "correct-horse", b"Enter your name"),
        ("Ada", "not-an-email", "correct-horse", b"Enter a valid email"),
        ("Ada", "a" * 250 + "@x.com", "correct-horse", b"Enter a valid email"),
        ("Ada", "ada@example.com", "short", b"at least 8 characters"),
        ("Ada", "ada@example.com", "p" * 129, b"128 characters or fewer"),
    ],
)
def test_registration_rejects_invalid_fields(client, name, email, password, message):
    response = signup(client, name=name, email=email, password=password)

    assert response.status_code == 200
    assert message in response.data


def test_registration_rejects_duplicate_email(client):
    signup(client)
    client.post("/logout", data={"csrf_token": _csrf(client, "/dashboard")})

    response = signup(client, name="Another Ada")

    assert response.status_code == 200
    assert b"already exists" in response.data


def test_signin_accepts_normalized_email(client):
    signup(client)
    client.post("/logout", data={"csrf_token": _csrf(client, "/dashboard")})

    response = post_with_csrf(
        client,
        "/signin",
        {"email": " ADA@EXAMPLE.COM ", "password": "correct-horse"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
    assert b"Ada Lovelace" in client.get("/dashboard").data


@pytest.mark.parametrize(
    ("email", "password"),
    [("ada@example.com", "wrong-password"), ("unknown@example.com", "correct-horse")],
)
def test_signin_rejects_unknown_or_incorrect_credentials(client, email, password):
    signup(client)
    client.post("/logout", data={"csrf_token": _csrf(client, "/dashboard")})

    response = post_with_csrf(client, "/signin", {"email": email, "password": password})

    assert response.status_code == 200
    assert b"wasn" in response.data
    assert client.get("/dashboard").status_code == 302


def test_dashboard_requires_authentication_and_redirects(client):
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/signin")


def test_home_redirects_anonymous_user_to_signin(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/signin")


def test_dashboard_clears_session_for_deleted_account(client):
    signup(client)
    with client.session_transaction() as user_session:
        user_session["user_id"] = 99999

    response = client.get("/dashboard")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/signin")
    with client.session_transaction() as user_session:
        assert "user_id" not in user_session


def test_logout_clears_session(client):
    signup(client)
    response = client.post("/logout", data={"csrf_token": _csrf(client, "/dashboard")})

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/signin")
    assert client.get("/dashboard").status_code == 302


def test_post_without_valid_csrf_token_is_rejected(client):
    response = client.post(
        "/signup", data={"name": "Ada", "email": "ada@example.com", "password": "correct-horse"}
    )

    assert response.status_code == 400
    with client.session_transaction() as user_session:
        assert "user_id" not in user_session


def test_signed_in_user_is_redirected_from_auth_pages_and_home(client):
    signup(client)

    assert client.get("/").headers["Location"].endswith("/dashboard")
    assert client.get("/signup").headers["Location"].endswith("/dashboard")
    assert client.get("/signin").headers["Location"].endswith("/dashboard")


def test_database_initialization_and_connection_are_reusable(app):
    flask_app.init_db()
    database_path = Path(app.config["DATABASE"])
    with app.app_context():
        first = flask_app.get_db()
        second = flask_app.get_db()
        first.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Grace", "grace@example.com", "hash"),
        )
        first.commit()
        user = second.execute("SELECT name FROM users WHERE email = ?", ("grace@example.com",)).fetchone()

    assert first is second
    assert isinstance(user, sqlite3.Row)
    assert user["name"] == "Grace"
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        first.execute("SELECT 1")

    # Windows refuses to remove an SQLite file while any connection holds it open.
    database_path.unlink()

def _csrf(client, path):
    client.get(path)
    with client.session_transaction() as user_session:
        return user_session["csrf_token"]
