import cv2, json, requests, time, threading, os, numpy as np, asyncio
import sys
from dotenv import load_dotenv

# winsound solo existe en Windows; en Linux usamos un no-op
if sys.platform == "win32":
    import winsound
    def _beep(freq, dur): winsound.Beep(freq, dur)
else:
    def _beep(freq, dur): pass

import db_manager as dbm
import ergonomics_engine as erg
import biometry_engine as bio
import legal_engine as leg
import epp_engine as epp
import mediapipe as mp
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from datetime import datetime

app = FastAPI(title="SST 4.0 - Computer Vision Orquestador")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

load_dotenv()
LOCATION = os.getenv("LOCATION", "PLANTA PRINCIPAL - SECTOR PROCESOS") # Ubicacion por defecto

main_loop = None

@app.on_event("startup")
async def startup_event():
    global main_loop
    main_loop = asyncio.get_running_loop()
    # Precargar el modelo YOLO para EPP
    print("SISTEMA: Cargando modelo YOLO para EPP (esto puede tomar unos segundos)...")
    epp.get_yolo_model()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()


# ─── Estado Global ────────────────────────────────────────────────────────────
active_streams  = {}  # camera_url -> last JPEG bytes
active_cameras  = {}  # camera_url -> {method, start_time, worker, risk, running}
stats_lock      = threading.Lock()

system_stats = {
    "total_violations": 0,
    "critical_alerts": 0,
    "high_alerts": 0,
    "risk_distribution": {"Insignificante": 0, "Bajo": 0, "Medio": 0, "Alto": 0, "Critico": 0},
    "violations_by_hour": {},
    "violations_by_worker": {},
    "session_start": datetime.now().isoformat(),
}

# --- Firebase Integración ---
FIREBASE_URL = "https://deteccion-de-posturas-y-epps-default-rtdb.firebaseio.com"

def firebase_stats_loop():
    while True:
        try:
            with stats_lock:
                stats_copy = {
                    "total_violations": system_stats["total_violations"],
                    "critical_alerts": system_stats["critical_alerts"],
                    "risk_distribution": system_stats["risk_distribution"].copy()
                }
            requests.put(f"{FIREBASE_URL}/stats.json", json=stats_copy, timeout=5)
        except Exception as e:
            pass
        time.sleep(3)

threading.Thread(target=firebase_stats_loop, daemon=True).start()

# ─── MediaPipe ────────────────────────────────────────────────────────────────
MODEL_PATH   = os.path.join(BASE_DIR, "pose_landmarker.task")
HAS_MEDIAPIPE = False

try:
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision as mp_vision
    HAS_MEDIAPIPE = True
    print("SISTEMA: MediaPipe Tasks disponible.")
except Exception as e:
    print(f"SISTEMA: MediaPipe no disponible: {e}")

from biometry_engine import HAS_DEEPFACE

# ─── n8n Webhook ──────────────────────────────────────────────────────────────
WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "https://n8n-n8n.y3jjap.easypanel.host/webhook-test/sst-alerts")
n8n_status  = {"last_sent": None, "success": 0, "errors": 0}

def send_n8n_webhook(worker_id, method, score, risk, camera_url, doc_path, duration):
    def _send():
        payload = {
            "timestamp":    datetime.now().isoformat(),
            "worker_id":    worker_id,
            "method":       method,
            "score":        score,
            "risk":         risk,
            "camera":       camera_url,
            "document":     os.path.basename(doc_path) if doc_path else "",
            "duration_s":   duration,
            "alert_type":   "EPP_VIOLATION" if method == "EPP" else "ERGONOMIC_VIOLATION",
            "severity":     "CRITICAL" if risk == "Critico" else "HIGH",
        }
        try:
            r = requests.post(WEBHOOK_URL, json=payload, timeout=5)
            n8n_status["last_sent"] = datetime.now().isoformat()
            n8n_status["success"] += 1
            print(f"N8N -> {r.status_code}")
        except Exception as e:
            n8n_status["errors"] += 1
            print(f"N8N ERROR: {e}")
    threading.Thread(target=_send, daemon=True).start()

