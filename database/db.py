import sqlite3
from werkzeug.security import generate_password_hash

def get_db():
    """Open connection to spendly.db with row_factory and foreign keys enabled."""
    conn = sqlite3.connect('spendly.db')
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn

def init_db():
    """Create tables using CREATE TABLE IF NOT EXISTS."""
    conn = get_db()
    try:
        # Create users table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        ''')

        # Create expenses table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')

        conn.commit()
    finally:
        conn.close()

def create_user(name, email, password):
    """Hash password with werkzeug, insert user row, return new id.
    Lets sqlite3.IntegrityError (from email UNIQUE) propagate to caller."""
    conn = get_db()
    try:
        password_hash = generate_password_hash(password)
        cursor = conn.execute(
            'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
            (name, email, password_hash)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def find_user_by_email(email):
    """Return the user row matching email, or None. Caller normalises email."""
    conn = get_db()
    try:
        cursor = conn.execute(
            'SELECT id, name, email, password_hash FROM users WHERE email = ? LIMIT 1',
            (email,)
        )
        return cursor.fetchone()
    finally:
        conn.close()

def find_user_by_id(user_id):
    """Return the user row matching id, or None."""
    conn = get_db()
    try:
        cursor = conn.execute(
            'SELECT id, name, email, password_hash FROM users WHERE id = ? LIMIT 1',
            (user_id,)
        )
        return cursor.fetchone()
    finally:
        conn.close()


def get_user_profile(user_id):
    """Return name, email, and created_at for the user."""
    conn = get_db()
    try:
        cursor = conn.execute(
            'SELECT name, email, created_at FROM users WHERE id = ?',
            (user_id,)
        )
        return cursor.fetchone()
    finally:
        conn.close()


def get_user_stats(user_id):
    """Return total spent, transaction count, and top category for the user."""
    conn = get_db()
    try:
        # Get basic stats
        stats = conn.execute(
            'SELECT SUM(amount) as total, COUNT(*) as count FROM expenses WHERE user_id = ?',
            (user_id,)
        ).fetchone()

        # Get top category
        top_cat = conn.execute(
            'SELECT category FROM expenses WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1',
            (user_id,)
        ).fetchone()

        return {
            "total_spent": stats["total"] if stats["total"] else 0.0,
            "transaction_count": stats["count"] if stats["count"] else 0,
            "top_category": top_cat["category"] if top_cat else "—"
        }
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=5):
    """Return the most recent expenses for the user."""
    conn = get_db()
    try:
        cursor = conn.execute(
            'SELECT date, description, category, amount FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT ?',
            (user_id, limit)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_category_totals(user_id):
    """Return total spent per category for the user."""
    conn = get_db()
    try:
        cursor = conn.execute(
            'SELECT category, SUM(amount) as total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC',
            (user_id,)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def seed_db():
    """Insert sample data for development, but only if users table is empty."""
    conn = get_db()
    try:
        # Check if we already have users
        cursor = conn.execute('SELECT COUNT(*) FROM users')
        count = cursor.fetchone()[0]

        if count > 0:
            # Data already seeded, return early
            return

        # Insert demo user
        user_id = create_user('Demo User', 'demo@spendly.com', 'demo123')

        # Sample expenses data
        # Format: (amount, category, date, description)
        sample_expenses = [
            (12.50, 'Food', '2026-08-05', 'Lunch at cafe'),
            (45.00, 'Transport', '2026-08-03', 'Taxi ride to airport'),
            (89.99, 'Bills', '2026-08-01', 'Electricity bill'),
            (25.00, 'Health', '2026-08-04', 'Pharmacy purchase'),
            (30.00, 'Entertainment', '2026-08-06', 'Movie tickets'),
            (120.00, 'Shopping', '2026-08-02', 'New clothes'),
            (10.00, 'Other', '2026-08-07', 'Donation'),
            (7.50, 'Food', '2026-08-08', 'Coffee and pastry')
        ]

        # Insert sample expenses
        for amount, category, date, description in sample_expenses:
            conn.execute(
                'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
                (user_id, amount, category, date, description)
            )

        conn.commit()
    finally:
        conn.close()