import json
import random
import re
from playwright.sync_api import sync_playwright

#  CONFIGURACIÓN
USUARIO = "alondra_cgp"                  # Perfil a scrapear
SESSION_ID = ""  # cookie sessionid
CANTIDAD_POSTS = 50
ARCHIVO_SALIDA = "resultados.json"
# -----------------------------------------------
datos_api = {}  #  guarda la respuesta interna de Instagran (Metodo 1)
def escuchar_respuestas(response):
    # Metodo 1: captura la respuesta interna que Instagram ya descarga con los datos del perfil.
    if "web_profile_info" in response.url:
        try:
            datos_api["perfil"] = response.json()["data"]["user"]
        except Exception:
            pass
def pausa(page):
    # Espera entre 2 y 4 segundos, simulando a una persona.
    page.wait_for_timeout(random.uniform(2000, 4000))


def obtener_perfil(page):
    page.wait_for_selector("header", timeout=20000)
    pausa(page)

    perfil = {"nombre": None, "nombre_de_perfil": USUARIO, "seguidores": None,
              "seguidos": None, "total_publicaciones": None, "biografia": None}

    # Metodo 2 (respaldo): leer las etiquetas ocultas de la página
    titulo = page.locator('meta[property="og:title"]').get_attribute("content") or ""
    descripcion = page.locator('meta[property="og:description"]').get_attribute("content") or ""

    m = re.match(r"(.*?)\s*\(@", titulo)
    if m:
        perfil["nombre"] = m.group(1).strip() or None

    m = re.search(r"([\d.,KkMm]+)\s*(?:Followers|seguidores)\D+"
                  r"([\d.,KkMm]+)\s*(?:Following|seguidos)\D+"
                  r"([\d.,KkMm]+)\s*(?:Posts|publicaciones)", descripcion)
    if m:
        perfil["seguidores"], perfil["seguidos"], perfil["total_publicaciones"] = m.groups()

    # Biografía del perfil"
    bio, despues = [], False
    for linea in page.locator("header").inner_text().split("\n"):
        linea = linea.strip()
        if despues and linea and linea != perfil["nombre"]:
            bio.append(linea)
        if re.search(r"following|seguidos", linea.lower()):
            despues = True
    perfil["biografia"] = "\n".join(bio) or None

    # Metodo 1 : si se capturó la respuesta, esos datos exactos reemplazan a los del Metodo 2
    u = datos_api.get("perfil")
    if u:
        perfil["nombre"] = u.get("full_name") or perfil["nombre"]
        perfil["seguidores"] = u["edge_followed_by"]["count"]
        perfil["seguidos"] = u["edge_follow"]["count"]
        perfil["total_publicaciones"] = u["edge_owner_to_timeline_media"]["count"]
        perfil["biografia"] = u.get("biography")

    return perfil


def obtener_posts(page, cantidad):
    posts = {}          # código -> publicación (evita repetidas)
    sin_novedades = 0   # veces seguidas sin publicaciones nuevas

    while len(posts) < cantidad and sin_novedades < 5:
        enlaces = page.evaluate("""() =>
            [...document.querySelectorAll('main a[href*="/p/"], main a[href*="/reel/"]')]
            .map(a => ({
                href: a.getAttribute('href'),
                texto: a.querySelector('img')?.alt || '',
                imagen: a.querySelector('img')?.src || ''
            }))
        """)

        antes = len(posts)
        for e in enlaces:
            m = re.search(r"/(p|reel)/([^/?]+)", e["href"])
            if m and m.group(2) not in posts and len(posts) < cantidad:
                tipo, codigo = m.groups()
                posts[codigo] = {"codigo": codigo, "tipo": tipo,
                                 "url": f"https://www.instagram.com/{tipo}/{codigo}/",
                                 "descripcion": e["texto"], "imagen_url": e["imagen"]}

        sin_novedades = sin_novedades + 1 if len(posts) == antes else 0
        print(f"  {len(posts)} publicaciones encontradas")

        page.mouse.wheel(0, random.randint(1500, 2500))  # bajar la página
        pausa(page)
    return list(posts.values())


def main():
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=False)
        contexto = navegador.new_context(locale="en-US", viewport={"width": 1280, "height": 900})
        contexto.add_cookies([{"name": "sessionid", "value": SESSION_ID,
                               "domain": ".instagram.com", "path": "/",
                               "secure": True, "httpOnly": True}])

        page = contexto.new_page()
        page.on("response", escuchar_respuestas)  # Activar la captura de datos ANTES de entrar

        print(f" Igresando al perfil de @{USUARIO}...")
        page.goto(f"https://www.instagram.com/{USUARIO}/", wait_until="domcontentloaded")

        perfil = obtener_perfil(page)
        posts = obtener_posts(page, CANTIDAD_POSTS)

        with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
            json.dump({"perfil": perfil, "publicaciones": posts}, f, ensure_ascii=False, indent=4)

        print(f" Realizado . {len(posts)} publicaciones guardadas en {ARCHIVO_SALIDA}")
        navegador.close()


if __name__ == "__main__":
    main()