def update_stats(risk, worker_id):
    with stats_lock:
        system_stats["risk_distribution"][risk] = \
            system_stats["risk_distribution"].get(risk, 0) + 1
        if risk in ["Alto", "Critico"]:
            system_stats["total_violations"] += 1
            if risk == "Critico":
                system_stats["critical_alerts"] += 1
            else:
                system_stats["high_alerts"] += 1
            hour = datetime.now().strftime("%H")
            system_stats["violations_by_hour"][hour] = \
                system_stats["violations_by_hour"].get(hour, 0) + 1
            system_stats["violations_by_worker"][worker_id] = \
                system_stats["violations_by_worker"].get(worker_id, 0) + 1

# ─── Helpers ──────────────────────────────────────────────────────────────────
def create_landmarker():
    if not HAS_MEDIAPIPE:
        return None
    try:
        opts = mp_vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=mp_vision.RunningMode.VIDEO,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        return mp_vision.PoseLandmarker.create_from_options(opts)
    except Exception as e:
        print(f"Error creando landmarker: {e}")
        return None

def get_color(risk):
    if risk in ["Insignificante", "Bajo"]: return (0, 220, 80)
    if risk == "Medio":  return (0, 200, 255)
    if risk == "Alto":   return (0, 100, 255)
    return (0, 0, 255)

def draw_marionette(image, landmarks, color):
    h, w, _ = image.shape
    connections = [(11,12),(11,13),(13,15),(12,14),(14,16),(11,23),(12,24),(23,24),(23,25),(25,27),(24,26),(26,28)]
    pts = {}
    for i, lm in enumerate(landmarks):
        cx, cy = int(lm.x * w), int(lm.y * h)
        pts[i] = (cx, cy)
        cv2.circle(image, (cx, cy), 5, (255,255,255), -1)
    for s, e in connections:
        if s in pts and e in pts:
            cv2.line(image, pts[s], pts[e], color, 3)

def log_event(camera_url, worker_id, method, score, risk, doc_path, duration=0, company_id=1, camera_id=1):
    dbm.log_event(camera_url, worker_id, method, score, risk, doc_path, duration)
    
    # Registrar en base de datos SaaS
    try:
        import saas_db as sdb
        sdb.log_saas_alert(company_id, camera_id, worker_id, method, risk, doc_path, doc_path)
    except Exception as e:
        print(f"Error guardando alerta en SaaS DB: {e}")
        
    event_data = {
        "type": "alert",
        "timestamp": datetime.now().isoformat(),
        "camera": camera_url,
        "worker_id": worker_id,
        "method": method,
        "score": score,
        "risk": risk,
        "duration": f"{duration}s",
        "legal_doc": doc_path
    }
    
    # Push to Firebase
    def _send_fb():
        try:
            requests.post(f"{FIREBASE_URL}/alerts.json", json=event_data, timeout=3)
        except Exception as e:
            print(f"Firebase Alert Error: {e}")
    threading.Thread(target=_send_fb, daemon=True).start()

    if main_loop and main_loop.is_running():
        asyncio.run_coroutine_threadsafe(manager.broadcast(json.dumps(event_data)), main_loop)


