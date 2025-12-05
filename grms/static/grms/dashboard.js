(function () {
    document.body.classList.add('grms-dashboard-page');

    const data = window.GRMS_DATA || {};

    const buildSurfaceChart = () => {
        if (!window.Chart) return;
        const canvas = document.getElementById('surfaceChart');
        if (!canvas) return;
        const surface = data.surface || {};
        new Chart(canvas, {
            type: 'pie',
            data: {
                labels: ['Asphalt/Paved', 'Gravel', 'Earth/Dirt'],
                datasets: [
                    {
                        data: [surface.asphalt || 0, surface.gravel || 0, surface.dirt || 0],
                        backgroundColor: ['#2563eb', '#10b981', '#f59e0b'],
                    },
                ],
            },
            options: {
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                },
            },
        });
    };

    const buildTrafficChart = () => {
        if (!window.Chart) return;
        const canvas = document.getElementById('trafficChart');
        if (!canvas) return;
        const years = data.traffic_years || [];
        const values = data.traffic_values || [];
        if (!years.length || !values.length) return;

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: years,
                datasets: [
                    {
                        data: values,
                        borderColor: '#2563eb',
                        backgroundColor: 'rgba(37, 99, 235, 0.12)',
                        fill: true,
                        tension: 0.35,
                    },
                ],
            },
            options: {
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { precision: 0 },
                    },
                },
            },
        });
    };

    const buildMap = () => {
        if (!window.L) return;
        const mapEl = document.getElementById('roadMap');
        if (!mapEl) return;

        const map = L.map(mapEl).setView([9.145, 40.489673], 6);
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 18,
            attribution: '&copy; OpenStreetMap contributors',
        }).addTo(map);

        const locations = data.road_locations || [];
        locations.forEach(({ lat, lon, name }) => {
            if (lat == null || lon == null) return;
            const marker = L.marker([lat, lon]).addTo(map);
            if (name) {
                marker.bindPopup(name);
            }
        });
    };

    document.addEventListener('DOMContentLoaded', () => {
        buildSurfaceChart();
        buildTrafficChart();
        buildMap();
    });
})();
