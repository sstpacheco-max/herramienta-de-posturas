import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sst_database.db")

def init_db():
    """Inicializa la base de datos y crea las tablas si no existen."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tabla de eventos/logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            camera TEXT NOT NULL,
            worker_id TEXT NOT NULL,
            method TEXT NOT NULL,
            score INTEGER,
            risk TEXT NOT NULL,
            duration TEXT,
            legal_doc TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def log_event(camera_url, worker_id, method, score, risk, doc_path, duration=0):
    """Guarda un evento en la base de datos."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        timestamp = datetime.now().isoformat()
        duration_str = f"{duration}s"
        
        cursor.execute('''
            INSERT INTO events (timestamp, camera, worker_id, method, score, risk, duration, legal_doc)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, camera_url, worker_id, method, score, risk, duration_str, doc_path))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error guardando evento en DB: {e}")
        return False

def get_recent_logs(limit=20):
    """Obtiene los últimos N eventos para el dashboard."""
    try:
        conn = sqlite3.connect(DB_PATH)
        # Permite acceder a las columnas por nombre
        conn.row_factory = sqlite3.Row 
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM events 
            ORDER BY timestamp ASC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convertir a lista de diccionarios para compatibilidad con la API
        return [dict(row) for row in rows]
    except Exception as e:
        print(f"Error leyendo eventos de DB: {e}")
        return []

# Inicializar al importar el módulo
init_db()
