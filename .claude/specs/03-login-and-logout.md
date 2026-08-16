# Spec: Login and Logout

## Overview
Implement the sign-in and sign-out flow for Spendly. After Step 2 (Registration) the `/register` POST handler creates a user, but no session is established — visitors can fill out `/register` and then cannot sign in. This step wires up the `POST /login` handler with credential verification via `werkzeug.security.check_password_hash`, establishes a server-side Flask session so the user stays signed in across requests, and implements `GET /logout` to clear the session. The post-login landing destination is `/` (the marketing landing page) — `/profile` and other protected routes arrive in later steps. A logged-in user sees their name and a "Sign out" link in the navbar instead of "Sign in / Get started".

## Depends on
- **Step 1 — Database Setup** (complete). The `users` table with `password_hash` exists; `get_db()` enforces `PRAGMA foreign_keys = ON`.
- **Step 2 — Registration** (complete). `database/db.create_user()` exists and the registration flow already normalises email to lowercase before insert, so the lookup here can do the same.

## Routes
- `POST /login` — accepts form fields `email` and `password`; looks the user up by normalised email, verifies the password with `werkzeug.security.check_password_hash`, stores `user_id` in the Flask session on success, redirects to `/`; re-renders `login.html` with an error message on failure — public
- `GET /login` — already implemented as a stub; the existing handler must split into `methods=["GET", "POST"]` so the same view serves both verbs — public
- `GET /logout` — replace the stub `return "Logout — coming in Step 3"`; clears the Flask session via `session.clear()`, then redirects to `/` — public (idempotent: signing out when already signed out is fine)

## Database changes
No schema changes.

One new helper in `database/db.py`:
- `find_user_by_email(email: str) -> sqlite3.Row | None`
  - Returns the row for the given email, or `None` if no match
  - Must use a **parameterised query** (`?` placeholders — never f-strings)
  - Caller is responsible for normalising email (lowercasing) before calling

The route itself should call `werkzeug.security.check_password_hash` — that verification does **not** belong in `database/db.py` because it is auth-layer logic, not data access. Keeping `db.py` free of `check_password_hash` preserves the single-responsibility split the registration spec established.

## Templates
- **Modify:** `templates/login.html`
  - Change `<form method="POST" action="/login">` to use `{{ url_for('login') }}` (CLAUDE.md forbids hardcoded URLs)
  - No structural changes — the existing fields, labels, and `{% if error %}` block are already correct
- **Modify:** `templates/base.html`
  - The navbar needs to react to session state:
    - When `session.get('user_id')` is set: show the user's name and a "Sign out" link pointing to `{{ url_for('logout') }}` instead of "Sign in" / "Get started"
    - When not set: render the existing "Sign in" / "Get started" links unchanged
  - The user's display name should be passed in via `render_template(..., user_name=...)` from each route, **not** queried inline in `base.html` (keep DB access in routes, not templates)
  - This is the first template that branches on auth state, so the conditional lives inline in `base.html` — do not introduce a `_navbar.html` partial just for this

## Files to change
- `app.py`
  - Import `session` from `flask`
  - Import `check_password_hash` from `werkzeug.security`
  - Import `find_user_by_email` from `database/db`
  - Add `app.secret_key = ...` (read from env var `SPENDLY_SECRET_KEY` with a dev fallback) — Flask sessions require a secret key
  - Split existing `login()` into GET/POST handlers with validation and credential check
  - Replace `logout()` stub with `session.clear()` + `redirect(url_for('landing'))`
  - All existing routes that render templates need to pass the current user's name to the template (via a small helper, see below) so the navbar can render the right state
- `database/db.py` — add `find_user_by_email()` helper
- `templates/login.html` — replace hardcoded `action="/login"` with `url_for('login')`
- `templates/base.html` — branch the navbar links on `session.get('user_id')`

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug==3.1.6` already exposes `check_password_hash`.

## Rules for implementation
- No SQLAlchemy or ORMs — raw sqlite3 only
- Parameterised queries only (`?` placeholders) — never f-strings in SQL
- Password verification must use `werkzeug.security.check_password_hash`; never compare plaintext or use a custom hash
- All templates extend `base.html` (already true for `login.html`)
- All internal links use `url_for()` — never hardcoded URLs
- CSS variables only (`--ink`, `--accent`, etc.) — never hardcode hex values in new styles
- DB logic lives in `database/db.py` only — routes must call helpers, never `sqlite3.connect` inline
- `check_password_hash` belongs in the route (auth layer), not in `database/db.py` (data layer)
- Use `abort()` for HTTP errors, not bare `return "error string"`
- One responsibility per route function — fetch data, render/redirect, done
- Flask session, not JWT or signed cookies — keep the auth model simple
- Email is trimmed and lowercased before lookup (matches the registration normalisation)
- Use a single response status convention: render the form with status `400` on credential failure (mirrors the registration spec) — 200 on success is handled by the redirect
- Do **not** introduce a `_navbar.html` partial or a `@app.context_processor` for `user_name` — pass `user_name=...` from each route explicitly. With only 6 routes today, the explicit approach stays simple; if route count grows, that is a refactor for a later step.

## Definition of done
- [ ] Submitting a valid email/password at `/login` redirects to `/` (302) and a Flask session cookie is set
- [ ] After signing in, the navbar on every page shows the signed-in user's name and a "Sign out" link (instead of "Sign in / Get started") — verifiable on `/`, `/login`, and any other page that extends `base.html`
- [ ] Submitting an unknown email re-renders `login.html` with a generic "Invalid email or password" message and **no** session is created
- [ ] Submitting a known email with the wrong password re-renders `login.html` with the same generic "Invalid email or password" message (do **not** leak which field was wrong) and **no** session is created
- [ ] Submitting with either field blank re-renders `login.html` with a validation error and **no** session is created
- [ ] Case-insensitive login: a user registered as `Alice@Example.com` can sign in with `alice@example.com` (matches the registration normalisation)
- [ ] `GET /logout` when signed in clears the session and redirects to `/`; the navbar reverts to "Sign in / Get started" on the next page load
- [ ] `GET /logout` when not signed in is a safe no-op (still redirects to `/`, does not raise)
- [ ] `login.html` form `action` uses `url_for('login')` (no hardcoded `/login`)
- [ ] No password hash or plaintext password appears in any response body or cookie value (verify with browser devtools — the cookie should be the opaque Flask session cookie, not a JWT or plaintext token)
- [ ] App still boots on port 5001 with `python app.py` and `/` still renders the landing page
- [ ] No new pip packages installed; `requirements.txt` is unchanged
