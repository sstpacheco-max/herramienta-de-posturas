from fpdf import FPDF
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NORMATIVA_EPP   = ("Resolucion 2400 de 1979 (Art. 176-177) y Decreto 1072 de 2015: "
                   "uso obligatorio de los Elementos de Proteccion Personal suministrados por el empleador.")
NORMATIVA_POSE  = ("Resolucion 2844 de 2007 (GATISO Desordenes Musculoesqueleticos) y "
                   "Decreto 1072 de 2015: prevencion del riesgo biomecanico.")

ACCIONES = {
    "Insignificante": "Ninguna accion requerida",
    "Bajo":           "Monitoreo preventivo",
    "Medio":          "Nota Verbal / Registro Dashboard",
    "Alto":           "Llamado de Atencion formal",
    "Critico":        "Citacion a Descargos inmediata",
}


def _build_pdf(title, worker_id, timestamp, risk_level, action, norm, description, evidence_path=""):
    """Construye y guarda un PDF de reporte; retorna la ruta del archivo."""
    try:
        pdf = FPDF()
        pdf.add_page()

        # Encabezado
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 14, title, 0, 1, "C")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 6, f"Generado: {timestamp}", 0, 1, "C")
        pdf.ln(4)

        # Detalles
        pdf.set_fill_color(230, 230, 230)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 9, "  DATOS DEL EVENTO", 0, 1, "L", True)
        pdf.set_font("Helvetica", "", 10)
        pdf.ln(2)

        def row(label, value, bold_val=False):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(45, 7, label, 0, 0)
            pdf.set_font("Helvetica", "B" if bold_val else "", 10)
            pdf.cell(0, 7, value, 0, 1)

        row("TRABAJADOR:", worker_id.replace("_", " ").title())
        row("FECHA Y HORA:", timestamp)
        pdf.set_text_color(180, 0, 0)
        row("NIVEL DE RIESGO:", risk_level.upper(), bold_val=True)
        pdf.set_text_color(0, 0, 0)
        row("ACCION:", action)
        row("NORMATIVA:", "", bold_val=False)
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(0, 6, norm)
        pdf.ln(4)

        # Evidencia fotográfica
        if evidence_path and os.path.exists(evidence_path):
            pdf.set_font("Helvetica", "B", 11)
            pdf.cell(0, 9, "  EVIDENCIA FOTOGRAFICA", 0, 1, "L", True)
            pdf.ln(3)
            pdf.image(evidence_path, x=20, w=170)
            pdf.ln(4)

        # Descripción
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 9, "  DESCRIPCION DE LOS HECHOS", 0, 1, "L", True)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 7, description)
        pdf.ln(8)

        # Firmas
        pdf.ln(8)
        pdf.cell(80, 8, "_" * 28, 0, 0, "C")
        pdf.cell(30, 8, "", 0, 0)
        pdf.cell(80, 8, "_" * 28, 0, 1, "C")
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(80, 6, "Firma del Trabajador", 0, 0, "C")
        pdf.cell(30, 6, "", 0, 0)
        pdf.cell(80, 6, "Coordinador SST", 0, 1, "C")

        report_dir = os.path.join(BASE_DIR, "reportes_legales")
        os.makedirs(report_dir, exist_ok=True)
        tag = title.split()[1].lower() if len(title.split()) > 1 else "reporte"
        filename = os.path.join(report_dir,
                                f"Reporte_{tag}_{worker_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        pdf.output(filename)
        print(f"PDF generado: {filename}")
        return filename
    except Exception as e:
        print(f"ERROR generando PDF: {e}")
        return None


def create_epp_report(worker_id, epp_missing, epp_detected, risk_level, evidence_path=""):
    """Reporte individual para violaciones de EPP."""
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    accion = ACCIONES.get(risk_level, "Revision requerida")
    missing_str  = ", ".join(epp_missing)  if epp_missing  else "Ninguno"
    detected_str = ", ".join(epp_detected) if epp_detected else "Ninguno"
    desc = (
        f"El {ts}, el sistema SST 4.0 detecto incumplimiento en el uso de EPP.\n\n"
        f"EPP FALTANTES: {missing_str}\n"
        f"EPP DETECTADOS: {detected_str}\n"
        f"NIVEL DE RIESGO: {risk_level}\n\n"
        f"NORMATIVA INCUMPLIDA: {NORMATIVA_EPP}\n\n"
        "Este documento sirve como notificacion formal y registro de evidencia."
    )
    return _build_pdf(
        "REPORTE EPP - Elementos de Proteccion Personal",
        worker_id, ts, risk_level, accion, NORMATIVA_EPP, desc, evidence_path
    )


def create_posture_report(worker_id, method, score, risk_level, evidence_path=""):
    """Reporte individual para violaciones de postura (RULA/REBA)."""
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    accion = ACCIONES.get(risk_level, "Revision requerida")
    method_clean = method.replace("+EPP", "")
    desc = (
        f"El {ts}, el sistema SST 4.0 detecto una postura biomecanica de riesgo.\n\n"
        f"METODO DE ANALISIS: {method_clean}\n"
        f"PUNTUACION: {score}\n"
        f"NIVEL DE RIESGO: {risk_level}\n\n"
        f"NORMATIVA INCUMPLIDA: {NORMATIVA_POSE}\n\n"
        "Este documento sirve como notificacion formal y registro de evidencia."
    )
    return _build_pdf(
        f"REPORTE POSTURA - Analisis {method_clean}",
        worker_id, ts, risk_level, accion, NORMATIVA_POSE, desc, evidence_path
    )


def create_document_draft(worker_id, worker_name, method, risk_level, evidence_path="", details=None):
    """Compatibilidad con código existente — genera EPP o postura según el método."""
    if "EPP" in method and details:
        detected = []
        return create_epp_report(worker_id, details, detected, risk_level, evidence_path)
    else:
        return create_posture_report(worker_id, method, 0, risk_level, evidence_path)
