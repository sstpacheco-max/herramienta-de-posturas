import cv2
import numpy as np

# Configuración de EPPs con rangos de color HSV
EPP_CONFIG = {
    "Casco": {
        "region": "top",
        "colors": [
            (np.array([0, 0, 180]),   np.array([180, 40, 255])),  # Blanco
            (np.array([20, 80, 150]), np.array([35, 255, 255])),  # Amarillo
            (np.array([100, 80, 80]), np.array([130, 255, 255])), # Azul
            (np.array([0, 100, 100]), np.array([10, 255, 255])),  # Rojo
        ],
        "threshold": 0.04,
        "risk_weight": 3
    },
    "Chaleco Reflectivo": {
        "region": "torso",
        "colors": [
            (np.array([5, 150, 150]),  np.array([20, 255, 255])), # Naranja
            (np.array([20, 120, 120]), np.array([38, 255, 255])), # Amarillo
            (np.array([40, 80, 100]),  np.array([80, 255, 255])), # Verde
        ],
        "threshold": 0.05,
        "risk_weight": 2
    },
    "Guantes": {
        "region": "hands",
        "colors": [
            (np.array([100, 80, 80]), np.array([130, 255, 255])), # Azul
            (np.array([35, 80, 80]),  np.array([85, 255, 255])),  # Verde
            (np.array([20, 80, 150]), np.array([35, 255, 255])),  # Amarillo
        ],
        "threshold": 0.02,
        "risk_weight": 1
    }
}

RISK_TABLE = [
    (0, "Insignificante", 0),
    (1, "Bajo", 2),
    (2, "Medio", 5),
    (4, "Alto", 8),
    (float('inf'), "Critico", 10),
]

def detect_epp(frame, person_bbox=None):
    """
    Detecta EPPs en el frame usando análisis de color HSV.
    person_bbox: (x1, y1, x2, y2) opcional para limitar región de análisis.
    Retorna dict con detected, missing, risk, score.
    """
    h, w = frame.shape[:2]
    x1, y1 = (person_bbox[0], person_bbox[1]) if person_bbox else (0, 0)
    x2, y2 = (person_bbox[2], person_bbox[3]) if person_bbox else (w, h)
    ph = max(y2 - y1, 1)

    regions = {
        "top":   frame[y1 : y1 + int(ph * 0.30), x1:x2],
        "torso": frame[y1 + int(ph * 0.20) : y1 + int(ph * 0.70), x1:x2],
        "hands": frame[y1 + int(ph * 0.55) : y2, x1:x2],
    }

    details = {}
    detected_list, missing_list = [], []
    missing_weight = 0

    for epp_name, cfg in EPP_CONFIG.items():
        region = regions.get(cfg["region"])
        if region is None or region.size == 0:
            details[epp_name] = False
            missing_list.append(epp_name)
            missing_weight += cfg["risk_weight"]
            continue

        hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
        total = region.shape[0] * region.shape[1]
        found = False

        for lower, upper in cfg["colors"]:
            mask = cv2.inRange(hsv, lower, upper)
            if total > 0 and cv2.countNonZero(mask) / total > cfg["threshold"]:
                found = True
                break

        details[epp_name] = found
        if found:
            detected_list.append(epp_name)
        else:
            missing_list.append(epp_name)
            missing_weight += cfg["risk_weight"]

    risk, score = "Insignificante", 0
    for threshold, r, s in RISK_TABLE:
        if missing_weight <= threshold:
            risk, score = r, s
            break

    return {"detected": detected_list, "missing": missing_list,
            "details": details, "risk": risk, "score": score}


def draw_epp_results(image, epp_results, y_offset=160):
    """Dibuja los resultados EPP sobre el frame."""
    for name, found in epp_results.get("details", {}).items():
        color  = (0, 200, 80) if found else (0, 50, 255)
        symbol = "OK" if found else "NO"
        cv2.putText(image, f"[{symbol}] {name}", (20, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        y_offset += 26
    return image
