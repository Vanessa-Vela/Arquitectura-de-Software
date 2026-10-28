// Gráfico radar del Big Five (Chart.js, copia local en static/js/vendor).
const Charts = {
  radar: null,

  dibujarRadar(rasgos) {
    const canvas = document.getElementById("radar");

    // Si la librería no cargó, el resto de los resultados se muestra igual.
    if (typeof Chart === "undefined") {
      canvas.style.display = "none";
      console.warn("Chart.js no está disponible: no se dibuja el radar.");
      return;
    }
    canvas.style.display = "";

    if (this.radar) this.radar.destroy();   // evita gráficos duplicados al reanalizar
    this.radar = new Chart(canvas, {
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