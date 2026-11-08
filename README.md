# Morrow sign-in project

A small Python and Flask web app with account creation, sign-in, and a protected account page. Accounts are stored in SQLite and passwords are hashed with Werkzeug.

## Run locally

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m flask --app app run --debug
```

Open <http://127.0.0.1:5000>. The SQLite database is created in `instance/accounts.sqlite3` the first time the app runs.

## Run tests and view coverage

Install the dependencies above, then run:

```powershell
py -m pytest
```

Pytest runs the automated suite and creates a terminal summary, an HTML report at `coverage_html/index.html`, and an XML report at `coverage.xml`. The HTML report shows covered and uncovered lines and branches for `app.py`.

## Configuration

- Set `SECRET_KEY` to a long, random value for deployments. If unset, a temporary key is generated when the app starts, so active sessions are cleared on restart.
- Set `DATABASE_PATH` to change the SQLite database location.
- Set `COOKIE_SECURE=1` when serving over HTTPS.
- Debug mode is off by default. Use Flask's development server only for local development; deploy behind a production WSGI server for public use.

