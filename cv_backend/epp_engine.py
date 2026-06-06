import cv2
import numpy as np
import os
try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

# Rutas del modelo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "best_ppe_nano.pt")

# URL pública del modelo EPP entrenado en SH17 (YOLOv8n, 17 clases de EPP)
MODEL_DOWNLOAD_URL = "https://github.com/ahmadmughees/SH17dataset/releases/download/v1/yolo8n.pt"

# Variables globales del modelo
_model = None
_model_coco = None

def _download_model():
    """Descarga el modelo EPP si no existe localmente."""
    import urllib.request
    print(f"SISTEMA: Descargando modelo EPP desde {MODEL_DOWNLOAD_URL} ...")
    try:
        urllib.request.urlretrieve(MODEL_DOWNLOAD_URL, MODEL_PATH)
        print(f"SISTEMA: Modelo EPP descargado en {MODEL_PATH}")
        return True
    except Exception as e:
        print(f"SISTEMA: No se pudo descargar el modelo EPP: {e}")
        return False

def get_yolo_model():
    global _model, _model_coco
    if _model_coco is None and YOLO is not None:
        try:
            _model_coco = YOLO("yolov8n.pt")
        except:
            pass

    if _model is None and YOLO is not None:
        if not os.path.exists(MODEL_PATH):
            _download_model()
        if os.path.exists(MODEL_PATH):
            try:
                _model = YOLO(MODEL_PATH)
                print(f"SISTEMA: Modelo YOLO EPP NANO cargado exitosamente. Clases: {_model.names}")
            except Exception as e:
                print(f"Error cargando YOLO EPP: {e}")
    return _model

RISK_TABLE = [
    (0, "Insignificante", 0),
    (1, "Bajo", 2),
    (2, "Medio", 5),
    (4, "Alto", 8),
    (float('inf'), "Critico", 10),
]

