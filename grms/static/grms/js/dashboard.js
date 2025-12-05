// Surface chart
const surfaceCtx = document.getElementById('surfaceChart');
const surfaceData = Array.isArray(window.surfaceData) ? window.surfaceData : [];
if (surfaceCtx && surfaceData.length) {
    new Chart(surfaceCtx, {
        type: 'pie',
        data: {
            labels: ['Asphalt', 'Gravel', 'Earth'],
            datasets: [{ data: surfaceData, backgroundColor: ['#3b82f6','#10b981','#f59e0b'] }]
        }
    });
}

// Traffic trend
const trafficCtx = document.getElementById('trafficChart');
const trafficYears = Array.isArray(window.trafficYears) ? window.trafficYears : [];
const trafficValues = Array.isArray(window.trafficValues) ? window.trafficValues : [];
if (trafficCtx && trafficYears.length && trafficValues.length) {
    new Chart(trafficCtx, {
        type: 'line',
        data: {
            labels: trafficYears,
            datasets: [{ label:'ADT', data:trafficValues, borderColor:'#0ea5e9' }]
        }
    });
}

// Leaflet map
if (document.getElementById('map') && window.L) {
    const map = L.map('map').setView([13.5, 39.5], 8);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
}
