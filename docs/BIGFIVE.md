# Big Five desde Instagram

Estima los cinco rasgos de personalidad (OCEAN) de una cuenta pública de Instagram.
Usa el scraper del repo (`scraper_ig.py`, Playwright + cookie de sesión) y calcula el Big Five con la API de Gemini
(o con un análisis heurístico local si no hay API key).

## Estructura

```
├── scraper_ig.py      # scraper original (también se puede correr solo: python scraper_ig.py)
├── backend/
│   ├── app.py         # API FastAPI (rutas) y entrega del front
│   ├── config.py      # variables de entorno y constantes
│   ├── models.py      # esquemas Pydantic (Perfil, Publicacion, Rasgo, BigFive)
│   ├── scraper.py     # puente que llama a scraper_ig.scrapear()
│   └── analyzer.py    # cálculo del Big Five: Gemini + heurístico local
├── frontend/
│   ├── index.html
│   └── static/
│       ├── css/style.css
│       └── js/        # api.js (HTTP) · charts.js (radar) · app.js (pantalla)
├── data/              # JSON por usuario (no se sube a git)
├── docs/BIGFIVE.md    # este archivo
├── .env.example
├── requirements.txt
└── run.py
```

`scraper_ig.py` conserva su lógica (Método 1 y 2). Solo se agregó la función `scrapear()` que hace
el recorrido completo y devuelve `(perfil, posts)`; `main()` la usa y sigue generando `resultados.json`.

## Cómo correrlo

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
playwright install chromium
copy .env.example .env            # completar IG_SESSIONID y GEMINI_API_KEY
python run.py
```

Abrir http://127.0.0.1:8000

Si ya tienes un `resultados.json` del scraper, cópialo como `data/<usuario>.json`
(por ejemplo `data/alondra_cgp.json`) y se analiza sin volver a scrapear.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/health` | Estado, si hay Gemini y si hay cookie |
| GET | `/api/perfiles` | Usuarios guardados en `data/` |
| GET | `/api/analizar/{usuario}?posts=50&refrescar=false` | Scrapea (o usa lo guardado) y calcula el Big Five |

## Cómo se calcula

- **Gemini**: recibe biografía, métricas y descripciones; devuelve un puntaje 0-100 por rasgo con su evidencia.
- **Heurístico**: puntaje base 50 ajustado por señales del texto (léxicos de ideas, trabajo, afecto,
  conflicto y preocupación; emojis, exclamaciones, menciones, hashtags, longitud, diversidad léxica).
  Las fórmulas están en `backend/analyzer.py`.

## Uso responsable

Solo datos públicos. Es una estimación con fines académicos: una cuenta muestra la imagen que la
persona proyecta, no su personalidad completa, y no es un diagnóstico psicológico. No uses los
resultados para tomar decisiones sobre la persona analizada. La cookie `sessionid` equivale a tu
sesión: va en `.env` y nunca se sube al repositorio.