def detect_epp(frame, person_bbox=None):
    """
    Detecta EPPs en el frame usando YOLOv8.
    person_bbox: (x1, y1, x2, y2) opcional para filtrar detecciones dentro de la persona.
    Retorna dict con detected, missing, risk, score.
    """
    model = get_yolo_model()
    
    # Valores por defecto si no hay modelo o falla
    detected_list = []
    missing_list = ["Casco", "Guantes", "Calzado", "Gafas", "Mascarilla"]
    details = {"Casco": False, "Guantes": False, "Calzado": False, "Gafas": False, "Mascarilla": False}
    missing_weight = 7 # 3(Casco) + 1(Guantes) + 1(Calzado) + 1(Gafas) + 1(Mascarilla)
    raw_boxes = []

    if model is None:
        # Sin modelo YOLO no podemos detectar; retornamos estado neutro para evitar falsos positivos
        return {"detected": [], "missing": [], "details": {k: True for k in details},
                "risk": "Insignificante", "score": 0, "raw_boxes": []}

    if model is not None:
        try:
            # Usar el frame original sin CLAHE para evitar distorsión de colores en YOLO
            frame_enhanced = frame

            if person_bbox:
                x1, y1, x2, y2 = map(int, person_bbox)
                h, w = frame.shape[:2]
                person_h = y2 - y1
                person_w = x2 - x1
                
                # Expandir dinámicamente basado en la altura/anchura de la persona
                # Incrementamos drásticamente los márgenes porque si MediaPipe solo ve la cara,
                # el casco queda fuera del ROI original.
                x1 = max(0, x1 - int(person_w * 0.8))
                y1 = max(0, y1 - int(person_h * 2.0)) # 200% hacia arriba para incluir el casco completo
                x2 = min(w, x2 + int(person_w * 0.8))
                y2 = min(h, y2 + int(person_h * 1.5)) # 150% hacia abajo para incluir el torso y manos
                
                roi = frame_enhanced[y1:y2, x1:x2]
                if roi.size > 0:
                    results = model.predict(roi, conf=0.10, iou=0.4, verbose=False)
                    if _model_coco:
                        res_coco = _model_coco.predict(roi, conf=0.25, verbose=False)
                else:
                    results = []
                    res_coco = []
            else:
                results = model.predict(frame_enhanced, conf=0.10, iou=0.4, verbose=False)
                if _model_coco:
                    res_coco = _model_coco.predict(frame, conf=0.25, verbose=False)

            person_found_in_coco = False
            if _model_coco and len(res_coco) > 0:
                for b in res_coco[0].boxes:
                    c_id = int(b.cls[0].item())
                    n = _model_coco.names[c_id]
                    if n == "person":
                        person_found_in_coco = True
                    bx1, by1, bx2, by2 = b.xyxy[0].tolist()
                    if person_bbox:
                        bx1 += x1; bx2 += x1
                        by1 += y1; by2 += y1
                    raw_boxes.append((int(bx1), int(by1), int(bx2), int(by2), f"COCO:{n}"))

            # Tambien aceptamos "person" detectada por el modelo EPP (clase 0)
            person_found_in_epp = False
            if len(results) > 0:
                for b in results[0].boxes:
                    cid = int(b.cls[0].item())
                    nm = model.names[cid].lower()
                    if nm == "person" or nm == "head" or nm == "face":
                        person_found_in_epp = True
                        break

            if len(results) > 0:
                boxes = results[0].boxes
                names = model.names
                
                # Reseteamos todo a falso para procesar las detecciones
                details = {"Casco": False, "Guantes": False, "Calzado": False, "Gafas": False, "Mascarilla": False}
                missing_list = []
                missing_weight = 0

                for box in boxes:
                    cls_id = int(box.cls[0].item())
                    name = names[cls_id].lower()
                    
                    if "helmet" in name or "hardhat" in name or "casco" in name:
                        if not "no_" in name and not "no-" in name:
                            details["Casco"] = True
                    if "glove" in name:
                        if not "no_" in name and not "no-" in name:
                            details["Guantes"] = True
                    if "shoes" in name or "boot" in name:
                        if not "no_" in name and not "no-" in name:
                            details["Calzado"] = True
                    if "goggle" in name or "glass" in name:
                        if not "no_" in name and not "no-" in name:
                            details["Gafas"] = True
                    if "mask" in name:
                        if not "no_" in name and not "no-" in name:
                            details["Mascarilla"] = True
                    
                    bx1, by1, bx2, by2 = box.xyxy[0].tolist()
                    if person_bbox:
                        bx1 += x1; bx2 += x1
                        by1 += y1; by2 += y1
                    raw_boxes.append((int(bx1), int(by1), int(bx2), int(by2), name))

                # Construir listas finales basado en lo encontrado
                if details["Casco"]:
                    detected_list.append("Casco")
                else:
                    missing_list.append("Casco")
                    missing_weight += 3

                if details["Guantes"]:
                    detected_list.append("Guantes")
                else:
                    missing_list.append("Guantes")
                    missing_weight += 1

                if details["Calzado"]:
                    detected_list.append("Calzado")
                else:
                    missing_list.append("Calzado")
                    missing_weight += 1

                if details["Gafas"]:
                    detected_list.append("Gafas")
                else:
                    missing_list.append("Gafas")
                    missing_weight += 1

                if details["Mascarilla"]:
                    detected_list.append("Mascarilla")
                else:
                    missing_list.append("Mascarilla")
                    missing_weight += 1

            # Si no pasaron un bounding box (no usamos MediaPipe), COCO no encontró persona
            # y el propio modelo EPP tampoco — entonces asumimos frame vacío.
            if not person_bbox and not person_found_in_coco and not person_found_in_epp:
                missing_weight = 0
                missing_list = []
                detected_list = []
                # Restablecemos detalles para no mostrar nada en rojo
                details = {"Casco": True, "Guantes": True, "Calzado": True, "Gafas": True, "Mascarilla": True}

        except Exception as e:
            print(f"Error en inferencia YOLO: {e}")

    risk, score = "Insignificante", 0
    for threshold, r, s in RISK_TABLE:
        if missing_weight <= threshold:
            risk, score = r, s
            break

    return {"detected": detected_list, "missing": missing_list,
            "details": details, "risk": risk, "score": score, "raw_boxes": raw_boxes}

def draw_epp_results(image, epp_results, y_offset=160):
    """Dibuja los resultados EPP sobre el frame."""
    # Dibujar raw boxes de YOLO para debug visual
    for (x1, y1, x2, y2, name) in epp_results.get("raw_boxes", []):
        if name.startswith("COCO:"):
            color = (255, 255, 0) # Cyan para COCO
        else:
            color = (255, 0, 255) if "no_" in name else (0, 255, 0)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        cv2.putText(image, name, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    for name, found in epp_results.get("details", {}).items():
        color  = (0, 200, 80) if found else (0, 50, 255)
        symbol = "OK" if found else "NO"
        cv2.putText(image, f"[{symbol}] {name}", (20, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        y_offset += 26
    return image
