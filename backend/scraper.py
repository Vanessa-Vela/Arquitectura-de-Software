"""Puente entre la API y el scraper original (scraper_ig.py, en la raíz del repo).

No duplica la lógica: llama a scraper_ig.scrapear(). Como ese módulo guarda su
estado en variables globales, se serializan las llamadas con un candado.
"""
import sys
import threading

from . import config

if str(config.BASE_DIR) not in sys.path:
    sys.path.insert(0, str(config.BASE_DIR))

_candado = threading.Lock()


def scrapear_perfil(usuario, cantidad=config.POSTS_POR_DEFECTO, sessionid=None):
    import scraper_ig   # import tardío: el resto de la API corre aunque Playwright no esté instalado

    with _candado:
        return scraper_ig.scrapear(usuario, cantidad, sessionid or config.IG_SESSIONID)
