# Test and coverage report

**Run date:** 2026-11-08  
**Command:** `py -m pytest`  
**Result:** 19 passed

## Coverage

| File | Statements | Covered | Branches | Covered | Coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| `app.py` | 122 | 122 | 38 | 38 | 100% |

The development server launcher under `if __name__ == "__main__"` is excluded from measurement. The measured application logic has no uncovered statements or branches in this run.

## Scenarios exercised

- Account registration, `validate_signup` input checks, duplicate email handling, and password hashing
- Sign-in with normalized email, incorrect passwords, and unknown accounts
- Dashboard access rules, including a session referencing a deleted account
- Logout and CSRF rejection
- Database initialization, row access, connection reuse, and app home redirects

## Generated artifacts

- `coverage_html/index.html` — interactive line and branch coverage report
- `coverage.xml` — machine-readable coverage report

Run `py -m pytest` again after changing the application or tests to refresh both reports and this summary's figures.
