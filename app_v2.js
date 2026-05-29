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
                <p style="margin-top: 5px; font-size: 0.9rem; color: var(--text-muted);">El sistema está listo. Haz clic en ➕ para iniciar tu cámara.</p>
            </div>
        `;
        // Limpiamos alertas de prueba iniciales
        document.getElementById('alerts-ticker').innerHTML = '';
        
        // Iniciar simulación de estadísticas base (sin spam de alertas)
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
                
                    let lastAlertTime = 0;
                    let lastEppAlertTime = 0;

                    // Función heurística para detectar colores EPP (blanco, amarillo, verde, naranja brillante)
                    function calcWebEPP(ctx, landmarks) {
                        if(!landmarks || landmarks.length < 26) return {casco: true, chaleco: true};
                        const w = ctx.canvas.width; const h = ctx.canvas.height;
                        
                        const checkZone = (x_norm, y_norm, radius) => {
                            const cx = Math.floor(x_norm * w); const cy = Math.floor(y_norm * h);
                            if (cx < radius || cx + radius >= w || cy < radius || cy + radius >= h) return false;
                            try {
                                const imgData = ctx.getImageData(cx - radius, cy - radius, radius*2, radius*2);
                                let r=0, g=0, b=0;
                                for(let i=0; i<imgData.data.length; i+=4) { r += imgData.data[i]; g += imgData.data[i+1]; b += imgData.data[i+2]; }
                                const pixels = imgData.data.length / 4; r /= pixels; g /= pixels; b /= pixels;
                                const brightness = (r + g + b) / 3;
                                if (brightness > 180) return true; // Blanco/Claro
                                if (r > 150 && g > 150 && b < 100) return true; // Amarillo
                                if (r > 200 && g > 100 && b < 100) return true; // Naranja
                                if (g > 180 && r < 100 && b < 100) return true; // Verde fluor
                                return false;
                            } catch(e) { return true; }
                        };

                        const nariz = landmarks[0];
                        const h_izq = landmarks[11], h_der = landmarks[12];
                        return {
                            casco: checkZone(nariz.x, nariz.y - 0.15, 15),
                            chaleco: checkZone((h_izq.x + h_der.x)/2, (h_izq.y + h_der.y)/2 + 0.15, 25)
                        };
                    }
                    
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
                            
                            // Extraer métricas biomecánicas reales en el cliente web
                            const metrics = calcWebBiomechanics(results.poseLandmarks);
                            updateTelemetryCharts({
                                score: metrics.score, // Puntuación ergonómica estimada
                                compression: metrics.compression,
                                com: metrics.com
                            });
                            
                            // Detección ligera de EPP por colorimetría
                            const epp = calcWebEPP(canvasCtx, results.poseLandmarks);
                            
                            // Actualizar UI de EPP en tiempo real
                            const eppList = document.getElementById('epp-status-list');
                            if (eppList) {
                                eppList.innerHTML = `
                                    <div class="worker-epp">
                                        <span class="worker-name">Cámara Web</span>
                                        <div class="epp-items">
                                            <span class="item ${epp.casco ? 'ok' : 'fail'}">${epp.casco ? '✅' : '❌'} Casco</span>
                                            <span class="item ${epp.chaleco ? 'ok' : 'fail'}">${epp.chaleco ? '✅' : '❌'} Chaleco</span>
                                        </div>
                                    </div>
                                `;
                            }
                            
                            // Generar alerta real si hay mala postura (throttle de 5 segundos)
                            const now = Date.now();
                            if (metrics.score >= 4 && (now - lastAlertTime > 5000)) {
                                lastAlertTime = now;
                                const ticker = document.getElementById('alerts-ticker');
                                const li = document.createElement('li');
                                const isCrit = metrics.score >= 7;
                                li.className = `alert-item ${isCrit ? 'critical' : 'high'}`;
                                li.innerHTML = `
                                    <span class="alert-msg">Alerta: ${isCrit ? 'Postura Peligrosa' : 'Mala Postura'} Detectada - Cámara Web</span>
                                    <span class="alert-time">${new Date().toLocaleTimeString()}</span>
                                `;
                                ticker.prepend(li);
                                if (ticker.children.length > 5) ticker.lastChild.remove();
                            }

                            // Generar alerta de falta de EPP (throttle de 6 segundos)
                            if (!epp.casco || !epp.chaleco) {
                                if (now - lastEppAlertTime > 6000) {
                                    lastEppAlertTime = now;
                                    const ticker = document.getElementById('alerts-ticker');
                                    const li = document.createElement('li');
                                    li.className = 'alert-item high';
                                    const faltante = !epp.casco && !epp.chaleco ? 'Casco y Chaleco' : (!epp.casco ? 'Casco' : 'Chaleco');
                                    li.innerHTML = `
                                        <span class="alert-msg">Alerta: Falta ${faltante} - Cámara Web</span>
                                        <span class="alert-time">${new Date().toLocaleTimeString()}</span>
                                    `;
                                    ticker.prepend(li);
                                    if (ticker.children.length > 5) ticker.lastChild.remove();
                                }
                            }
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

        // (Se eliminó el código que generaba alertas falsas constantes en el ticker)

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

            // El movimiento de gráficos ahora se maneja por WebSocket (telemetría real)
            document.getElementById('current-time').textContent = new Date().toLocaleTimeString();

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
            // Funciones Matemáticas Biomecánicas para la versión Online Web
    function calculateAngle3D(p1, p2, p3) {
        if (!p1 || !p2 || !p3) return 0;
        const v1 = {x: p1.x - p2.x, y: p1.y - p2.y, z: p1.z - p2.z};
        const v2 = {x: p3.x - p2.x, y: p3.y - p2.y, z: p3.z - p2.z};
        const dot = v1.x*v2.x + v1.y*v2.y + v1.z*v2.z;
        const mag1 = Math.sqrt(v1.x*v1.x + v1.y*v1.y + v1.z*v1.z);
        const mag2 = Math.sqrt(v2.x*v2.x + v2.y*v2.y + v2.z*v2.z);
        if(mag1 === 0 || mag2 === 0) return 0;
        return Math.acos(Math.max(-1.0, Math.min(1.0, dot / (mag1 * mag2)))) * (180 / Math.PI);
    }

    function calcWebBiomechanics(landmarks) {
        if(!landmarks || landmarks.length < 26) return {com: [0.5, 0.5], compression: 0, score: 1};
        const h_izq = landmarks[11], h_der = landmarks[12];
        const c_izq = landmarks[23], c_der = landmarks[24];
        const r_izq = landmarks[25];
        
        // Estabilograma
        const x_com = (h_izq.x + h_der.x + c_izq.x + c_der.x) / 4.0;
        const z_com = (h_izq.z + h_der.z + c_izq.z + c_der.z) / 4.0;

        // Compresión L4/L5
        const angle_tronco = calculateAngle3D(h_izq, c_izq, r_izq);
        const peso_sup = 75 * 0.60;
        const fuerza_gravedad = peso_sup * 9.81;
        const angle_rad = Math.min(angle_tronco, 90) * (Math.PI / 180);
        const momento_flexion = fuerza_gravedad * 0.3 * Math.sin(angle_rad);
        const fuerza_muscular = momento_flexion / 0.05;
        const compresion = (fuerza_gravedad * Math.cos(angle_rad)) + fuerza_muscular;
        
        // Puntuación RULA/REBA muy simplificada
        let score = 2;
        if (angle_tronco > 20) score = 4;
        if (angle_tronco > 60) score = 7;

        return {com: [x_com, z_com], compression: compresion, score: score};
    }

    // --- WebSockets y Telemetría Real-Time ---
    const wsUrl = (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/ws/alerts';
    let ws;

    function connectWebSocket() {
        if (isGitHubPages) return;
        
        ws = new WebSocket(wsUrl);
        
        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'telemetry') {
                    updateTelemetryCharts(data);
                } else if (data.type === 'alert') {
                    updateDashboard(); 
                }
            } catch(e) {}
        };
        
        ws.onclose = () => {
            setTimeout(connectWebSocket, 3000);
        };
    }

    function drawStabilogram(comX, comZ) {
        const canvas = document.getElementById('canvas-stabilogram');
        if(!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width;
        const h = canvas.height;
        
        ctx.clearRect(0, 0, w, h);
        
        // Ejes
        ctx.strokeStyle = 'rgba(255,255,255,0.2)';
        ctx.beginPath();
        ctx.moveTo(w/2, 0); ctx.lineTo(w/2, h);
        ctx.moveTo(0, h/2); ctx.lineTo(w, h/2);
        ctx.stroke();
        
        // Mapeo (MediaPipe Z suele estar entre -1 y 1)
        let cx = w/2 + (comX - 0.5) * w * 2; 
        let cy = h/2 + (comZ) * h; 
        
        cx = Math.max(10, Math.min(w-10, cx));
        cy = Math.max(10, Math.min(h-10, cy));
        
        const dist = Math.hypot(cx - w/2, cy - h/2);
        const color = dist > (w/2)*0.6 ? '#ff4d4d' : (dist > (w/2)*0.3 ? '#ffa726' : '#00e676');

        ctx.shadowBlur = 10;
        ctx.shadowColor = color;
        ctx.beginPath();
        ctx.arc(cx, cy, 8, 0, Math.PI*2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.shadowBlur = 0;
    }

    function updateTelemetryCharts(data) {
        // Ergo Chart (Score RULA/REBA)
        const ergoData = ergoChart.data.datasets[0].data;
        ergoData.push(data.score);
        ergoData.shift();
        ergoChart.update('none');

        // Tension Chart (Compresión L4/L5)
        const tensionData = tensionChart.data.datasets[0].data;
        tensionData.push(data.compression || 0);
        tensionData.shift();
        tensionChart.update('none');
        
        if (data.com) {
            drawStabilogram(data.com[0], data.com[1]);
        }
    }

    setInterval(updateDashboard, 2000);
    updateDashboard();
    connectWebSocket();
    // --- Lógica de Carga de Video ---
    const videoUpload = document.getElementById('video-upload');
    const uploadZone = document.getElementById('upload-zone');
    const loadingSim = document.getElementById('loading-sim');
    const progressBar = document.getElementById('progress-bar');
    const mainVideoContainer = document.getElementById('main-video-container');

    if (videoUpload && uploadZone && loadingSim) {
        // Drag and drop events
        mainVideoContainer.addEventListener('dragover', (e) => {
            e.preventDefault();
            mainVideoContainer.style.borderColor = 'var(--accent-green)';
        });
        mainVideoContainer.addEventListener('dragleave', (e) => {
            e.preventDefault();
            mainVideoContainer.style.borderColor = 'rgba(79, 172, 254, 0.5)';
        });
        mainVideoContainer.addEventListener('drop', (e) => {
            e.preventDefault();
            mainVideoContainer.style.borderColor = 'rgba(79, 172, 254, 0.5)';
            if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                videoUpload.files = e.dataTransfer.files;
                startProcessing();
            }
        });

        videoUpload.addEventListener('change', (e) => {
            if (videoUpload.files && videoUpload.files.length > 0) {
                startProcessing();
            }
        });

        function startProcessing() {
            uploadZone.style.display = 'none';
            loadingSim.style.display = 'block';
            mainVideoContainer.onclick = null; // Disable clicking
            mainVideoContainer.style.cursor = 'default';
            
            // Simular carga e IA
            let progress = 0;
            const interval = setInterval(() => {
                progress += Math.random() * 15;
                if (progress >= 100) {
                    progress = 100;
                    clearInterval(interval);
                    document.getElementById('loading-text').textContent = 'Análisis Completado. Redirigiendo...';
                    setTimeout(() => {
                        window.location.href = 'analisis.html';
                    }, 1000);
                }
                progressBar.style.width = progress + '%';
            }, 300);
        }
    }
});