# ─── Video Processing ─────────────────────────────────────────────────────────
def process_video_stream(camera_url: str, method: str = "RULA"):
    print(f"STREAM: Iniciando {camera_url} [{method}]")
    
    # Determinar si camera_url es un ID de la base de datos SaaS
    company_id = 1 # Por defecto Planta Alfa
    camera_id = 1
    source = camera_url
    
    if camera_url.isdigit():
        try:
            import saas_db as sdb
            cam = sdb.get_camera(int(camera_url))
            if cam:
                source = int(cam["stream_url"]) if cam["stream_url"].isdigit() else cam["stream_url"]
                company_id = cam["company_id"]
                camera_id = cam["id"]
                print(f"SaaS DB: Camara encontrada '{cam['name']}' para Empresa ID {company_id}, fuente: {source}")
            else:
                source = int(camera_url)
        except Exception as e:
            print(f"Error leyendo de saas_db: {e}")
            source = int(camera_url)
            
    if isinstance(source, int) and source == 0 and os.name == 'nt':
        cap = cv2.VideoCapture(source, cv2.CAP_DSHOW)
    else:
        cap = cv2.VideoCapture(source)
        
    if not cap.isOpened():
        print(f"ERROR: No se pudo abrir {source}")
        active_cameras.pop(camera_url, None)
        return

    active_cameras[camera_url] = {
        "method": method, "start_time": datetime.now().isoformat(),
        "worker": "Buscando...", "risk": "Insignificante",
        "score": 0, "running": True,
    }

    landmarker       = create_landmarker()
    last_alert_time  = 0
    violation_start  = None
    current_worker   = "Buscando..."
    frame_ts_ms      = 0
    use_pose         = method in ["RULA", "REBA", "RULA+EPP", "REBA+EPP"]
    use_epp          = method in ["EPP", "RULA+EPP", "REBA+EPP"]
    pose_method      = method.replace("+EPP", "")

    while active_cameras.get(camera_url, {}).get("running", False):
        success, image = cap.read()
        if not success: break

        frame_ts_ms += 33
        risk, score = "Insignificante", 0
        epp_results = None

        # --- Overlay de Tiempo y Lugar ---
        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Clonar imagen limpia antes de dibujar los textos gigantes para pasarsela a YOLO
        image_clean = image.copy()
        
        cv2.putText(image, f"{timestamp_str} | {LOCATION}", (20, image.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        if use_pose and landmarker:
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=image)
            result = landmarker.detect_for_video(mp_img, int(time.time() * 1000))

            if result.pose_landmarks:
                lms = result.pose_landmarks[0]
                score, risk = (erg.get_rula_score(lms) if pose_method == "RULA"
                               else erg.get_reba_score(lms))

                if frame_ts_ms % 3000 < 33:
                    current_worker = bio.identify_worker(image)

                draw_marionette(image, lms, get_color(risk))
                cv2.putText(image, f"EMPLEADO: {current_worker}", (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)
                cv2.putText(image, f"{pose_method}: {score} ({risk})", (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, get_color(risk), 2)
            else:
                cv2.putText(image, "ESPERANDO PERSONA...", (20, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200,200,200), 1)

        # Extraer bounding box de la persona si hay landmarks
        person_bbox = None
        if use_pose and landmarker and result.pose_landmarks:
            h, w = image.shape[:2]
            x_coords = [lm.x * w for lm in result.pose_landmarks[0]]
            y_coords = [lm.y * h for lm in result.pose_landmarks[0]]
            person_bbox = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

        # Extraer telemetría avanzada si hay postura
        com = (0.5, 0.5)
        compression = 0
        if use_pose and landmarker and result.pose_landmarks:
            com = erg.calculate_center_of_mass(result.pose_landmarks[0])
            compression = erg.calculate_l4_l5_compression(result.pose_landmarks[0])

        if use_epp:
            # Pasar la imagen original SIN TEXTOS DIBUJADOS para que YOLO no se confunda
            epp_results = epp.detect_epp(image_clean, person_bbox=person_bbox)
            image = epp.draw_epp_results(image, epp_results, y_offset=160)
            if epp_results["score"] > score:
                score, risk = epp_results["score"], epp_results["risk"]

        # Actualizar estadísticas (no bloquear por frame)
        if frame_ts_ms % 1000 < 33:
            update_stats(risk, current_worker)
            active_cameras[camera_url].update(
                {"worker": current_worker, "risk": risk, "score": score})
            
            # Enviar telemetría en tiempo real por WebSocket (1 FPS aprox)
            telemetry = {
                "type": "telemetry",
                "camera": camera_url,
                "worker": current_worker,
                "score": score,
                "risk": risk,
                "com": com,
                "compression": compression
            }
            if main_loop and main_loop.is_running():
                asyncio.run_coroutine_threadsafe(manager.broadcast(json.dumps(telemetry)), main_loop)

        # Alerta sostenida
        if risk in ["Alto", "Critico"]:
            _beep(1500, 200)
            if violation_start is None: violation_start = time.time()
            duration = int(time.time() - violation_start)
            h, w = image.shape[:2]
            cv2.rectangle(image, (0,0), (w,h), (0,0,255), 15)
            cv2.putText(image, f"ALERTA SST: {duration}s", (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,0,255), 2)

            if time.time() - last_alert_time > 10:
                # Guardar evidencia
                ev_dir = os.path.join(BASE_DIR, "evidencias")
                if not os.path.exists(ev_dir): os.makedirs(ev_dir)
                ev_path = os.path.join(ev_dir, f"ev_{current_worker}_{int(time.time())}.jpg")
                cv2.imwrite(ev_path, image)
                
                details = epp_results["missing"] if epp_results else None
                doc_path = leg.create_document_draft(current_worker, current_worker, method, risk, evidence_path=ev_path, details=details)
                log_event(camera_url, current_worker, method, score, risk, doc_path, duration, company_id=company_id, camera_id=camera_id)
                send_n8n_webhook(current_worker, method, score, risk, camera_url, doc_path, duration)
                last_alert_time = time.time()
        else:
            violation_start = None

        ret, buf = cv2.imencode('.jpg', image)
        if ret: active_streams[camera_url] = buf.tobytes()
        time.sleep(0.01)

    cap.release()
    active_cameras.pop(camera_url, None)
    active_streams.pop(camera_url, None)
    print(f"STREAM: Detenido {camera_url}")

# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open(os.path.join(BASE_DIR, "static", "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/status")
def get_status():
    start = datetime.fromisoformat(system_stats["session_start"])
    uptime_s = int((datetime.now() - start).total_seconds())
    h, m = divmod(uptime_s // 60, 60)
    return {
        "status":           "online",
        "mediapipe":        HAS_MEDIAPIPE,
        "deepface":         HAS_DEEPFACE,
        "active_streams":   len(active_cameras),
        "uptime":           f"{h}h {m}m",
        "n8n_last_sent":    n8n_status["last_sent"],
        "n8n_success":      n8n_status["success"],
        "n8n_errors":       n8n_status["errors"],
        "cameras":          [
            {"url": url, **info} for url, info in active_cameras.items()
        ],
    }

@app.get("/api/stats")
def get_stats(company_id: int = None):
    if company_id is not None:
        try:
            import saas_db as sdb
            return sdb.get_company_stats(company_id)
        except Exception as e:
            print(f"SaaS Stats Error: {e}")
            
    with stats_lock:
        top_workers = sorted(
            [{"id": k, "violations": v}
             for k, v in system_stats["violations_by_worker"].items()],
            key=lambda x: x["violations"], reverse=True
        )[:5]
        return {
            **system_stats,
            "top_workers": top_workers,
        }

@app.get("/api/video-feed")
def video_feed(camera_url: str):
    def generate():
        while True:
            if camera_url in active_streams:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
                       + active_streams[camera_url] + b'\r\n')
            time.sleep(0.04)
    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/api/logs")
def get_logs(company_id: int = None):
    if company_id is not None:
        try:
            import saas_db as sdb
            return sdb.get_recent_alerts(company_id, 20)
        except Exception as e:
            print(f"SaaS Logs Error: {e}")
    return dbm.get_recent_logs(20)

# ─── SaaS Autenticación y Gestión ───────────────────────────────────────────

@app.post("/api/auth/login")
async def login(username: str = Form(...), password: str = Form(...)):
    import saas_db as sdb
    user = sdb.authenticate_user(username, password)
    if user:
        return {"status": "success", "user": user}
    return {"status": "error", "message": "Usuario o contrasena incorrectos."}

@app.post("/api/auth/register")
async def register(
    company_name: str = Form(...), 
    license_key: str = Form(...), 
    username: str = Form(...), 
    password: str = Form(...), 
    email: str = Form(None)
):
    import saas_db as sdb
    res = sdb.register_company_and_admin(company_name, license_key, username, password, email)
    return res

@app.get("/api/cameras")
def get_cameras(company_id: int):
    import saas_db as sdb
    return sdb.get_cameras(company_id)

@app.post("/api/cameras/add")
def add_camera(company_id: int = Form(...), name: str = Form(...), stream_url: str = Form(...), location: str = Form(...)):
    import saas_db as sdb
    cam_id = sdb.add_camera(company_id, name, stream_url, location)
    return {"status": "success", "camera_id": cam_id}

@app.post("/api/start-stream")
def start_stream(camera_url: str, method: str = "RULA",
                 background_tasks: BackgroundTasks = None):
    if camera_url in active_cameras:
        return {"message": "Ya está corriendo", "status": "exists"}
    background_tasks.add_task(process_video_stream, camera_url, method)
    return {"message": "Iniciado", "camera_url": camera_url, "method": method}

@app.post("/api/stop-stream")
def stop_stream(camera_url: str):
    if camera_url in active_cameras:
        active_cameras[camera_url]["running"] = False
        return {"message": "Detenido"}
    return {"message": "No encontrado"}

@app.get("/api/download-doc")
def download_doc(path: str):
    from fastapi.responses import FileResponse
    if os.path.exists(path):
        return FileResponse(path, filename=os.path.basename(path))
    return {"error": "Archivo no encontrado"}

@app.post("/api/register-face")
async def register_face(worker_id: str = Form(...), file: UploadFile = File(...)):
    import numpy as np
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    path = bio.add_face_to_db(image, worker_id)
    return {"status": "ok", "path": path}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
