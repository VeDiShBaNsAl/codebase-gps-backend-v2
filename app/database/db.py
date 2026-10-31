import sqlite3
import os
from contextlib import contextmanager
from app.config.settings import settings

def get_db_path() -> str:
    os.makedirs(settings.data_dir, exist_ok=True)
    db_path = settings.database_url
    if db_path.startswith("./"):
        db_path = os.path.join(os.getcwd(), db_path[2:])
    return db_path

@contextmanager
def get_db_connection():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS repositories (
            id TEXT PRIMARY KEY,
            owner TEXT NOT NULL,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            branch TEXT NOT NULL,
            status TEXT NOT NULL,
            current_stage TEXT NOT NULL,
            progress INTEGER NOT NULL,
            error TEXT,
            local_path TEXT,
            total_files INTEGER DEFAULT 0,
            total_symbols INTEGER DEFAULT 0,
            total_relationships INTEGER DEFAULT 0,
            languages TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS nodes (
            id TEXT NOT NULL,
            repo_id TEXT NOT NULL,
            type TEXT NOT NULL,
            name TEXT NOT NULL,
            file_path TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            language TEXT NOT NULL,
            PRIMARY KEY (repo_id, id),
            FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_nodes_repo ON nodes(repo_id)")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_id TEXT NOT NULL,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            type TEXT NOT NULL,
            resolution TEXT NOT NULL,
            source_file TEXT NOT NULL,
            source_line INTEGER NOT NULL,
            FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_repo ON edges(repo_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(repo_id, source)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(repo_id, target)")
        cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
            repo_id UNINDEXED,
            symbol_id UNINDEXED,
            name,
            file_path,
            docstring
        )
        """)
