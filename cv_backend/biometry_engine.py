import os
import cv2
import numpy as np

# Intentar cargar DeepFace si está disponible
try:
    from deepface import DeepFace
    HAS_DEEPFACE = True
except:
    HAS_DEEPFACE = False

DB_PATH = "db_rostros"
MODEL_FILE = "lbph_model.yml"

# Face detector para LBPH
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def get_lbph_recognizer():
    """Crea y entrena un reconocedor LBPH con las imágenes de la DB."""
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    faces = []
    labels = []
    label_map = {}
    
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
        return None, {}

    current_id = 0
    for filename in os.listdir(DB_PATH):
        if filename.lower().endswith(('.jpg', '.jpeg', '.png')):
            path = os.path.join(DB_PATH, filename)
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None: continue
            
            # Detectar cara en la imagen de referencia
            detected_faces = face_cascade.detectMultiScale(img, 1.3, 5)
            for (x, y, w, h) in detected_faces:
                faces.append(img[y:y+h, x:x+w])
                worker_id = filename.split('.')[0]
                label_map[current_id] = worker_id
                labels.append(current_id)
                break # Solo una cara por imagen de ref
            current_id += 1
            
    if len(faces) > 0:
        recognizer.train(faces, np.array(labels))
        return recognizer, label_map
    return None, {}

# Caché del reconocedor para no re-entrenar cada frame
_recognizer_cache = {"model": None, "map": {}, "mtime": 0}

def identify_worker(frame):
    """
    Identifica al trabajador en el frame.
    Usa DeepFace si está disponible, de lo contrario usa LBPH de OpenCV.
    """
    if HAS_DEEPFACE:
        try:
            if not os.path.exists(DB_PATH) or len(os.listdir(DB_PATH)) == 0:
                return "DB_VACIA"
            results = DeepFace.find(img_path=frame, db_path=DB_PATH, enforce_detection=False, silent=True)
            if len(results) > 0 and not results[0].empty:
                best_match = results[0].iloc[0]['identity']
                return os.path.basename(best_match).split('.')[0]
            return "Desconocido"
        except:
            pass # Reintentar con LBPH

    # Fallback a LBPH (OpenCV)
    try:
        # Verificar si la DB cambió
        db_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else 0
        if _recognizer_cache["model"] is None or db_mtime > _recognizer_cache["mtime"]:
            model, lmap = get_lbph_recognizer()
            _recognizer_cache.update({"model": model, "map": lmap, "mtime": db_mtime})
        
        if _recognizer_cache["model"] is None:
            return "SST_OPERARIO_GENERICO"

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detected_faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        for (x, y, w, h) in detected_faces:
            roi = gray[y:y+h, x:x+w]
            label_id, confidence = _recognizer_cache["model"].predict(roi)
            # Confianza baja en LBPH significa mejor coincidencia (distancia)
            if confidence < 70: 
                return _recognizer_cache["map"].get(label_id, "Desconocido")
        
        return "Buscando..."
    except Exception as e:
        print(f"Error Biometria: {e}")
        return "Error_BIO"

def add_face_to_db(image, worker_id):
    """Guarda una imagen de referencia."""
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
    file_path = os.path.join(DB_PATH, f"{worker_id}.jpg")
    cv2.imwrite(file_path, image)
    # Forzar recarga del modelo LBPH
    _recognizer_cache["mtime"] = 0
    return file_path
