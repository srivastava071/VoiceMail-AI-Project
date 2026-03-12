import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            language TEXT DEFAULT 'en-IN',
            theme TEXT DEFAULT 'light'
        )
    """)


    # Add role column if it doesn't exist (for existing DBs)
    try:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
    except:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            action TEXT,
            details TEXT,
            status TEXT DEFAULT 'success',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS api_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            api_type TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # ✅ NEW TABLE FOR TELEGRAM CONTACTS
    c.execute("""
        CREATE TABLE IF NOT EXISTS telegram_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            chat_id TEXT UNIQUE
        )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS whatsapp_contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        phone TEXT UNIQUE
        )
    """)
    
    c.execute("""
    CREATE TABLE IF NOT EXISTS unified_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT,
        sender TEXT,
        receiver TEXT,
        message TEXT,
        direction TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

    