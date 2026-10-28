// Pestaña de la ley de Benford. Usa $ y el() de app.js (cargado antes) y Api de api.js.
const BenfordUI = {
  grafico: null,

  dibujarGrafico(digitos) {
    const canvas = $("grafico-benford");
    if (typeof Chart === "undefined") {          // si la librería no cargó, igual se ven las tablas
      canvas.style.display = "none";
      console.warn("Chart.js no está disponible: no se dibuja el gráfico.");
      return;
    }
    canvas.style.display = "";
    if (this.grafico) this.grafico.destroy();
    this.grafico = new Chart(canvas, {
      data: {
        labels: digitos.map(d => String(d.digito)),
        datasets: [
          { type: "bar", label: "Observado (%)", data: digitos.map(d => d.observado_pct),
            backgroundColor: "rgba(59, 91, 219, 0.55)" },
          { type: "line", label: "Benford (%)", data: digitos.map(d => d.esperado_pct),
            borderColor: "#e8590c", backgroundColor: "#e8590c", tension: 0.3, pointRadius: 4 },
        ],
      },
      options: {
        scales: {
          x: { title: { display: true, text: "Primer dígito" } },
          y: { beginAtZero: true, title: { display: true, text: "% de cuentas" } },
        },
      },
    });
  },

  pintarResumen(d) {
    const r = d.resultado;
    const caja = $("benford-resumen");
    caja.replaceChildren();
    caja.append(el("h2", `@${d.usuario}: lista de ${d.lista === "followers" ? "seguidores" : "seguidos"}, `
      + `cifra de ${d.metrica === "followers" ? "seguidores" : "seguidos"} de cada cuenta`));

    const stats = el("div", null, "stats");
    [["Cuentas con cifra válida", r.n_validos], ["Excluidas (cero o ilegible)", r.n_excluidos],
     ["χ²", r.chi2 ?? "-"], [`Valor crítico (gl = ${r.gl}, α = 0.05)`, r.valor_critico],
     ["p-valor", r.p_valor ?? "-"]].forEach(([etq, val]) => {
      const s = el("div", null, "stat");
      s.append(el("b", val), el("span", etq));
      stats.append(s);
    });
    caja.append(stats);

    const clase = r.ajusta === true ? "ok" : r.ajusta === false ? "alerta" : "neutro";
    caja.append(el("div", r.veredicto, "veredicto " + clase), el("p", r.interpretacion));
    const ul = el("ul", null, "advertencias");
    r.advertencias.forEach((a) => ul.append(el("li", a)));
    caja.append(ul);
    caja.append(el("p", d.origen === "cache" ? "Datos tomados de data/benford (sin scrapear)." : "Datos recién scrapeados.", "nota"));
  },

  pintarDigitos(digitos) {
    const cuerpo = $("benford-digitos");
    cuerpo.replaceChildren();
    digitos.forEach((x) => {
      const tr = document.createElement("tr");
      tr.append(el("td", x.digito), el("td", x.observado), el("td", x.observado_pct.toFixed(2) + " %"),
                el("td", x.esperado.toFixed(1)), el("td", x.esperado_pct.toFixed(2) + " %"));
      cuerpo.append(tr);
    });
  },

  pintarTabla(tabla, archivo) {
    const cuerpo = $("benford-tabla");
    cuerpo.replaceChildren();
    tabla.forEach((f) => {
      const tr = document.createElement("tr");
      tr.append(el("td", "@" + f.usuario), el("td", f.valor_texto ?? "-"),
                el("td", f.valor ?? "-"), el("td", f.primer_digito ?? "-"));
      cuerpo.append(tr);
    });
    const p = $("benford-descarga");
    p.replaceChildren();
    const a = document.createElement("a");
    a.href = "/api/benford/descargar/" + encodeURIComponent(archivo);
    a.textContent = "Descargar CSV (" + archivo + ")";
    p.append(a);
  },

  mostrar(d) {
    this.pintarResumen(d);
    this.dibujarGrafico(d.resultado.digitos);
    this.pintarDigitos(d.resultado.digitos);
    this.pintarTabla(d.resultado.tabla, d.archivo_csv);
    $("resultado-benford").hidden = false;
  },

  mensaje(texto, esError = false) {
    const m = $("mensaje-benford");
    m.hidden = !texto;
    m.textContent = texto || "";
    m.className = "mensaje" + (esError ? " error" : "");
  },

  async analizar() {
    const btn = $("btn-benford");
    btn.disabled = true;
    $("resultado-benford").hidden = true;
    this.mensaje($("b-refrescar").checked
      ? "Abriendo Instagram y leyendo cuenta por cuenta. Puede tardar varios minutos, no cierres la ventana de Chromium…"
      : "Analizando…");
    try {
      const d = await Api.benford($("b-usuario").value.trim().replace(/^@/, ""), $("b-lista").value,
                                  $("b-metrica").value, $("b-muestra").value, $("b-refrescar").checked);
      this.mensaje("");
      this.mostrar(d);
    } catch (e) {
      this.mensaje(e.message, true);
    } finally {
      btn.disabled = false;
    }
  },

  cambiarVista(vista) {
    const esBenford = vista === "benford";
    $("vista-bigfive").hidden = esBenford;
    $("vista-benford").hidden = !esBenford;
    $("tab-bigfive").classList.toggle("activa", !esBenford);
    $("tab-benford").classList.toggle("activa", esBenford);
  },
};

$("tab-bigfive").addEventListener("click", () => BenfordUI.cambiarVista("bigfive"));
$("tab-benford").addEventListener("click", () => BenfordUI.cambiarVista("benford"));
$("form-benford").addEventListener("submit", (ev) => { ev.preventDefault(); BenfordUI.analizar(); });
