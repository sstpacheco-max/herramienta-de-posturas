// Lógica para Generar el Informe SST 4.0

function getErgoRecommendation(method, score) {
    if (method === 'REBA') {
        if (score <= 3) return { level: 'Riesgo Bajo', text: 'Mantener posturas actuales, realizar pausas activas preventivas.' };
        if (score <= 7) return { level: 'Riesgo Medio', text: 'Se requiere investigación adicional y posibles modificaciones en la estación de trabajo.' };
        if (score <= 10) return { level: 'Riesgo Alto', text: 'Actuación y rediseño de tareas a corto plazo.' };
        return { level: 'Riesgo Muy Alto', text: 'Actuación inmediata. Pausar actividad hasta rediseñar el puesto.' };
    } else if (method === 'RULA') {
        if (score <= 2) return { level: 'Riesgo Insignificante', text: 'Postura aceptable.' };
        if (score <= 4) return { level: 'Riesgo Bajo', text: 'Pueden requerirse cambios en la tarea; es conveniente una investigación más profunda.' };
        if (score <= 6) return { level: 'Riesgo Medio/Alto', text: 'Se requiere investigación y cambios a corto plazo.' };
        return { level: 'Riesgo Muy Alto', text: 'Se requieren investigación y cambios inmediatos en el puesto de trabajo.' };
    } else if (method === 'OWAS') {
        if (score === 1) return { level: 'Categoría 1', text: 'Posturas normales.' };
        if (score === 2) return { level: 'Categoría 2', text: 'Posturas con posibilidad de causar daño. Requiere acciones correctivas en un futuro cercano.' };
        return { level: 'Categoría 3/4', text: 'Posturas dañinas. Acciones correctivas urgentes.' };
    }
    return { level: 'N/A', text: 'Método no especificado.' };
}

function getEppRecommendation(casco, chaleco) {
    let missing = [];
    if (!casco) missing.push('Casco');
    if (!chaleco) missing.push('Chaleco');

    if (missing.length === 0) return { status: 'Cumple (100%)', text: 'Ninguna acción requerida. Mantener supervisión.' };
    
    let recs = [];
    if (!casco) recs.push('Restringir acceso al área de operaciones. Programar charla de seguridad obligatoria sobre protección craneal.');
    if (!chaleco) recs.push('Proveer chaleco de alta visibilidad inmediatamente para evitar atropellos por maquinaria.');
    
    return { status: `Falta: ${missing.join(', ')}`, text: recs.join(' ') };
}

function generarInformeHTML(data) {
    const date = new Date().toLocaleDateString('es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute:'2-digit' });
    const ergoRec = getErgoRecommendation(data.method, data.score);
    const eppRec = getEppRecommendation(data.epp.casco, data.epp.chaleco);

    return `
        <div style="font-family: Arial, sans-serif; color: #333; background: #fff; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 1rem; margin-bottom: 2rem;">
                <h1 style="color: #2c3e50; margin: 0; font-size: 24px;">REPORTE DE EVALUACIÓN SST 4.0</h1>
                <p style="color: #7f8c8d; margin: 5px 0 0 0;">Generado el ${date}</p>
            </div>
            
            <h3 style="color: #2980b9; border-bottom: 1px solid #eee; padding-bottom: 5px;">1. Evaluación Ergonómica (${data.method})</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 2rem; font-size: 14px;">
                <tr style="background: #ecf0f1;">
                    <th style="padding: 10px; border: 1px solid #bdc3c7; text-align: left;">Puntuación Detectada</th>
                    <th style="padding: 10px; border: 1px solid #bdc3c7; text-align: left;">Nivel de Riesgo</th>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #bdc3c7; font-weight: bold; font-size: 18px; text-align: center;">${data.score}</td>
                    <td style="padding: 10px; border: 1px solid #bdc3c7;">
                        <strong>${ergoRec.level}</strong><br>
                        <span style="color: #c0392b; font-weight: 500;">Recomendación:</span> ${ergoRec.text}
                    </td>
                </tr>
            </table>

            <h3 style="color: #2980b9; border-bottom: 1px solid #eee; padding-bottom: 5px;">2. Cumplimiento de EPP</h3>
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 2rem; font-size: 14px;">
                <tr style="background: #ecf0f1;">
                    <th style="padding: 10px; border: 1px solid #bdc3c7; text-align: left;">Estado de Uso</th>
                    <th style="padding: 10px; border: 1px solid #bdc3c7; text-align: left;">Acción Correctiva</th>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #bdc3c7; color: ${eppRec.status.includes('Cumple') ? '#27ae60' : '#e74c3c'}; font-weight: bold;">
                        ${eppRec.status}
                    </td>
                    <td style="padding: 10px; border: 1px solid #bdc3c7;">
                        ${eppRec.text}
                    </td>
                </tr>
            </table>

            <div style="margin-top: 4rem; text-align: center;">
                <div style="display: inline-block; width: 200px; border-top: 1px solid #333; padding-top: 10px;">
                    Firma Supervisor SST
                </div>
            </div>
        </div>
    `;
}

function initReportModal(getDataCallback) {
    const btnOpen = document.getElementById('btn-generar-informe');
    const modal = document.getElementById('modal-informe');
    const btnClose = document.getElementById('btn-close-informe');
    const btnPrint = document.getElementById('btn-print-report');
    const reportBody = document.getElementById('report-body');

    if (btnOpen) {
        btnOpen.addEventListener('click', () => {
            const data = getDataCallback();
            if (reportBody) reportBody.innerHTML = generarInformeHTML(data);
            if (modal) modal.style.display = 'flex';
        });
    }

    if (btnClose) {
        btnClose.addEventListener('click', () => {
            if (modal) modal.style.display = 'none';
        });
    }

    if (btnPrint) {
        btnPrint.addEventListener('click', () => {
            // Se imprimirá la ventana. Se requiere CSS @media print
            window.print();
        });
    }
}
