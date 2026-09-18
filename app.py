from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
import os
import sqlite3
from database.db import (
    init_db, seed_db, create_user,
    find_user_by_email, find_user_by_id,
    get_user_profile, get_user_stats,
    get_recent_transactions, get_category_totals
)

app = Flask(__name__)
app.secret_key = os.environ.get("SPENDLY_SECRET_KEY", "dev-secret-change-me")


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def current_user_name():
    """Return the signed-in user's name, or None. Short-circuits on no session
    so anonymous traffic never touches the DB."""
    user_id = session.get("user_id")
    if user_id is None:
        return None
    user = find_user_by_id(user_id)
    return user["name"] if user else None


def format_pkr(amount):
    """Format a number as a PKR currency string."""
    return f"₨ {amount:,.2f}"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html", user_name=current_user_name())


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id") is not None:
        return redirect(url_for("landing"))
    if request.method == "POST":
        name     = request.form.get("name", "").strip()
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            error = "All fields are required."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif "@" not in email or "." not in email:
            error = "Please enter a valid email address."
        else:
            try:
                create_user(name, email, password)
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                error = "Email already registered."

        return render_template("register.html", error=error, user_name=current_user_name()), 400

    return render_template("register.html", user_name=current_user_name())


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id") is not None:
        return redirect(url_for("landing"))
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            error = "Email and password are required."
            return render_template("login.html", error=error, user_name=current_user_name()), 400

        user = find_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Invalid email or password."
            return render_template("login.html", error=error, user_name=current_user_name()), 400

        session["user_id"] = user["id"]
        return redirect(url_for("profile"))

    return render_template("login.html", user_name=current_user_name())


@app.route("/terms")
def terms():
    return render_template("terms.html", user_name=current_user_name())


@app.route("/privacy")
def privacy():
    return render_template("privacy.html", user_name=current_user_name())


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

# TODO: move to POST with a CSRF token before any production deployment —
# GET-based state changes are a CSRF risk.
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    # 1. User Profile
    profile_data = get_user_profile(user_id)
    if not profile_data:
        abort(404)

    # Format joined date: "2026-09-18 10:00:00" -> "September 2026"
    import datetime
    created_at = profile_data["created_at"]
    try:
        dt = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        dt = datetime.datetime.now()

    user = {
        "name": profile_data["name"],
        "email": profile_data["email"],
        "joined": dt.strftime("%B %Y"),
    }

    # 2. Summary Stats
    stats_data = get_user_stats(user_id)
    stats = {
        "total_spent": format_pkr(stats_data["total_spent"]),
        "transaction_count": stats_data["transaction_count"],
        "top_category": stats_data["top_category"],
    }

    # 3. Recent Transactions
    tx_data = get_recent_transactions(user_id)
    transactions = [
        {
            "date": tx["date"],
            "desc": tx["description"],
            "cat": tx["category"],
            "amt": format_pkr(tx["amount"]),
        }
        for tx in tx_data
    ]

    # 4. Category Breakdown
    cat_data = get_category_totals(user_id)
    total_all = sum(c["total"] for c in cat_data)

    categories = []
    for c in cat_data:
        percent = 0
        if total_all > 0:
            percent = round((c["total"] / total_all) * 100)

        categories.append({
            "name": c["category"],
            "total": format_pkr(c["total"]),
            "percent": percent,
        })

    # Fix rounding remainder to ensure sum is 100%
    if categories:
        diff = 100 - sum(c["percent"] for c in categories)
        categories[0]["percent"] += diff

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
        user_name=current_user_name(),
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
