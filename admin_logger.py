import sqlite3
from datetime import datetime


def log_activity(user_email: str, action: str, details: str = "", status: str = "success"):
    """Log any system activity to the activity_logs table."""
    try:
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute(
            "INSERT INTO activity_logs (user_email, action, details, status) VALUES (?, ?, ?, ?)",
            (user_email, action, details, status)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[Logger Error] {e}")


def log_api_usage(user_email: str, api_type: str):
    """Log API usage for monitoring."""
    try:
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute(
            "INSERT INTO api_usage (user_email, api_type) VALUES (?, ?)",
            (user_email, api_type)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[API Logger Error] {e}")


def get_admin_stats():
    """Return all monitoring data for the admin dashboard."""
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    # Total users
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    # Total messages sent
    c.execute("SELECT COUNT(*) FROM unified_messages WHERE direction='sent'")
    total_messages = c.fetchone()[0]

    # Total API calls
    c.execute("SELECT COUNT(*) FROM api_usage")
    total_api_calls = c.fetchone()[0]

    # Total errors
    c.execute("SELECT COUNT(*) FROM activity_logs WHERE status='error'")
    total_errors = c.fetchone()[0]

    # Recent logs (last 50)
    c.execute("""
        SELECT user_email, action, details, status, timestamp
        FROM activity_logs
        ORDER BY timestamp DESC
        LIMIT 50
    """)
    logs = c.fetchall()

    # API usage breakdown
    c.execute("""
        SELECT api_type, COUNT(*) as count
        FROM api_usage
        GROUP BY api_type
        ORDER BY count DESC
    """)
    api_breakdown = c.fetchall()

    # All users list
    c.execute("SELECT id, name, email, role FROM users ORDER BY id DESC")
    users = c.fetchall()

    # Active users today
    c.execute("""
        SELECT COUNT(DISTINCT user_email) FROM activity_logs
        WHERE DATE(timestamp) = DATE('now')
    """)
    active_today = c.fetchone()[0]

    conn.close()

    return {
        "total_users": total_users,
        "total_messages": total_messages,
        "total_api_calls": total_api_calls,
        "total_errors": total_errors,
        "logs": logs,
        "api_breakdown": api_breakdown,
        "users": users,
        "active_today": active_today,
    }