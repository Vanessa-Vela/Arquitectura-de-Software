"""Scraper de la lista de seguidores / seguidos de un perfil de Instagram.

Mismo enfoque que scraper_ig.py (Playwright + cookie del .env), pero en vez de leer
las publicaciones:
  1. entra al perfil y abre el popup de seguidores o seguidos,
  2. pasa el cursor por cada usuario de la lista y lee la tarjeta flotante (hover card),
  3. de la tarjeta saca la cifra de seguidores o seguidos de esa cuenta,
  4. hace scroll en el popup para ir cargando más usuarios hasta juntar la muestra.

Uso por consola:
  python scraper_seguidores.py usuario [followers|following] [followers|following] [muestra]
                                        lista a abrir          cifra a leer
"""
import os
import random
import re
import sys

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
SESSION_ID = os.getenv("IG_SESSIONID")

# Número seguido de la palabra: "2,328 followers", "12.3K followers", "12,3 mil seguidores"
NUMERO = r"(\d[\d.,]*(?:\s*(?:mill|mil|k|m))?)"
PATRON = {"followers": NUMERO + r"\s*(?:followers|seguidores)",
          "following": NUMERO + r"\s*(?:following|seguidos)"}
CLAVE_API = {"followers": "follower_count", "following": "following_count"}

# Usuarios (enlaces /usuario/) que se ven ahora mismo dentro del popup
JS_USUARIOS = r"""() => {
    const d = document.querySelector('div[role="dialog"]');
    if (!d) return [];
    const vistos = [];
    for (const a of d.querySelectorAll('a[href^="/"]')) {
        const m = a.getAttribute('href').match(/^\/([A-Za-z0-9._]+)\/$/);
        if (m && !vistos.includes(m[1])) vistos.push(m[1]);
    }
    return vistos;
}"""

# Busca la tarjeta flotante: el bloque de texto más corto que nombra al usuario
# y trae "<número> followers/following". Se ignora el encabezado del perfil.
JS_TARJETA = r"""([usuario, patron]) => {
    const rx = new RegExp(patron, 'i');
    const u = usuario.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const esUsuario = new RegExp('(^|[^a-z0-9._])' + u + '($|[^a-z0-9._])');
    let mejor = null;
    for (const el of document.querySelectorAll('div, section')) {
        if (el.closest('header')) continue;
        const t = el.innerText;
        if (!t || t.length > 600) continue;
        if (!esUsuario.test(t.toLowerCase()) || !rx.test(t)) continue;
        if (mejor === null || t.length < mejor.length) mejor = t;
    }
    return mejor;
}"""

# Baja el popup (el contenedor con scroll propio). Devuelve false si no lo encuentra.
JS_SCROLL = r"""() => {
    const d = document.querySelector('div[role="dialog"]');
    if (!d) return false;
    const sc = [d, ...d.querySelectorAll('div')].find(e =>
        e.scrollHeight > e.clientHeight + 20 && ['auto', 'scroll'].includes(getComputedStyle(e).overflowY));
    if (!sc) return false;
    sc.scrollTop = sc.scrollTop + sc.clientHeight * 0.9;
    return true;
}"""


def pausa(page, minimo=800, maximo=1600):
    # Pausa aleatoria (en milisegundos) para no ir a un ritmo de robot.
    page.wait_for_timeout(random.uniform(minimo, maximo))


def buscar_cuentas(obj, destino):
    # Respaldo: recorre un JSON y guarda cada diccionario con "username" y contadores.
    if isinstance(obj, dict):
        if "username" in obj and ("follower_count" in obj or "following_count" in obj):
            destino[str(obj["username"]).lower()] = obj
        for valor in obj.values():
            buscar_cuentas(valor, destino)
    elif isinstance(obj, list):
        for valor in obj:
            buscar_cuentas(valor, destino)


def escuchar_respuestas(response, capturados):
    # La tarjeta flotante suele pedir los datos de la cuenta a la API: se aprovechan esas respuestas.
    if "graphql" in response.url or "/api/v1/" in response.url:
        try:
            buscar_cuentas(response.json(), capturados)
        except Exception:
            pass


# Palabra que acompaña al número en el encabezado del perfil (inglés o español)
TEXTO_LISTA = {"followers": r"followers|seguidores", "following": r"following|seguidos"}


def abrir_lista(page, lista):
    # Click en "seguidores" o "seguidos" del encabezado del perfil -> aparece el popup.
    # Se prueban varias formas porque Instagram no siempre lo pone como enlace /followers/.
    palabra = TEXTO_LISTA[lista]
    encabezado = page.locator("header")
    candidatos = [
        page.locator(f'header a[href$="/{lista}/"]').first,    # enlace clásico
        encabezado.get_by_text(re.compile(r"\d[\d.,]*\s*(?:K|M|mil)?\s*(?:" + palabra + ")", re.I)).first,  # "2594 seguidores"
        encabezado.get_by_text(re.compile(palabra, re.I)).first,   # solo la palabra
    ]
    for candidato in candidatos:
        try:
            if candidato.count() == 0:
                continue
            candidato.click(timeout=5000)
            page.wait_for_selector('div[role="dialog"]', timeout=8000)
            pausa(page, 1500, 2500)
            return
        except Exception:
            continue

    page.screenshot(path="debug_seguidores.png")   # para ver qué estaba en pantalla
    raise RuntimeError("No se pudo abrir la lista de " + lista + ": no se encontró el botón o no apareció el popup. "
                                                                 "Revisa debug_seguidores.png.")

