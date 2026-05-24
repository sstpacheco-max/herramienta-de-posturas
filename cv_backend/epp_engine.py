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

# Variables globales del modelo
_model = None
_model_coco = None

def get_yolo_model():
    global _model, _model_coco
    if _model_coco is None and YOLO is not None:
        try:
            _model_coco = YOLO("yolov8n.pt")
        except:
            pass

    if _model is None and YOLO is not None and os.path.exists(MODEL_PATH):
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

    if model is not None:
        try:
            # Cortar la imagen a la persona si existe bbox
            # Mejorar contraste con CLAHE porque la cámara del usuario es monocromática
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l_channel, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            cl = clahe.apply(l_channel)
            limg = cv2.merge((cl,a,b))
            frame_enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

            if person_bbox:
                x1, y1, x2, y2 = map(int, person_bbox)
                # Expandir un poco el bbox para asegurar que no corta el casco
                h, w = frame.shape[:2]
                x1 = max(0, x1 - 50)
                y1 = max(0, y1 - 80)
                x2 = min(w, x2 + 50)
                y2 = min(h, y2 + 50)
                
                roi = frame_enhanced[y1:y2, x1:x2]
                if roi.size > 0:
                    results = model.predict(roi, conf=0.10, iou=0.4, verbose=False)
                    if _model_coco:
                        res_coco = _model_coco.predict(roi, conf=0.25, verbose=False)
                else:
                    results = []
            else:
                results = model.predict(frame_enhanced, conf=0.10, iou=0.4, verbose=False)
                if _model_coco:
                    res_coco = _model_coco.predict(frame, conf=0.25, verbose=False)

            if _model_coco and len(res_coco) > 0:
                for b in res_coco[0].boxes:
                    c_id = int(b.cls[0].item())
                    n = _model_coco.names[c_id]
                    bx1, by1, bx2, by2 = b.xyxy[0].tolist()
                    if person_bbox:
                        bx1 += x1; bx2 += x1
                        by1 += y1; by2 += y1
                    raw_boxes.append((int(bx1), int(by1), int(bx2), int(by2), f"COCO:{n}"))

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
