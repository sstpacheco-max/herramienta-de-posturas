import sqlite3
import os
import hashlib
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sst_saas_database.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str) -> str:
    """Retorna el hash SHA256 de la contraseña para seguridad básica local."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_db():
    """Crea las tablas multitenant si no existen."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Tabla de Empresas (Clientes contratantes)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            license_key TEXT UNIQUE NOT NULL,
            license_expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')
    
    # 2. Tabla de Usuarios (Empleados del cliente que auditan o supervisan)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL, -- 'admin', 'supervisor'
            email TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
    ''''
    
    # 3. Tabla de Cámaras asociadas a cada empresa
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cameras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            stream_url TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT DEFAULT 'offline',
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
    ''')
    
    # 4. Tabla de Alertas de seguridad
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            camera_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            worker_id TEXT NOT NULL,
            violation_type TEXT NOT NULL, -- 'EPP', 'ERGONOMICS'
            severity TEXT NOT NULL, -- 'Bajo', 'Medio', 'Alto', 'Critico'
            evidence_url TEXT, -- Enlace a la imagen local o nube
            pdf_report_url TEXT,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
            FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
    
    # Rellenar con datos de prueba si está vacío
    seed_demo_data()

def seed_demo_data():
    """Genera datos de prueba si la base de datos está recién creada."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM companies")
    if cursor.fetchone()[0] == 0:
        print("SISTEMA: Inicializando datos demo en la base de datos SaaS...")
        
        now = datetime.now().isoformat()
        expires = (datetime.now() + timedelta(days=365)).isoformat()
        
        # Insertar Compañías de demostración
        cursor.execute('''
            INSERT INTO companies (name, license_key, license_expires_at, created_at)
            VALUES (?, ?, ?, ?)
        ''', ("Planta Industrial Alfa", "ALFA-SST-2026", expires, now))
        alfa_id = cursor.lastrowid
        
        cursor.execute('''
            INSERT INTO companies (name, license_key, license_expires_at, created_at)
            VALUES (?, ?, ?, ?)
        ''', ("Logistica Global Beta", "BETA-SST-2026", expires, now))
        beta_id = cursor.lastrowid
        
        # Insertar Usuarios (admin/admin123 para Alfa, beta/beta123 para Beta)
        h_admin = hash_password("admin123")
        h_beta = hash_password("beta123")
        
        cursor.execute('''
            INSERT INTO users (company_id, username, password_hash, role, email, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (alfa_id, "admin", h_admin, "admin", "admin@plantaalfa.com", now))
        
        cursor.execute('''
            INSERT INTO users (company_id, username, password_hash, role, email, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (beta_id, "beta", h_beta, "admin", "admin@logisticabeta.com", now))
        
        # Insertar Cámaras iniciales
        cursor.execute('''
            INSERT INTO cameras (company_id, name, stream_url, location)
            VALUES (?, ?, ?, ?)
        ''', (alfa_id, "Camara Entrada Principal", "0", "Planta Principal - Sector Procesos"))
        
        cursor.execute('''
            INSERT INTO cameras (company_id, name, stream_url, location)
            VALUES (?, ?, ?, ?)
        ''', (beta_id, "Camara Bodega 1", "0", "Bodega Despacho - Rampa 3"))
        
        conn.commit()
    conn.close()

def authenticate_user(username, password):
    """Verifica credenciales de usuario. Retorna dict de usuario si es correcto, o None."""
    conn = get_connection()
    cursor = conn.cursor()
    
    h_password = hash_password(password)
    cursor.execute('''
        SELECT u.id, u.username, u.role, u.company_id, c.name as company_name 
        FROM users u
        JOIN companies c ON u.company_id = c.id
        WHERE u.username = ? AND u.password_hash = ?
    ''', (username, h_password))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def register_company_and_admin(company_name, license_key, username, password, email=None):
    """Crea una nueva empresa y su usuario administrador."""
    conn = get_connection()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    expires = (datetime.now() + timedelta(days=365)).isoformat()
    
    try:
        # 1. Crear empresa
        cursor.execute('''
            INSERT INTO companies (name, license_key, license_expires_at, created_at)
            VALUES (?, ?, ?, ?)
        ''', (company_name, license_key, expires, now))
        company_id = cursor.lastrowid
        
        # 2. Crear administrador de la empresa
        h_password = hash_password(password)
        cursor.execute('''
            INSERT INTO users (company_id, username, password_hash, role, email, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (company_id, username, h_password, "admin", email, now))
        
        conn.commit()
        conn.close()
        return {"status": "success", "company_id": company_id}
    except sqlite3.IntegrityError as e:
        conn.close()
        return {"status": "error", "message": "El usuario o la clave de licencia ya existen."}

def add_camera(company_id, name, stream_url, location):
    """Añade una cámara para un cliente específico."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO cameras (company_id, name, stream_url, location)
        VALUES (?, ?, ?, ?)
    ''', (company_id, name, stream_url, location))
    camera_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return camera_id

def get_cameras(company_id):
    """Obtiene las cámaras de una empresa en particular."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cameras WHERE company_id = ?', (company_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_camera(camera_id):
    """Obtiene una cámara específica por su ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM cameras WHERE id = ?', (camera_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def log_saas_alert(company_id, camera_id, worker_id, violation_type, severity, evidence_url=None, pdf_report_url=None):
    """Registra una alerta asociada a un cliente y una cámara."""
    conn = get_connection()
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute('''
        INSERT INTO alerts (company_id, camera_id, timestamp, worker_id, violation_type, severity, evidence_url, pdf_report_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (company_id, camera_id, timestamp, worker_id, violation_type, severity, evidence_url, pdf_report_url))
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id

def get_recent_alerts(company_id, limit=20):
    """Obtiene las alertas recientes de un cliente para su dashboard."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.*, c.name as camera_name 
        FROM alerts a
        JOIN cameras c ON a.camera_id = c.id
        WHERE a.company_id = ?
        ORDER BY a.timestamp DESC
        LIMIT ?
    ''', (company_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_company_stats(company_id):
    """Calcula estadísticas generales de incidentes para un cliente específico."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Total infracciones críticas o altas
    cursor.execute('''
        SELECT COUNT(*) FROM alerts 
        WHERE company_id = ? AND severity IN ('Alto', 'Critico')
    ''', (company_id,))
    total_violations = cursor.fetchone()[0]
    
    # 2. Total alertas críticas
    cursor.execute('''
        SELECT COUNT(*) FROM alerts 
        WHERE company_id = ? AND severity = 'Critico'
    ''', (company_id,))
    critical_alerts = cursor.fetchone()[0]
    
    # 3. Distribución de riesgos
    cursor.execute('''
        SELECT severity, COUNT(*) FROM alerts 
        WHERE company_id = ?
        GROUP BY severity
    ''', (company_id,))
    distribution = {"Bajo": 0, "Medio": 0, "Alto": 0, "Critico": 0}
    for row in cursor.fetchall():
        severity, count = row[0], row[1]
        if severity in distribution:
            distribution[severity] = count
            
    conn.close()
    return {
        "total_violations": total_violations,
        "critical_alerts": critical_alerts,
        "risk_distribution": distribution
    }

# Inicializar Base de Datos al importar
init_db()
