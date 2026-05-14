document.addEventListener('DOMContentLoaded', () => {
    const activeCamerasViewport = document.getElementById('active-cameras-viewport');
    const modalCamera = document.getElementById('modal-camera');
    const btnAddCam = document.getElementById('btn-add-cam');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const cameraForm = document.getElementById('camera-form');
    
    // --- Modo Demo para GitHub Pages ---
    const isGitHubPages = window.location.hostname.includes('github.io');
    if (isGitHubPages) {
        document.getElementById('system-status-text').textContent = 'MODO DEMO (Visual)';
        document.getElementById('active-cameras-viewport').innerHTML = `
            <div style="text-align: center;">
                <img src="preview.png" style="max-width: 100%; border-radius: 8px; box-shadow: 0 0 20px rgba(0,0,0,0.5);">
                <p style="margin-top: 10px; color: var(--accent-blue);">Visualización previa del sistema en línea</p>
            </div>
        `;
    }

    // --- Gráficos (Chart.js) ---
    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { 
            y: { display: false },
            x: { display: false }
        },
        elements: {
            line: { tension: 0.4, borderWidth: 2, borderColor: '#4facfe' },
            point: { radius: 0 }
        }
    };

    const ergoChart = new Chart(document.getElementById('canvas-ergo-1'), {
        type: 'line',
        data: {
            labels: Array(20).fill(''),
            datasets: [{ data: Array(20).fill(0), borderColor: '#ff4d4d', backgroundColor: 'rgba(255, 77, 77, 0.1)', fill: true }]
        },
        options: chartOptions
    });

    const tensionChart = new Chart(document.getElementById('canvas-tension'), {
        type: 'line',
        data: {
            labels: Array(30).fill(''),
            datasets: [{ data: Array(30).fill(0), borderColor: '#4facfe' }]
        },
        options: chartOptions
    });

    const riskBarChart = new Chart(document.getElementById('canvas-risk-bar'), {
        type: 'bar',
        data: {
            labels: ['Ceides', 'Postura', 'EPP', 'Zonas'],
            datasets: [{
                data: [40, 60, 20, 30],
                backgroundColor: ['#4facfe', '#ffa726', '#ff4d4d', '#00e676']
            }]
        },
        options: { ...chartOptions, scales: { y: { display: true, grid: { color: 'rgba(255,255,255,0.05)' } }, x: { display: true } } }
    });

    const ergoLineChart = new Chart(document.getElementById('canvas-ergo-line'), {
        type: 'line',
        data: {
            labels: Array(10).fill(''),
            datasets: [{ data: [4, 6, 8, 5, 7, 9, 6, 8, 7, 5], borderColor: '#ffa726' }]
        },
        options: chartOptions
    });

    // --- Funciones de UI ---
    btnAddCam.onclick = () => modalCamera.style.display = 'flex';
    btnCloseModal.onclick = () => modalCamera.style.display = 'none';

    cameraForm.onsubmit = async (e) => {
        e.preventDefault();
        const url = document.getElementById('camera-url').value;
        const method = document.getElementById('method').value;

        try {
            const res = await fetch(`/api/start-stream?camera_url=${encodeURIComponent(url)}&method=${encodeURIComponent(method)}`, { method: 'POST' });
            if (res.ok) {
                modalCamera.style.display = 'none';
                renderActiveCameras(url);
            }
        } catch (err) { console.error(err); }
    };

    function renderActiveCameras(url) {
        activeCamerasViewport.innerHTML = `
            <div class="video-wrapper" style="width: 100%; height: 100%; position: relative;">
                <img src="/api/video-feed?camera_url=${encodeURIComponent(url)}" style="width: 100%; height: 100%; object-fit: contain;">
                <button class="stop-floating" onclick="stopStream('${url}')" style="position: absolute; top: 10px; right: 10px; background: rgba(255,0,0,0.5); border: none; color: white; cursor: pointer; padding: 5px 10px; border-radius: 4px;">DETENER</button>
            </div>
        `;
    }

    window.stopStream = async (url) => {
        await fetch(`/api/stop-stream?camera_url=${encodeURIComponent(url)}`, { method: 'POST' });
        activeCamerasViewport.innerHTML = '<p class="empty-state">No hay cámaras activas. Haz clic en + para iniciar.</p>';
    };

    // --- Actualización de Datos (Polling) ---
    async function updateDashboard() {
        try {
            const [statusRes, statsRes, logsRes] = await Promise.all([
                fetch('/api/status'),
                fetch('/api/stats'),
                fetch('/api/logs')
            ]);

            if (statsRes.ok) {
                const stats = await statsRes.json();
                document.getElementById('stat-incidents').textContent = stats.total_violations;
                document.getElementById('stat-criticals').textContent = stats.critical_alerts;
                
                // Actualizar gráficos con datos reales
                const dist = stats.risk_distribution;
                riskBarChart.data.datasets[0].data = [dist.Bajo, dist.Medio, dist.Alto, dist.Critico];
                riskBarChart.update();
            }

            if (logsRes.ok) {
                const logs = await logsRes.json();
                updateAlerts(logs);
                updateEPPStatus(logs);
            }

            // Simular movimiento en gráficos mini para efecto visual
            updateMiniCharts();

        } catch (e) { console.error(e); }
    }

    function updateAlerts(logs) {
        const ticker = document.getElementById('alerts-ticker');
        ticker.innerHTML = '';
        logs.reverse().slice(0, 5).forEach(log => {
            const li = document.createElement('li');
            li.className = `alert-item ${log.risk.toLowerCase() === 'critico' ? 'critical' : 'high'}`;
            li.innerHTML = `
                <span class="alert-msg">Alerta: ${log.method} - ${log.worker_id}</span>
                <span class="alert-time">${new Date(log.timestamp).toLocaleTimeString()}</span>
            `;
            ticker.appendChild(li);
        });
    }

    function updateEPPStatus(logs) {
        const eppList = document.getElementById('epp-status-list');
        // Aquí podríamos agrupar por trabajador, por ahora mostramos los últimos 2 detectados
        const latest = logs.slice(-2);
        if (latest.length > 0) {
            eppList.innerHTML = '';
            latest.forEach(log => {
                const div = document.createElement('div');
                div.className = 'worker-epp';
                const isCrit = log.risk === 'Critico';
                div.innerHTML = `
                    <span class="worker-name">${log.worker_id}</span>
                    <div class="epp-items">
                        <span class="item ${isCrit ? 'fail' : 'ok'}">${isCrit ? '⚠️' : '✅'} RIESGO: ${log.risk}</span>
                    </div>
                `;
                eppList.appendChild(div);
            });
        }
    }

    function updateMiniCharts() {
        // Ergo Chart: Valor aleatorio para simular real-time
        const ergoData = ergoChart.data.datasets[0].data;
        ergoData.push(Math.floor(Math.random() * 40) + 20);
        ergoData.shift();
        ergoChart.update('none');

        // Tension Chart
        const tensionData = tensionChart.data.datasets[0].data;
        tensionData.push(Math.floor(Math.random() * 20) + 10);
        tensionData.shift();
        tensionChart.update('none');

        // Actualizar reloj
        document.getElementById('current-time').textContent = new Date().toLocaleTimeString();
    }

    setInterval(updateDashboard, 2000);
    updateDashboard();
});
