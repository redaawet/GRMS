document.addEventListener('DOMContentLoaded', function () {
  const dataScript = document.getElementById('grms-data');
  const payload = dataScript ? JSON.parse(dataScript.textContent) : {};

  const surfaceTotals = payload.surface || {};
  const surfaceData = [
    Number(surfaceTotals.asphalt || 0),
    Number(surfaceTotals.gravel || 0),
    Number(surfaceTotals.dirt || 0),
  ];

  const trafficYears = payload.traffic_years || [];
  const trafficValues = payload.traffic_values || [];

  const surfaceCtx = document.getElementById('surfaceChart');
  if (surfaceCtx && surfaceData.some((value) => value > 0)) {
    new Chart(surfaceCtx, {
      type: 'doughnut',
      data: {
        labels: ['Paved / Asphalt', 'Gravel', 'Earth'],
        datasets: [
          {
            data: surfaceData,
            backgroundColor: ['#2563eb', '#16a34a', '#f59e0b'],
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: { position: 'bottom' },
        },
      },
    });
  }

  const trafficCtx = document.getElementById('trafficChart');
  if (trafficCtx && trafficYears.length && trafficValues.length) {
    new Chart(trafficCtx, {
      type: 'line',
      data: {
        labels: trafficYears,
        datasets: [
          {
            label: 'ADT',
            data: trafficValues,
            borderColor: '#2563eb',
            backgroundColor: '#2563eb',
            borderWidth: 2,
            fill: false,
            tension: 0.25,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: false },
        },
      },
    });
  }

  const mapEl = document.getElementById('roadMap');
  const roadLocations = payload.road_locations || [];
  if (mapEl && typeof L !== 'undefined') {
    const defaultCenter = [9.145, 40.489];
    const map = L.map(mapEl).setView(defaultCenter, 6);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    if (roadLocations.length) {
      const markers = roadLocations.map((item) => {
        const marker = L.marker([item.lat, item.lon]).bindPopup(item.name || 'Road');
        marker.addTo(map);
        return marker;
      });

      const group = L.featureGroup(markers);
      map.fitBounds(group.getBounds().pad(0.2));
    } else {
      const empty = document.createElement('div');
      empty.className = 'panel-empty';
      empty.textContent = 'Add coordinates to roads to see them on the map.';
      mapEl.appendChild(empty);
    }
  }
});
