import asyncio
import json
import re
import sys

from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config
from . import benford
from .analyzer import analizar
from .models import Analisis, RespuestaBenford
from .scraper import scrapear_perfil, scrapear_seguidores

# Playwright en Windows necesita el loop Proactor
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(title="Big Five desde Instagram")
app.mount("/static", StaticFiles(directory=config.FRONTEND_DIR / "static"), name="static")

USUARIO_VALIDO = re.compile(r"^[A-Za-z0-9._]{1,30}$")
BENFORD_DIR = config.DATA_DIR / "benford"
BENFORD_DIR.mkdir(exist_ok=True)

def _archivo(usuario):
    if not USUARIO_VALIDO.match(usuario):
        raise HTTPException(400, "Nombre de usuario inválido")
    return config.DATA_DIR / f"{usuario.lower()}.json"


@app.get("/")
def inicio():
    return FileResponse(config.FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health():
    return {"estado": "ok",
            "gemini": bool(config.GEMINI_API_KEY),
            "modelo": config.GEMINI_MODEL,
            "cookie_instagram": bool(config.IG_SESSIONID)}


@app.get("/api/perfiles")
def perfiles_guardados():
    """Usuarios que ya tienen datos en /data (se pueden analizar sin volver a scrapear)."""
    return sorted(a.stem for a in config.DATA_DIR.glob("*.json"))


# Es 'def' (no 'async def') a propósito: FastAPI lo corre en un hilo aparte y
# así Playwright (API síncrona) no choca con el loop de asyncio.
@app.get("/api/analizar/{usuario}", response_model=Analisis)
def analizar_usuario(usuario: str,
                     posts: int = Query(config.POSTS_POR_DEFECTO, ge=1, le=config.POSTS_MAXIMO),
                     refrescar: bool = False):
    archivo = _archivo(usuario)

    if archivo.exists() and not refrescar:
        try:
            datos = json.loads(archivo.read_text(encoding="utf-8"))
            perfil, publicaciones, origen = datos["perfil"], datos["publicaciones"], "cache"
        except (ValueError, KeyError):
            raise HTTPException(422, f"El archivo data/{archivo.name} está dañado o no tiene el formato "
                                     "{perfil, publicaciones}. Márcalo 'Volver a scrapear' o bórralo.")
    else:
        try:
            perfil, publicaciones = scrapear_perfil(usuario, posts)
        except RuntimeError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(502, f"No se pudo scrapear @{usuario}: {e}")
        origen = "scraping"

    bigfive = analizar(perfil, publicaciones)

    archivo.write_text(json.dumps({"perfil": perfil, "publicaciones": publicaciones, "bigfive": bigfive},
                                  ensure_ascii=False, indent=4), encoding="utf-8")
    return {"perfil": perfil, "publicaciones": publicaciones, "bigfive": bigfive, "origen": origen}




@app.get("/api/benford/{usuario}", response_model=RespuestaBenford)
def analizar_benford(usuario: str,
                     lista: Literal["followers", "following"] = "followers",
                     metrica: Literal["followers", "following"] = "followers",
                     muestra: int = Query(benford.MUESTRA_PEDIDA, ge=30, le=500),
                     refrescar: bool = False):
    """Abre el popup de seguidores/seguidos, lee la cifra de cada cuenta y aplica la ley de Benford."""
    _archivo(usuario)   # solo valida el nombre de usuario
    nombre = f"{usuario.lower()}_{lista}_{metrica}"   # sin with_suffix: los usuarios pueden llevar puntos
    ruta_json = BENFORD_DIR / f"{nombre}.json"

    if ruta_json.exists() and not refrescar:
        try:
            registros = json.loads(ruta_json.read_text(encoding="utf-8"))["registros"]
            origen = "cache"
        except (ValueError, KeyError):
            raise HTTPException(422, f"El archivo data/benford/{ruta_json.name} está dañado. "
                                     "Márcalo 'Volver a scrapear' o bórralo.")
    else:
        try:
            registros = scrapear_seguidores(usuario, lista, metrica, muestra)
        except RuntimeError as e:
            raise HTTPException(400, str(e))
        except Exception as e:
            raise HTTPException(502, f"No se pudo leer la lista de @{usuario}: {e}")
        origen = "scraping"

    resultado = benford.analizar(registros)
    benford.guardar_csv(resultado["tabla"], BENFORD_DIR / f"{nombre}.csv")
    ruta_json.write_text(json.dumps({"registros": registros}, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"usuario": usuario, "lista": lista, "metrica": metrica, "origen": origen,
            "archivo_csv": f"{nombre}.csv", "resultado": resultado}


@app.get("/api/benford/descargar/{nombre}")
def descargar_csv(nombre: str):
    if not re.match(r"^[A-Za-z0-9._]+\.csv$", nombre) or ".." in nombre:
        raise HTTPException(400, "Nombre de archivo inválido")
    ruta = BENFORD_DIR / nombre
    if not ruta.exists():
        raise HTTPException(404, "Ese CSV no existe")
    return FileResponse(ruta, media_type="text/csv", filename=nombre)