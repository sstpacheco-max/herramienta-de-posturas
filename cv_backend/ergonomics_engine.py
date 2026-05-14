import math

def calculate_angle_3d(p1, p2, p3):
    """Calcula el ángulo entre tres puntos (en grados). p2 es el vértice."""
    if not all([p1, p2, p3]): return 0
    try:
        # Vectores p2->p1 y p2->p3
        v1 = (p1.x - p2.x, p1.y - p2.y, p1.z - p2.z)
        v2 = (p3.x - p2.x, p3.y - p2.y, p3.z - p2.z)
        
        dot_product = v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2]
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2 + v1[2]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2 + v2[2]**2)
        
        if mag1 == 0 or mag2 == 0: return 0
        
        angle = math.acos(max(-1.0, min(1.0, dot_product / (mag1 * mag2))))
        return math.degrees(angle)
    except:
        return 0

def get_rula_score(landmarks):
    """
    Evaluación simplificada RULA basada en ángulos de MediaPipe.
    Retorna (puntuacion_final, nivel_riesgo).
    """
    if not landmarks: return 1, "Insignificante"

    # 1. Brazo (Hombro -> Codo -> Muñeca)
    # Puntos MediaPipe: 11(h_izq), 12(h_der), 13(c_izq), 15(m_izq)
    try:
        hombro = landmarks[11]
        codo = landmarks[13]
        muneca = landmarks[15]
        tronco_inf = landmarks[23] # Cadera izq
        
        # Flexión del brazo (Ángulo respecto a la vertical del tronco)
        angle_brazo = calculate_angle_3d(tronco_inf, hombro, codo)
        score_brazo = 1
        if 20 < angle_brazo <= 45: score_brazo = 2
        elif 45 < angle_brazo <= 90: score_brazo = 3
        elif angle_brazo > 90: score_brazo = 4

        # Flexión de antebrazo
        angle_antebrazo = calculate_angle_3d(hombro, codo, muneca)
        score_antebrazo = 1
        if angle_antebrazo < 60 or angle_antebrazo > 100: score_antebrazo = 2

        # Flexión de tronco (simplificado)
        angle_tronco = calculate_angle_3d(hombro, tronco_inf, landmarks[25]) # Rodilla
        score_tronco = 1
        if 0 < angle_tronco <= 20: score_tronco = 2
        elif 20 < angle_tronco <= 60: score_tronco = 3
        elif angle_tronco > 60: score_tronco = 4

        # Puntuación final integrada (Lógica simplificada de tablas RULA)
        final_score = int((score_brazo + score_antebrazo + score_tronco) / 1.5) + 1
        final_score = min(7, final_score)

        risk_levels = {
            1: "Insignificante", 2: "Insignificante",
            3: "Bajo", 4: "Bajo",
            5: "Medio", 6: "Alto",
            7: "Critico"
        }
        
        return final_score, risk_levels.get(final_score, "Desconocido")
    except Exception as e:
        return 1, f"Error: {e}"

def get_reba_score(landmarks):
    """Evaluación REBA simplificada."""
    # Lógica similar a RULA pero incluyendo piernas
    final_score, risk = get_rula_score(landmarks) # Fallback temporal
    # REBA suele ser más severo
    reba_score = min(15, final_score * 2)
    
    reba_risks = {
        (1, 1): "Insignificante",
        (2, 3): "Bajo",
        (4, 7): "Medio",
        (8, 10): "Alto",
        (11, 15): "Critico"
    }
    
    for (min_s, max_s), r in reba_risks.items():
        if min_s <= reba_score <= max_s:
            return reba_score, r
            
    return reba_score, "Muy Alto"
