document.addEventListener('DOMContentLoaded', () => {
    const activeCamerasViewport = document.getElementById('active-cameras-viewport');
    const modalCamera = document.getElementById('modal-camera');
    const btnAddCam = document.getElementById('btn-add-cam');
    const btnAddCamTop = document.getElementById('btn-add-cam-top');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const cameraForm = document.getElementById('camera-form');
    
    // --- Modo Demo para GitHub Pages ---
    const isGitHubPages = window.location.hostname.includes('github.io');
    if (isGitHubPages) {
        document.getElementById('system-status-text').textContent = 'MODO DEMO (Visual)';
        document.getElementById('active-cameras-viewport').innerHTML = `
            <div style="text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: center;">
                <img src="preview.png" style="max-height: 85%; max-width: 100%; object-fit: contain; border-radius: 8px; box-shadow: 0 0 20px rgba(0,0,0,0.5);">
                <p style="margin-top: 5px; font-size: 0.8rem; color: var(--accent-blue);">Simulación en tiempo real activa</p>
            </div>
        `;
        // Iniciar simulación de datos para demo
        setInterval(simulateDemoData, 3000);
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
    if (btnAddCam) btnAddCam.onclick = () => modalCamera.style.display = 'flex';
    if (btnAddCamTop) btnAddCamTop.onclick = () => modalCamera.style.display = 'flex';
    if (btnCloseModal) btnCloseModal.onclick = () => modalCamera.style.display = 'none';

    cameraForm.onsubmit = async (e) => {
        e.preventDefault();
        
        const url = document.getElementById('camera-url').value;
        const method = document.getElementById('method').value;

        if (isGitHubPages) {
            modalCamera.style.display = 'none';
            
            if (url === '0' || url === '') {
                // Simulación visual con MediaPipe JS para Cámara Local
                activeCamerasViewport.innerHTML = `
                    <div class="video-wrapper" style="width: 100%; height: 100%; position: relative;">
                        <video id="web-video" autoplay playsinline style="display: none;"></video>
                        <canvas id="web-canvas" style="width: 100%; height: 100%; object-fit: contain; border-radius: 8px;"></canvas>
                        <div style="position: absolute; top: 10px; left: 10px; background: rgba(0,230,118,0.8); padding: 5px 10px; border-radius: 4px; font-weight: bold; color: black; font-size: 0.8rem;">
                            <span class="blink">●</span> RASTREO IA WEB ACTIVO
                        </div>
                        <button class="stop-floating" onclick="window.location.reload()" style="position: absolute; top: 10px; right: 10px; background: rgba(255,0,0,0.5); border: none; color: white; cursor: pointer; padding: 5px 10px; border-radius: 4px;">DETENER</button>
                    </div>
                `;
                
                const videoElement = document.getElementById('web-video');
                const canvasElement = document.getElementById('web-canvas');
                const canvasCtx = canvasElement.getContext('2d');

                const pose = new Pose({locateFile: (file) => {
                    return `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`;
                }});
                
                pose.setOptions({
                    modelComplexity: 1,
                    smoothLandmarks: true,
                    enableSegmentation: false,
                    smoothSegmentation: false,
                    minDetectionConfidence: 0.5,
                    minTrackingConfidence: 0.5
                });
                
                pose.onResults((results) => {
                    if (canvasElement.width !== videoElement.videoWidth) {
                        canvasElement.width = videoElement.videoWidth;
                        canvasElement.height = videoElement.videoHeight;
                    }
                    
                    canvasCtx.save();
                    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
                    canvasCtx.drawImage(results.image, 0, 0, canvasElement.width, canvasElement.height);
                    
                    if (results.poseLandmarks) {
                        drawConnectors(canvasCtx, results.poseLandmarks, POSE_CONNECTIONS, {color: '#00e676', lineWidth: 4});
                        drawLandmarks(canvasCtx, results.poseLandmarks, {color: '#ff4d4d', lineWidth: 2, radius: 3});
                    }
                    canvasCtx.restore();
                });

                const camera = new Camera(videoElement, {
                    onFrame: async () => {
                        await pose.send({image: videoElement});
                    },
                    width: 640,
                    height: 480
                });
                camera.start().catch(err => {
                    console.error(err);
                    alert("No se pudo acceder a la cámara de la PC. Verifica los permisos de tu navegador.");
                });
            } else {
                // Es una URL de cámara IP
                activeCamerasViewport.innerHTML = `
                    <div class="video-wrapper" style="width: 100%; height: 100%; position: relative;">
                        <img src="${url}" style="width: 100%; height: 100%; object-fit: contain; border-radius: 8px;" onerror="alert('Error al cargar la cámara IP. Asegúrate de que la URL sea accesible y CORS esté permitido.')">
                        <div style="position: absolute; top: 10px; left: 10px; background: rgba(255,165,0,0.8); padding: 5px 10px; border-radius: 4px; font-weight: bold; color: black; font-size: 0.8rem;">
                            <span class="blink">●</span> CÁMARA IP CONECTADA
                        </div>
                        <button class="stop-floating" onclick="window.location.reload()" style="position: absolute; top: 10px; right: 10px; background: rgba(255,0,0,0.5); border: none; color: white; cursor: pointer; padding: 5px 10px; border-radius: 4px;">DETENER</button>
                    </div>
                `;
            }
            return;
        }

        try {
            const res = await fetch(`/api/start-stream?camera_url=${encodeURIComponent(url)}&method=${encodeURIComponent(method)}`, { method: 'POST' });
            if (res.ok) {
                modalCamera.style.display = 'none';
                renderActiveCameras(url);
            } else {
                alert('Error al iniciar la cámara en el servidor local.');
            }
        } catch (err) { 
            console.error(err); 
            alert('No se pudo conectar con el backend. ¿Está corriendo main.py?');
        }
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

    function simulateDemoData() {
        const workers = ["Operario 1", "Operario 2", "Montacarguista", "Supervisor"];
        const alerts = [
            { msg: "Falta Casco", type: "high" },
            { msg: "Postura Crítica", type: "critical" },
            { msg: "Falta Chaleco", type: "high" },
            { msg: "Área Restringida", type: "critical" }
        ];

        const randomWorker = workers[Math.floor(Math.random() * workers.length)];
        const randomAlert = alerts[Math.floor(Math.random() * alerts.length)];

        // Actualizar Alertas
        const ticker = document.getElementById('alerts-ticker');
        const li = document.createElement('li');
        li.className = `alert-item ${randomAlert.type}`;
        li.innerHTML = `
            <span class="alert-msg">Alerta: ${randomAlert.msg} - ${randomWorker}</span>
            <span class="alert-time">${new Date().toLocaleTimeString()}</span>
        `;
        ticker.prepend(li);
        if (ticker.children.length > 5) ticker.lastChild.remove();

        // Actualizar EPP
        const eppList = document.getElementById('epp-status-list');
        eppList.innerHTML = `
            <div class="worker-epp">
                <span class="worker-name">${randomWorker}</span>
                <div class="epp-items">
                    <span class="item ${Math.random() > 0.3 ? 'ok' : 'fail'}">⛑️ Casco</span>
                    <span class="item ${Math.random() > 0.2 ? 'ok' : 'fail'}">🦺 Chaleco</span>
                </div>
            </div>
            <div class="worker-epp">
                <span class="worker-name">Trabajador B</span>
                <div class="epp-items">
                    <span class="item ok">⛑️ Casco</span>
                    <span class="item fail">🥽 Lentes</span>
                </div>
            </div>
        `;

        // Actualizar Stats
        document.getElementById('stat-incidents').textContent = Math.floor(Math.random() * 50) + 10;
        document.getElementById('stat-criticals').textContent = Math.floor(Math.random() * 10);
    }

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
