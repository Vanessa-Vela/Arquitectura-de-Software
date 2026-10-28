// Cliente HTTP: único lugar donde el front habla con el backend.
const Api = {
  async _get(url) {
    const r = await fetch(url);
    const datos = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(datos.detail || `Error ${r.status}`);
    return datos;
  },

  health() { return this._get("/api/health"); },
  perfilesGuardados() { return this._get("/api/perfiles"); },

  benford(usuario, lista, metrica, muestra, refrescar) {
    const q = new URLSearchParams({ lista, metrica, muestra, refrescar });
    return this._get(`/api/benford/${encodeURIComponent(usuario)}?${q}`);
  },

  analizar(usuario, posts, refrescar) {
    const q = new URLSearchParams({ posts, refrescar });
    return this._get(`/api/analizar/${encodeURIComponent(usuario)}?${q}`);
  },
};

