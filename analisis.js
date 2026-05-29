document.addEventListener('DOMContentLoaded', () => {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const headerTitle = document.getElementById('header-title');
    const methodViews = document.querySelectorAll('.method-view');
    const resultsTables = document.querySelectorAll('.results-table');
    const eppOverlay = document.getElementById('epp-overlay');

    const methodTitles = {
        'reba': 'ANÁLISIS POR MÉTODO REBA',
        'owas': 'ANÁLISIS POR MÉTODO OWAS',
        'repetitivas': 'ANÁLISIS POR MÉTODO REPETITIVAS',
        'epp': 'IDENTIFICACIÓN DE EPP'
    };

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active from all tabs
            tabBtns.forEach(b => b.classList.remove('active'));
            // Add active to clicked tab
            btn.classList.add('active');

            const targetMethod = btn.getAttribute('data-target');

            // Update title
            headerTitle.textContent = methodTitles[targetMethod];

            // Toggle right panel views
            methodViews.forEach(view => {
                view.classList.remove('active');
            });
            document.getElementById(`view-${targetMethod}`).classList.add('active');

            // Toggle bottom tables
            resultsTables.forEach(table => {
                table.classList.remove('active');
            });
            document.getElementById(`table-${targetMethod}`).classList.add('active');

            // Toggle EPP overlay in video
            if (targetMethod === 'epp') {
                eppOverlay.classList.add('active');
            } else {
                eppOverlay.classList.remove('active');
            }
        });
    });

    // Toggle para brazo izquierdo/derecho en método Repetitivas
    const armToggles = document.querySelectorAll('.toggle-btn');
    armToggles.forEach(btn => {
        btn.addEventListener('click', (e) => {
            armToggles.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            // En un entorno real, esto actualizaría los datos mostrados debajo
        });
    });
});
