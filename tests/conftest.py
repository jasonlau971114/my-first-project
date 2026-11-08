import pytest

import app as flask_app


@pytest.fixture
def app(tmp_path):
    original_config = {
        "DATABASE": flask_app.app.config["DATABASE"],
        "SECRET_KEY": flask_app.app.config["SECRET_KEY"],
        "TESTING": flask_app.app.config["TESTING"],
    }
    database_path = tmp_path / "test_accounts.sqlite3"
    flask_app.app.config.update(
        TESTING=True,
        SECRET_KEY="pytest-session-secret",
        DATABASE=str(database_path),
    )
    flask_app.init_db()
    yield flask_app.app
    flask_app.app.config.update(original_config)


@pytest.fixture
def client(app):
    return app.test_client()
