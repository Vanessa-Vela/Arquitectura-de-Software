import json
import random
import re       #Expresiones regulares,
from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

#  CONFIGURACIÓN
USUARIO = "alondra_cgp"                  # Perfil a scrapear
load_dotenv()                           # lee el archivo .env
SESSION_ID = os.getenv("IG_SESSIONID")  # la cookie viene del .env, no del código
if not SESSION_ID:
    raise SystemExit("Falta IG_SESSIONID en el archivo .env")
CANTIDAD_POSTS = 50
ARCHIVO_SALIDA = "resultados.json"
# -----------------------------------------------
datos_api = {}  # Guarda la respuesta interna de Instagram (Metodo 1)
datos_posts = {}   # Guarda los datos de cada publicación: datos (me gusta, comentarios)

def buscar_usuario(obj):
    # Recorre el JSON (diccionarios y listas) y devuelve el diccionario
    # que tenga a la vez la biografía y los seguidores.
    if isinstance(obj, dict):
        if "biography" in obj and "follower_count" in obj:
            return obj
        for valor in obj.values():
            r = buscar_usuario(valor)
            if r:
                return r
    elif isinstance(obj, list):
        for valor in obj:
            r = buscar_usuario(valor)
            if r:
                return r
    return None


def buscar_publicaciones(obj):
    # Recorre el JSON y guarda en datos_posts cada publicación que encuentre.
    # Una publicación es un diccionario que tiene "code" y me gusta o comentarios.
    if isinstance(obj, dict):
        if "code" in obj and ("like_count" in obj or "comment_count" in obj):
            datos_posts[obj["code"]] = obj
        for valor in obj.values():
            buscar_publicaciones(valor)
    elif isinstance(obj, list):
        for valor in obj:
            buscar_publicaciones(valor)


def escuchar_respuestas(response):
    # Metodo 1: captura las respuestas graphql que Instagram ya descarga.
    # De ellas saca los datos del perfil y los datos de las publicaciones.
    if "graphql" in response.url:
        try:
            datos = response.json()
            usuario = buscar_usuario(datos)
            # Solo guardamos si es el perfil que buscamos (no cuentas sugeridas)
            if usuario and usuario.get("username", USUARIO) == USUARIO:
                datos_api["perfil"] = usuario
            buscar_publicaciones(datos)
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

     # Acepta inglés y español, y sufijos K, M o "mil" (ej: 12.3K o 12,3 mil)
    m = re.search(r"([\d.,]+(?:\s*(?:K|M|mil))?)\s*(?:Followers|seguidores)\D+"
                  r"([\d.,]+(?:\s*(?:K|M|mil))?)\s*(?:Following|seguidos)\D+"
                  r"([\d.,]+(?:\s*(?:K|M|mil))?)\s*(?:Posts|publicaciones)",
                  descripcion, re.I)
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
        perfil["seguidores"] = u.get("follower_count", perfil["seguidores"])
        perfil["seguidos"] = u.get("following_count", perfil["seguidos"])
        perfil["total_publicaciones"] = u.get("media_count", perfil["total_publicaciones"])
        perfil["biografia"] = u.get("biography") or perfil["biografia"]

    return perfil


def agregar_metricas(lista_posts):
    # Completa cada publicación con los datos capturados de las respuestas graphql.
    # Si de alguna publicación no se capturó nada, sus métricas quedan en None.
    for p in lista_posts:
        info = datos_posts.get(p["codigo"])
        if info:
            caption = info.get("caption")
            texto = caption.get("text") if isinstance(caption, dict) else caption
            p["descripcion"] = texto or p["descripcion"]
            p["me_gusta"] = info.get("like_count")
            p["comentarios"] = info.get("comment_count")


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
                                 "descripcion": e["texto"],
                                 "me_gusta": None, "comentarios": None,
                                 "imagen_url": e["imagen"] or None}   # None si no tiene imagen

        sin_novedades = sin_novedades + 1 if len(posts) == antes else 0
        print(f"  {len(posts)} publicaciones encontradas")

        page.mouse.wheel(0, random.randint(1500, 2500))  # bajar la página
        pausa(page)

    lista = list(posts.values())
    agregar_metricas(lista)   # al final, cuando ya se capturaron todas las respuestas
    return lista


def main():
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=False)
        contexto = navegador.new_context(locale="en-US", viewport={"width": 1280, "height": 900})
        contexto.add_cookies([{"name": "sessionid", "value": SESSION_ID,
                               "domain": ".instagram.com", "path": "/",
                               "secure": True, "httpOnly": True}])

        page = contexto.new_page()
        page.on("response", escuchar_respuestas)  # Activar la captura de datos ANTES de entrar

        print(f" Ingresando al perfil de @{USUARIO}...")
        page.goto(f"https://www.instagram.com/{USUARIO}/", wait_until="domcontentloaded")

        perfil = obtener_perfil(page)
        print("Datos del perfil con:", "Método 1 (capturado)" if datos_api.get("perfil") else "Método 2 (respaldo)")
        posts = obtener_posts(page, CANTIDAD_POSTS)

        con_metricas = sum(1 for p in posts if p["me_gusta"] is not None)
        print(f"Publicaciones con métricas: {con_metricas} de {len(posts)}")

        with open(ARCHIVO_SALIDA, "w", encoding="utf-8") as f:
            json.dump({"perfil": perfil, "publicaciones": posts}, f, ensure_ascii=False, indent=4)

        print(f" Realizado . {len(posts)} publicaciones guardadas en {ARCHIVO_SALIDA}")
        navegador.close()


if __name__ == "__main__":
    main()