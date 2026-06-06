import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sst_database.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Tabla de trabajadores
    c.execute('''
        CREATE TABLE IF NOT EXISTS workers (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre        TEXT NOT NULL,
            cedula        TEXT UNIQUE NOT NULL,
            cargo         TEXT DEFAULT '',
            departamento  TEXT DEFAULT '',
            turno         TEXT DEFAULT 'Mañana',
            activo        INTEGER DEFAULT 1,
            created_at    TEXT NOT NULL
        )
    ''')

    # Tabla de eventos de riesgo
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp    TEXT NOT NULL,
            camera       TEXT NOT NULL,
            worker_id    TEXT NOT NULL,
            worker_db_id INTEGER,
            method       TEXT NOT NULL,
            score        INTEGER,
            risk         TEXT NOT NULL,
            duration     TEXT,
            legal_doc    TEXT,
            epp_detected TEXT,
            epp_missing  TEXT
        )
    ''')

    # Migraciones para tablas existentes
    migrations = [
        ("epp_detected", "TEXT"),
        ("epp_missing",  "TEXT"),
        ("worker_db_id", "INTEGER"),
    ]
    for col, typ in migrations:
        try:
            c.execute(f"ALTER TABLE events ADD COLUMN {col} {typ}")
        except Exception:
            pass

    conn.commit()
    conn.close()

# ─── Workers CRUD ─────────────────────────────────────────────────────────────

def add_worker(nombre, cedula, cargo="", departamento="", turno="Mañana"):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO workers (nombre, cedula, cargo, departamento, turno, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (nombre, cedula, cargo, departamento, turno, datetime.now().isoformat()))
        worker_id = c.lastrowid
        conn.commit()
        conn.close()
        return worker_id
    except Exception as e:
        print(f"Error añadiendo trabajador: {e}")
        return None

def get_all_workers():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM workers WHERE activo=1 ORDER BY nombre ASC")
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error leyendo trabajadores: {e}")
        return []

def get_worker_by_id(worker_db_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM workers WHERE id=?", (worker_db_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as e:
        print(f"Error leyendo trabajador: {e}")
        return None

def update_worker(worker_db_id, nombre, cedula, cargo="", departamento="", turno="Mañana"):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            UPDATE workers SET nombre=?, cedula=?, cargo=?, departamento=?, turno=?
            WHERE id=?
        ''', (nombre, cedula, cargo, departamento, turno, worker_db_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error actualizando trabajador: {e}")
        return False

def deactivate_worker(worker_db_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE workers SET activo=0 WHERE id=?", (worker_db_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error desactivando trabajador: {e}")
        return False

def get_worker_events(worker_db_id, limit=200):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(
            "SELECT * FROM events WHERE worker_db_id=? ORDER BY timestamp DESC LIMIT ?",
            (worker_db_id, limit)
        )
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error leyendo eventos de trabajador: {e}")
        return []

def get_worker_summary(worker_db_id):
    """Resumen estadístico de un trabajador: total eventos, conteo por riesgo, último evento."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute('''
            SELECT risk, COUNT(*) as cnt
            FROM events WHERE worker_db_id=?
            GROUP BY risk
        ''', (worker_db_id,))
        rows = c.fetchall()
        summary = {r["risk"]: r["cnt"] for r in rows}
        c.execute('''
            SELECT timestamp FROM events WHERE worker_db_id=?
            ORDER BY timestamp DESC LIMIT 1
        ''', (worker_db_id,))
        last = c.fetchone()
        conn.close()
        return {
            "total": sum(summary.values()),
            "by_risk": summary,
            "last_event": last["timestamp"] if last else None,
        }
    except Exception as e:
        print(f"Error en resumen de trabajador: {e}")
        return {"total": 0, "by_risk": {}, "last_event": None}

def log_event(camera_url, worker_id, method, score, risk, doc_path,
              duration=0, epp_detected=None, epp_missing=None, worker_db_id=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            INSERT INTO events
              (timestamp, camera, worker_id, worker_db_id, method, score, risk,
               duration, legal_doc, epp_detected, epp_missing)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            camera_url, worker_id, worker_db_id, method, score, risk,
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
