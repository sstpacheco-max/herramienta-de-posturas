import cv2, json, requests, time, threading, os, numpy as np
import ergonomics_engine as erg
import biometry_engine as bio
import legal_engine as leg
import epp_engine as epp
import mediapipe as mp
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from datetime import datetime

app = FastAPI(title="SST 4.0 - Computer Vision Orquestador")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

LOCATION = "PLANTA PRINCIPAL - SECTOR PROCESOS" # Ubicacion por defecto

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
WEBHOOK_URL = "https://n8n-n8n.y3jjap.easypanel.host/webhook-test/sst-alerts"
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

def log_event(camera_url, worker_id, method, score, risk, doc_path, duration=0):
    event = {
        "timestamp": datetime.now().isoformat(),
        "camera": camera_url, "worker_id": worker_id,
        "method": method, "score": score, "risk": risk,
        "duration": f"{duration}s", "legal_doc": doc_path,
    }
    try:
        lf = os.path.join(BASE_DIR, "sst_log_eventos.json")
        logs = []
        if os.path.exists(lf):
            with open(lf, "r") as f: logs = json.load(f)
        logs.append(event)
        with open(lf, "w") as f: json.dump(logs, f, indent=4)
    except: pass

# ─── Video Processing ─────────────────────────────────────────────────────────
def process_video_stream(camera_url: str, method: str = "RULA"):
    print(f"STREAM: Iniciando {camera_url} [{method}]")
    source = int(camera_url) if camera_url.isdigit() else camera_url

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"ERROR: No se pudo abrir {camera_url}")
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

        if use_epp:
            epp_results = epp.detect_epp(image)
            image = epp.draw_epp_results(image, epp_results, y_offset=160)
            if epp_results["score"] > score:
                score, risk = epp_results["score"], epp_results["risk"]

        # Actualizar estadísticas (no bloquear por frame)
        if frame_ts_ms % 1000 < 33:
            update_stats(risk, current_worker)
            active_cameras[camera_url].update(
                {"worker": current_worker, "risk": risk, "score": score})

        # Alerta sostenida
        if risk in ["Alto", "Critico"]:
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
                
                doc_path = leg.create_document_draft(current_worker, current_worker, method, risk, evidence_path=ev_path)
                log_event(camera_url, current_worker, method, score, risk, doc_path, duration)
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
def get_stats():
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
def get_logs():
    lf = os.path.join(BASE_DIR, "sst_log_eventos.json")
    if os.path.exists(lf):
        try:
            with open(lf, "r") as f: return json.load(f)[-20:]
        except: return []
    return []

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
