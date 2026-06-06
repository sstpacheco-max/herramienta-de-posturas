import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sst_database.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp   TEXT NOT NULL,
            camera      TEXT NOT NULL,
            worker_id   TEXT NOT NULL,
            method      TEXT NOT NULL,
            score       INTEGER,
            risk        TEXT NOT NULL,
            duration    TEXT,
            legal_doc   TEXT,
            epp_detected TEXT,
            epp_missing  TEXT
        )
    ''')
    # Agregar columnas EPP si ya existe la tabla sin ellas (migración)
    for col, typ in [("epp_detected", "TEXT"), ("epp_missing", "TEXT")]:
        try:
            c.execute(f"ALTER TABLE events ADD COLUMN {col} {typ}")
        except Exception:
            pass
    conn.commit()
    conn.close()

def log_event(camera_url, worker_id, method, score, risk, doc_path,
              duration=0, epp_detected=None, epp_missing=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO events
              (timestamp, camera, worker_id, method, score, risk, duration,
               legal_doc, epp_detected, epp_missing)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            camera_url, worker_id, method, score, risk,
            f"{duration}s", doc_path,
            ", ".join(epp_detected) if epp_detected else "",
            ", ".join(epp_missing)  if epp_missing  else "",
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error guardando evento en DB: {e}")
        return False

def get_recent_logs(limit=20):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error leyendo eventos de DB: {e}")
        return []

def get_all_events():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM events ORDER BY timestamp DESC")
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error leyendo todos los eventos: {e}")
        return []

init_db()
