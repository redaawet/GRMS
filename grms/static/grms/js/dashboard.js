// Sample chart code; replace data with actual values
document.addEventListener('DOMContentLoaded', function () {
  const surfaceCtx = document.getElementById('surfaceChart');
  if (surfaceCtx) {
    new Chart(surfaceCtx, {
      type: 'doughnut',
      data: {
        labels: ['Earth', 'Gravel', 'Paved'],
        datasets: [{
          data: [40, 35, 25], // example values
          backgroundColor: ['#4e73df', '#1cc88a', '#36b9cc'],
        }],
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
  if (trafficCtx) {
    new Chart(trafficCtx, {
      type: 'line',
      data: {
        labels: ['2019', '2020', '2021', '2022', '2023'],
        datasets: [{
          label: 'ADT',
          data: [1800, 1900, 2100, 2300, 2500],
          borderColor: '#4e73df',
          borderWidth: 2,
          fill: false,
        }],
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: false },
        },
      },
    });
  }
});
