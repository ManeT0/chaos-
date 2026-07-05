import sqlite3


def init_db(path: str = "chaos.db"):
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            target TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def record_experiment(name: str, status: str, target: str | None = None, path: str = "chaos.db"):
    conn = sqlite3.connect(path)
    conn.execute(
        "INSERT INTO experiments (name, status, target) VALUES (?, ?, ?)",
        (name, status, target),
    )
    conn.commit()
    conn.close()


def list_experiments(path: str = "chaos.db"):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, name, status, target, created_at FROM experiments ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