def leer_cifra(page, usuario, metrica, capturados):
    # Pasa el cursor por el usuario y lee la cifra de la tarjeta flotante.
    try:
        page.locator(f'div[role="dialog"] a[href="/{usuario}/"]').first.hover(timeout=4000)
    except Exception:
        return None

    texto = None
    for _ in range(6):                                    # espera hasta ~2 s a que aparezca la tarjeta
        page.wait_for_timeout(350)
        tarjeta = page.evaluate(JS_TARJETA, [usuario, PATRON[metrica]])
        m = re.search(PATRON[metrica], tarjeta, re.I) if tarjeta else None
        if m:
            texto = m.group(1).strip()
            break

    if texto is None:                                     # respaldo: lo que llegó por la red
        info = capturados.get(usuario.lower())
        if info and info.get(CLAVE_API[metrica]) is not None:
            texto = str(info[CLAVE_API[metrica]])

    page.mouse.move(5, 5)                                 # quita el cursor para cerrar la tarjeta
    return texto


def obtener_muestra(page, objetivo, metrica, muestra, capturados):
    registros = {}        # usuario -> texto de la cifra
    intentados = set()    # usuarios ya probados (con o sin éxito)
    sin_novedades = 0     # veces seguidas que el scroll no trajo usuarios nuevos

    while len(registros) < muestra and sin_novedades < 6:
        nuevos = [u for u in page.evaluate(JS_USUARIOS)
                  if u not in intentados and u.lower() != objetivo.lower()]

        for u in nuevos:
            if len(registros) >= muestra:
                break
            intentados.add(u)
            texto = leer_cifra(page, u, metrica, capturados)
            if texto:
                registros[u] = texto
            pausa(page)

            # si las primeras 10 cuentas no dan ninguna cifra, los selectores ya no sirven
            if len(intentados) >= 10 and not registros:
                raise RuntimeError("No se pudo leer la tarjeta flotante de ningún usuario: "
                                   "Instagram pudo cambiar su estructura.")
            if len(intentados) > muestra * 3:
                raise RuntimeError("Demasiados intentos sin completar la muestra.")

        print(f"  {len(registros)} cuentas con cifra ({len(intentados)} revisadas)")
        sin_novedades = 0 if nuevos else sin_novedades + 1

        if len(registros) < muestra:
            if not page.evaluate(JS_SCROLL):
                page.mouse.wheel(0, 900)
            pausa(page, 1500, 3000)

    return [{"usuario": u, "valor_texto": t} for u, t in registros.items()]


def scrapear_seguidores(usuario, lista="followers", metrica="followers", muestra=200, session_id=None):
    # Devuelve [{"usuario": ..., "valor_texto": "2,328"}, ...]
    sessionid = session_id or SESSION_ID
    if not sessionid:
        raise RuntimeError("Falta IG_SESSIONID en el archivo .env")
    if lista not in PATRON or metrica not in PATRON:
        raise ValueError("lista y metrica deben ser 'followers' o 'following'")

    capturados = {}
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=False)
        try:
            contexto = navegador.new_context(locale="en-US", viewport={"width": 1280, "height": 900})
            contexto.add_cookies([{"name": "sessionid", "value": sessionid,
                                   "domain": ".instagram.com", "path": "/",
                                   "secure": True, "httpOnly": True}])
            page = contexto.new_page()
            page.on("response", lambda r: escuchar_respuestas(r, capturados))

            print(f" Ingresando al perfil de @{usuario}...")
            page.goto(f"https://www.instagram.com/{usuario}/", wait_until="domcontentloaded")
            page.wait_for_selector("header", timeout=20000)
            pausa(page, 2000, 4000)

            print(f" Abriendo la lista de {lista}...")
            abrir_lista(page, lista)
            registros = obtener_muestra(page, usuario, metrica, muestra, capturados)
        finally:
            navegador.close()
    return registros


def main():
    if len(sys.argv) < 2:
        usuario = input("Usuario de Instagram: ")
    else:
        usuario = sys.argv[1]
    usuario = usuario.strip().lstrip("@")
    lista = sys.argv[2] if len(sys.argv) > 2 else "followers"
    metrica = sys.argv[3] if len(sys.argv) > 3 else "followers"
    muestra = int(sys.argv[4]) if len(sys.argv) > 4 else 200

    from backend import benford          # el análisis vive en backend/benford.py

    registros = scrapear_seguidores(usuario, lista, metrica, muestra)
    res = benford.analizar(registros)
    archivo = f"benford_{usuario}_{lista}_{metrica}.csv"
    benford.guardar_csv(res["tabla"], archivo)

    print(f"\n {len(registros)} cuentas guardadas en {archivo}")
    print(" Dígito  observado  esperado(Benford)")
    for d in res["digitos"]:
        print(f"   {d['digito']}      {d['observado_pct']:6.2f}%     {d['esperado_pct']:6.2f}%")
    if res["chi2"] is not None:
        print(f" chi-cuadrado = {res['chi2']}  (crítico {res['valor_critico']}, p = {res['p_valor']})")
    print(" Diagnóstico:", res["veredicto"])


if __name__ == "__main__":
    main()
