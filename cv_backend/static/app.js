document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('camera-form');
    const camerasList = document.getElementById('cameras-list');
    
    // Create toast container
    const toastContainer = document.createElement('div');
    toastContainer.className = 'toast-container';
    document.body.appendChild(toastContainer);

    function showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span>${message}</span>
        `;
        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s ease-out forwards';
            setTimeout(() => {
                toastContainer.removeChild(toast);
            }, 300);
        }, 3000);
    }

    const btnLocalCam = document.getElementById('btn-local-cam');
    if (btnLocalCam) {
        btnLocalCam.onclick = () => {
            const urlInput = document.getElementById('camera-url');
            urlInput.value = '0';
            showToast('Cámara local (0) seleccionada', 'success');
        };
    }

    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const workerId = document.getElementById('worker-id').value;
            const photoFile = document.getElementById('worker-photo').files[0];

            const formData = new FormData();
            formData.append('worker_id', workerId);
            formData.append('file', photoFile);

            try {
                showToast('Procesando biometría...', 'info');
                const response = await fetch('/api/register-face', {
                    method: 'POST',
                    body: formData
                });
                if (response.ok) {
                    showToast(`¡${workerId} registrado con éxito!`, 'success');
                    registerForm.reset();
                } else {
                    showToast('Error al registrar biometría', 'error');
                }
            } catch (error) {
                showToast('Error de conexión', 'error');
            }
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const urlInput = document.getElementById('camera-url');
        const methodInput = document.getElementById('method');
        
        const url = urlInput.value.trim();
        const method = methodInput.value;

        if (!url) return;

        try {
            // Llama al backend de FastAPI para iniciar el stream
            const response = await fetch(`/api/start-stream?camera_url=${encodeURIComponent(url)}&method=${encodeURIComponent(method)}`, {
                method: 'POST'
            });

            if (response.ok) {
                showToast(`Monitoreo iniciado para: ${url}`, 'success');
                addCameraCard(url, method);
                urlInput.value = '';
            } else {
                showToast('Error al iniciar el monitoreo', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showToast('Error de conexión con el servidor', 'error');
        }
    });

    function addCameraCard(url, method) {
        // Remove empty state if it exists
        const emptyState = camerasList.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        const card = document.createElement('div');
        card.className = 'camera-card';
        card.innerHTML = `
            <div class="camera-header">
                <div class="camera-status">
                    <div class="status-dot"></div>
                    Monitoreo en Vivo
                </div>
            </div>
            <div class="video-container" style="margin: 10px 0; border-radius: 10px; overflow: hidden; background: #000; position: relative;">
                <img src="/api/video-feed?camera_url=${encodeURIComponent(url)}" style="width: 100%; display: block;" alt="Live Feed">
                <button class="btn-stop" data-url="${url}">✕</button>
            </div>
            <div class="camera-footer" style="display: flex; justify-content: space-between; align-items: flex-end;">
                <div>
                    <div class="camera-url">${url}</div>
                    <div class="camera-method">Método: ${method}</div>
                </div>
            </div>
        `;
        
        const stopBtn = card.querySelector('.btn-stop');
        stopBtn.onclick = async () => {
            try {
                const response = await fetch(`/api/stop-stream?camera_url=${encodeURIComponent(url)}`, { method: 'POST' });
                if (response.ok) {
                    card.remove();
                    showToast(`Monitoreo detenido: ${url}`, 'info');
                    if (camerasList.children.length === 0) {
                        camerasList.innerHTML = '<p class="empty-state">No hay cámaras activas en este momento.</p>';
                    }
                }
            } catch (e) { console.error(e); }
        };
        
        camerasList.appendChild(card);
    }

    // Polling de estadísticas
    async function fetchStats() {
        try {
            const [statusRes, statsRes] = await Promise.all([
                fetch('/api/status'),
                fetch('/api/stats')
            ]);
            
            if (statusRes.ok && statsRes.ok) {
                const status = await statusRes.json();
                const stats = await statsRes.json();
                
                document.getElementById('stat-total-violations').textContent = stats.total_violations;
                document.getElementById('stat-critical-alerts').textContent = stats.critical_alerts;
                document.getElementById('stat-uptime').textContent = status.uptime;
                
                const n8nStatus = document.getElementById('stat-n8n-status');
                if (status.n8n_errors > 0 && status.n8n_success === 0) {
                    n8nStatus.textContent = 'Error';
                    n8nStatus.style.color = 'var(--accent)';
                } else {
                    n8nStatus.textContent = status.n8n_success > 0 ? `Activo (${status.n8n_success})` : 'Conectado';
                    n8nStatus.style.color = 'var(--success)';
                }
            }
        } catch (error) {
            console.error('Error fetching stats:', error);
        }
    }

    // Polling de logs cada 3 segundos para mayor dinamismo
    async function fetchLogs() {
        try {
            const response = await fetch('/api/logs');
            if (response.ok) {
                const logs = await response.json();
                renderLogs(logs);
            }
        } catch (error) {
            console.error('Error fetching logs:', error);
        }
    }

    function renderLogs(logs) {
        const logsBody = document.getElementById('logs-body');
        if (!logs || logs.length === 0) return;

        logsBody.innerHTML = '';
        // Mostramos los últimos 10 logs de forma invertida (más recientes arriba)
        [...logs].reverse().slice(0, 10).forEach(log => {
            const row = document.createElement('tr');
            const date = new Date(log.timestamp).toLocaleTimeString();
            const riskClass = log.risk.toLowerCase() === 'alto' ? 'risk-alto' : 
                             log.risk.toLowerCase() === 'critico' ? 'risk-critico' : '';
            
            row.innerHTML = `
                <td>${date}</td>
                <td><strong>${log.worker_id}</strong></td>
                <td>${log.method}</td>
                <td>${log.score}</td>
                <td><span class="risk-tag ${riskClass}">${log.risk}</span></td>
                <td>${log.duration || '0s'}</td>
                <td><a href="/api/download-doc?path=${encodeURIComponent(log.legal_doc)}" class="btn-doc" target="_blank">📄 Descargar</a></td>
            `;
            logsBody.appendChild(row);
        });
    }

    setInterval(() => {
        fetchLogs();
        fetchStats();
    }, 3000);

    fetchLogs();
    fetchStats();
});
