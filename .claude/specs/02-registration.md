# Spec: Registration

## Overview
Implement user registration so new visitors can create an account on Spendly. The existing `register.html` template already renders a name/email/password form, but the `GET /register` route only renders it — there is no handler for the POST submission, no password hashing, and no session. This step adds the POST handler, a `create_user` helper in `database/db.py`, password hashing via `werkzeug.security`, server-side validation, and a redirect to `/login` on success after showing that user is created. Login, session persistence, and protected routes are deferred to later steps; this spec only covers **account creation**.

## Depends on
- **Step 1 — Database Setup** (complete). The `users` table exists with columns `id`, `name`, `email` (UNIQUE), `password_hash`, `created_at`. `get_db()` already sets `PRAGMA foreign_keys = ON`.

## Routes
- `POST /register` — accepts form fields `name`, `email`, `password`; validates, hashes the password, inserts a row into `users`, redirects to `/login` on success; re-renders `register.html` with an error message on failure — public
- `GET /register` — already implemented; the existing handler must split into `methods=["GET", "POST"]` so the same view serves both verbs — public

## Database changes
No schema changes. The `users` table from Step 1 already supports this feature.

One new helper in `database/db.py`:
- `create_user(name: str, email: str, password: str) -> int`
  - Hashes `password` with `werkzeug.security.generate_password_hash`
  - Inserts a row into `users` and returns the new `id`
  - Must use a **parameterised query** (`?` placeholders — never f-strings)
  - Must let the `UNIQUE` constraint on `email` raise so the caller can map it to a friendly error (do **not** pre-check with a SELECT — that creates a race condition)

## Templates
- **Modify:** `templates/register.html`
  - Change `<form method="POST" action="/register">` to use `{{ url_for('register') }}` (CLAUDE.md forbids hardcoded URLs)
  - No structural changes — the existing fields, labels, and `{% if error %}` block are already correct

## Files to change
- `app.py` — import `request`, `redirect`, `url_for`, `flash` from flask; import `werkzeug.security.generate_password_hash`; import `create_user` from `database/db`; split existing `register()` into GET/POST handlers with validation
- `database/db.py` — add `create_user()` helper; add `from werkzeug.security import generate_password_hash` import
- `templates/register.html` — replace hardcoded `action="/register"` with `url_for('register')`

## Files to create
None.

## New dependencies
No new dependencies. `werkzeug==3.1.6` is already in `requirements.txt` and exposes `generate_password_hash`.

## Rules for implementation
- No SQLAlchemy or ORMs — raw sqlite3 only
- Parameterised queries only (`?` placeholders) — never f-strings in SQL
- Passwords must be hashed with `werkzeug.security.generate_password_hash`; never store plaintext
- All templates extend `base.html` (already true for `register.html`)
- All internal links use `url_for()` — never hardcoded URLs
- CSS variables only (`--ink`, `--accent`, etc.) — never hardcode hex values in new styles
- DB logic lives in `database/db.py` only — routes must call helpers, never `sqlite3.connect` inline
- Use `abort()` for HTTP errors, not bare `return "error string"`
- One responsibility per route function — fetch data, render/redirect, done

## Definition of done
- [ ] Submitting valid name/email/password at `/register` creates a row in `users` with a hashed password (verifiable via `sqlite3 spendly.db "SELECT name, email FROM users WHERE email='…'"` — never query `password`)
- [ ] After successful registration, browser is redirected to `/login` (302)
- [ ] Submitting with any missing field re-renders `register.html` with a visible error message and **no** row is inserted
- [ ] Submitting an already-registered email re-renders `register.html` with a "Email already registered" message and **no** new row is inserted (the `UNIQUE` constraint is caught and translated, not allowed to 500)
- [ ] Submitting a password shorter than 8 characters re-renders `register.html` with a validation error (matches the "Min. 8 characters" placeholder hint)
- [ ] Email is trimmed and lowercased before insert so `"Alice@Example.com "` and `"alice@example.com"` collide on the UNIQUE constraint
- [ ] `register.html` form `action` uses `url_for('register')` (no hardcoded `/register`)
- [ ] No plaintext password appears anywhere in `spendly.db` (verify with `sqlite3 spendly.db "SELECT password_hash FROM users"`)
- [ ] App still boots on port 5001 with `python app.py` and `/` still renders the landing page
- [ ] No new pip packages installed; `requirements.txt` is unchanged
