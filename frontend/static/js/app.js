// Controlador de la página: lee el formulario, llama a la API y pinta el resultado.
const $ = (id) => document.getElementById(id);

function el(tag, texto, clase) {
  // textContent (no innerHTML) para no inyectar HTML de las descripciones
  const nodo = document.createElement(tag);
  if (texto !== undefined && texto !== null) nodo.textContent = texto;
  if (clase) nodo.className = clase;
  return nodo;
}

function mostrarMensaje(texto, esError = false) {
  const m = $("mensaje");
  m.hidden = !texto;
  m.textContent = texto || "";
  m.className = "mensaje" + (esError ? " error" : "");
}

function pintarPerfil(p, origen) {
  const caja = $("perfil");
  caja.replaceChildren();
  const cab = el("div", null, "perfil-cab");
  const titulo = el("h2", `${p.nombre || p.nombre_de_perfil} (@${p.nombre_de_perfil})`);
  cab.append(titulo);
  [["Seguidores", p.seguidores], ["Seguidos", p.seguidos], ["Publicaciones", p.total_publicaciones]]
    .forEach(([etq, val]) => {
      const s = el("div", null, "stat");
      s.append(el("b", val ?? "-"), el("span", etq));
      cab.append(s);
    });
  caja.append(cab);
  if (p.biografia) caja.append(el("p", p.biografia));
  caja.append(el("p", origen === "cache" ? "Datos tomados de /data (sin scrapear)." : "Datos recién scrapeados.", "nota"));
}

function pintarRasgos(rasgos) {
  const cont = $("rasgos");
  cont.replaceChildren();
  rasgos.forEach((r) => {
    const fila = el("div", null, "rasgo");
    const cab = el("div", null, "rasgo-cab");
    cab.append(el("span", r.nombre), el("b", `${r.puntaje} · ${r.nivel}`));
    const barra = el("div", null, "barra");
    const relleno = document.createElement("i");
    relleno.style.width = r.puntaje + "%";
    barra.append(relleno);
    fila.append(cab, barra, el("small", r.evidencia));
    cont.append(fila);
  });
}

function pintarPosts(posts) {
  const cuerpo = $("tabla-posts");
  cuerpo.replaceChildren();
  posts.forEach((p) => {
    const tr = document.createElement("tr");
    const desc = el("td", (p.descripcion || "").slice(0, 160), "desc");
    const enlace = document.createElement("a");
    enlace.href = p.url; enlace.target = "_blank"; enlace.rel = "noopener";
    enlace.textContent = p.tipo;
    const tdTipo = document.createElement("td");
    tdTipo.append(enlace);
    tr.append(tdTipo, desc, el("td", p.me_gusta ?? "-"), el("td", p.comentarios ?? "-"));
    cuerpo.append(tr);
  });
}

function pintarResultado(d) {
  const b = d.bigfive;
  pintarPerfil(d.perfil, d.origen);
  Charts.dibujarRadar(b.rasgos);
  pintarRasgos(b.rasgos);
  $("resumen").textContent = b.resumen;
  $("estilo").textContent = b.estilo_comunicacion;
  const ul = $("fortalezas");
  ul.replaceChildren(...b.fortalezas.map((f) => el("li", f)));
  $("limitaciones").textContent = b.limitaciones;
  $("metodo").textContent = b.metodo === "gemini" ? `Análisis con IA (${b.modelo}).` : "Análisis heurístico local.";
  pintarPosts(d.publicaciones);
  $("resultado").hidden = false;
}

async function analizar(usuario) {
  const btn = $("btn-analizar");
  btn.disabled = true;
  $("resultado").hidden = true;
  mostrarMensaje($("refrescar").checked || !guardados.includes(usuario.toLowerCase())
    ? "Scrapeando el perfil, puede tardar uno o dos minutos…" : "Analizando…");
  try {
    const datos = await Api.analizar(usuario, $("posts").value, $("refrescar").checked);
    mostrarMensaje("");
    pintarResultado(datos);
    cargarGuardados();
  } catch (e) {
    mostrarMensaje(e.message, true);
  } finally {
    btn.disabled = false;
  }
}

let guardados = [];

async function cargarGuardados() {
  try {
    guardados = await Api.perfilesGuardados();
  } catch { guardados = []; }
  const p = $("guardados");
  p.replaceChildren();
  if (!guardados.length) return;
  p.append("Guardados: ");
  guardados.forEach((u) => {
    const a = el("a", "@" + u);
    a.onclick = () => { $("usuario").value = u; $("refrescar").checked = false; analizar(u); };
    p.append(a);
  });
}

async function init() {
  try {
    const h = await Api.health();
    $("estado-servicio").textContent =
      (h.gemini ? `IA: Gemini (${h.modelo}). ` : "Sin API key de Gemini: se usa el análisis local. ") +
      (h.cookie_instagram ? "Cookie de Instagram configurada." : "Falta IG_SESSIONID: solo se pueden analizar perfiles guardados.");
  } catch { $("estado-servicio").textContent = "No se pudo contactar al servidor."; }
  cargarGuardados();
}

$("form-analisis").addEventListener("submit", (ev) => {
  ev.preventDefault();
  analizar($("usuario").value.trim().replace(/^@/, ""));
});

init();
