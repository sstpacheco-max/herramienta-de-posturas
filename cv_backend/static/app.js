document.addEventListener('DOMContentLoaded', () => {
    const activeCamerasViewport = document.getElementById('active-cameras-viewport');
    const modalCamera = document.getElementById('modal-camera');
    const btnAddCam = document.getElementById('btn-add-cam');
    const btnAddCamTop = document.getElementById('btn-add-cam-top');
    const btnCloseModal = document.getElementById('btn-close-modal');
    const cameraForm = document.getElementById('camera-form');
    
    // --- Firebase Initialization ---
    const firebaseConfig = {
        apiKey: "AIzaSyDAp8r9ZDRTY_3BHWtl-N9qtb0VsFTqV-w",
        authDomain: "deteccion-de-posturas-y-epps.firebaseapp.com",
        databaseURL: "https://deteccion-de-posturas-y-epps-default-rtdb.firebaseio.com",
        projectId: "deteccion-de-posturas-y-epps",
        storageBucket: "deteccion-de-posturas-y-epps.firebasestorage.app",
        messagingSenderId: "553248719917",
        appId: "1:553248719917:web:9ae9df2504acf21441a4a4"
    };

    // Inicializar Firebase
    firebase.initializeApp(firebaseConfig);
    const database = firebase.database();
    
    // Detectamos si es GitHub Pages para ocultar el reproductor local
    const isGitHubPages = window.location.hostname.includes('github.io');
    if (isGitHubPages) {
        document.getElementById('system-status-text').textContent = 'MODO REMOTO (Firebase)';
        document.getElementById('active-cameras-viewport').innerHTML = `
            <div style="text-align: center; height: 100%; display: flex; flex-direction: column; justify-content: center;">
                <p style="margin-top: 5px; font-size: 1rem; color: var(--accent-blue);">🖥️ Conectado remotamente vía Firebase.</p>
                <p style="font-size: 0.8rem; color: gray;">El video en vivo se procesa en el servidor local. Este panel muestra alertas y métricas en tiempo real.</p>
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

    // --- Audio Alarm (AudioContext) ---
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    function playAlarmSound() {
        if (audioCtx.state === 'suspended') audioCtx.resume();
        const osc = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        
        osc.type = 'square';
        osc.frequency.setValueAtTime(800, audioCtx.currentTime); // 800Hz
        osc.frequency.exponentialRampToValueAtTime(1200, audioCtx.currentTime + 0.1);
        
        gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime); // Volumen al 10%
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.5);
        
        osc.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        
        osc.start();
        osc.stop(audioCtx.currentTime + 0.5);
    }

    // --- Firebase Listeners ---
    function initFirebaseListeners() {
        console.log("Iniciando listeners de Firebase...");
        const alertsRef = database.ref('alerts').orderByChild('timestamp').limitToLast(5);
        
        let initialDataLoaded = false;
        
        alertsRef.on('child_added', (snapshot) => {
            const data = snapshot.val();
            if (!data) return;
            
            if (initialDataLoaded) {
                // Visual Flash de alerta
                document.body.style.boxShadow = "inset 0 0 50px rgba(255,0,0,0.8)";
                setTimeout(() => document.body.style.boxShadow = "none", 500);

                // Alarma Sonora
                if(data.risk === 'Alto' || data.risk === 'Critico') {
                    playAlarmSound();
                }
            }
            
            // Actualizar interfaz
            updateAlerts([data], true);
            updateEPPStatus([data], true);
        });

        alertsRef.once('value', () => {
            initialDataLoaded = true;
        });

        // Listener global de stats
        database.ref('stats').on('value', (snapshot) => {
            const stats = snapshot.val();
            if (stats) {
                document.getElementById('stat-incidents').textContent = stats.total_violations || 0;
                document.getElementById('stat-criticals').textContent = stats.critical_alerts || 0;
                
                const dist = stats.risk_distribution || {};
                riskBarChart.data.datasets[0].data = [dist.Bajo || 0, dist.Medio || 0, dist.Alto || 0, dist.Critico || 0];
                riskBarChart.update();
            }
        });
    }
    
    initFirebaseListeners();

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
        \`;
    }
    window.stopStream = async (url) => {
        await fetch(`/api/stop-stream?camera_url=${encodeURIComponent(url)}`, { method: 'POST' });
        activeCamerasViewport.innerHTML = '<p class="empty-state">No hay cámaras activas. Haz clic en + para iniciar.</p>';
    };

    // --- Actualización de Datos (Polling para Estadísticas Globales local) ---
    async function updateDashboard() {
        if (isGitHubPages) return;
        try {
            const [statusRes, statsRes] = await Promise.all([
                fetch('/api/status'),
                fetch('/api/stats')
            ]);

            if (statsRes.ok) {
                const stats = await statsRes.json();
                document.getElementById('stat-incidents').textContent = stats.total_violations;
                document.getElementById('stat-criticals').textContent = stats.critical_alerts;
                
                // Actualizar gráficos con datos reales
                const dist = stats.risk_distribution;
                riskBarChart.data.datasets[0].data = [dist.Bajo || 0, dist.Medio || 0, dist.Alto || 0, dist.Critico || 0];
                riskBarChart.update();
            }

            // Simular movimiento en gráficos mini para efecto visual
            updateMiniCharts();

        } catch (e) { console.error(e); }
    }

    function updateAlerts(logs, prepend=false) {
        const ticker = document.getElementById('alerts-ticker');
        if(!prepend) ticker.innerHTML = '';
        
        logs.slice(0, 5).forEach(log => {
            const li = document.createElement('li');
            li.className = `alert-item ${log.risk.toLowerCase() === 'critico' ? 'critical' : 'high'}`;
            li.innerHTML = `
                <span class="alert-msg">Alerta: ${log.method} - ${log.worker_id}</span>
                <span class="alert-time">${new Date(log.timestamp).toLocaleTimeString()}</span>
                ${log.legal_doc ? `<a href="/api/download-doc?path=${encodeURIComponent(log.legal_doc)}" target="_blank" style="margin-left:10px; color:#fff; text-decoration:underline; font-size:12px;">📄 PDF</a>` : ''}
            `;
            if(prepend) {
                ticker.prepend(li);
                if (ticker.children.length > 5) ticker.lastChild.remove();
            } else {
                ticker.appendChild(li);
            }
        });
    }

    function updateEPPStatus(logs, prepend=false) {
        const eppList = document.getElementById('epp-status-list');
        const latest = logs.slice(0, 2);
        if (latest.length > 0) {
            if(!prepend) eppList.innerHTML = '';
            latest.forEach(log => {
                const div = document.createElement('div');
                div.className = 'worker-epp';
                const isCrit = log.risk === 'Critico' || log.risk === 'Alto';
                div.innerHTML = `
                    <span class="worker-name">${log.worker_id}</span>
                    <div class="epp-items">
                        <span class="item ${isCrit ? 'fail' : 'ok'}">${isCrit ? '⚠️' : '✅'} RIESGO: ${log.risk}</span>
                    </div>
                `;
                if(prepend) {
                    eppList.prepend(div);
                    if (eppList.children.length > 3) eppList.lastChild.remove();
                } else {
                    eppList.appendChild(div);
                }
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

    if (!isGitHubPages) {
        fetch('/api/logs').then(r=>r.json()).then(logs => {
            if (logs && logs.length > 0) {
                updateAlerts(logs.reverse());
                updateEPPStatus(logs);
            }
        }).catch(e => console.log("Logs locales no disponibles"));
    }
    
    setInterval(updateDashboard, 5000);
    setInterval(updateMiniCharts, 1000);
    updateDashboard();
});
