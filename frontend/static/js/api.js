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

  analizar(usuario, posts, refrescar) {
    const q = new URLSearchParams({ posts, refrescar });
    return this._get(`/api/analizar/${encodeURIComponent(usuario)}?${q}`);
  },
};
