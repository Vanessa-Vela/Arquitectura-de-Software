// Gráfico radar del Big Five (Chart.js).
const Charts = {
  radar: null,

  dibujarRadar(rasgos) {
    if (this.radar) this.radar.destroy();   // evita gráficos duplicados al reanalizar
    this.radar = new Chart(document.getElementById("radar"), {
      type: "radar",
      data: {
        labels: rasgos.map(r => r.nombre),
        datasets: [{
          label: "Puntaje (0-100)",
          data: rasgos.map(r => r.puntaje),
          backgroundColor: "rgba(59, 91, 219, 0.2)",
          borderColor: "#3b5bdb",
          pointBackgroundColor: "#3b5bdb",
        }],
      },
      options: {
        scales: { r: { min: 0, max: 100, ticks: { stepSize: 20 } } },
        plugins: { legend: { display: false } },
      },
    });
  },
};
