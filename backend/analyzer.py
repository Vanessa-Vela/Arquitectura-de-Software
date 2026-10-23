"""Cálculo del Big Five (OCEAN) a partir de los datos públicos de una cuenta.

Dos caminos:
  1. Gemini (si hay API key): recibe un resumen del perfil y devuelve puntajes con evidencia.
  2. Heurístico local: puntajes a partir de rasgos del texto (léxicos, emojis, menciones...).
     Se usa si no hay key o si la API falla.

Los puntajes son estimaciones, no un diagnóstico psicológico.
"""
import json
import re

from . import config

RASGOS = [
    ("apertura", "Apertura a la experiencia"),
    ("responsabilidad", "Responsabilidad"),
    ("extraversion", "Extraversión"),
    ("amabilidad", "Amabilidad"),
    ("neuroticismo", "Neuroticismo"),
]

LIMITACIONES = ("Estimación a partir de contenido público (biografía, descripciones y métricas). "
                "Una cuenta muestra la imagen que la persona decide proyectar, no su personalidad "
                "completa; no sustituye una evaluación psicológica.")

# ---- léxicos (prefijos de palabras en español) ----
LEX = {
    "cultura": ("conocimiento", "dato", "ciencia", "cient", "investig", "educa", "cultura", "arte",
                "libro", "idea", "innova", "tecnolog", "analis", "aprend", "polític", "social",
                "sociolog", "democrat", "digital"),
    "orden": ("trabajo", "responsab", "objetivo", "meta", "plan", "compromiso", "disciplin",
              "estrateg", "resultado", "proyecto", "program", "consult", "direct", "gestion"),
    "social": ("únete", "unete", "comparte", "ven ", "síguen", "siguen", "juntos", "equipo",
               "evento", "invit", "charla", "entrevista", "conversa", "comunidad", "nosotr"),
    "positivo": ("gracias", "agradec", "gratitud", "amor", "feliz", "felicid", "gozo", "alegr",
                 "bendic", "hermos", "orgull", "sonris", "abrazo", "familia", "cariño", "inspir"),
    "conflicto": ("contra", "mentira", "mienten", "corrup", "odio", "ataque", "violen", "culpa",
                  "enemig", "fraude", "escándalo", "escandalo"),
    "negativo": ("miedo", "preocup", "ansied", "peligro", "riesgo", "crisis", "triste", "dolor",
                 "amenaz", "angust", "estrés", "estres", "problema", "temor"),
}

EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def _nivel(p):
    return "Alto" if p > 60 else "Bajo" if p < 40 else "Medio"


def _clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))


def _norm(valor, ref):
    """Compara contra un valor típico: 0 -> -1, ref -> 0, 2*ref o más -> +1."""
    return min(valor / ref, 2) - 1 if ref else 0


# ---------------------------------------------------------------------
# Resumen de rasgos medibles del perfil
# ---------------------------------------------------------------------
def _contar(tokens, prefijos):
    return sum(1 for t in tokens if t.startswith(prefijos))


def calcular_rasgos_texto(perfil, posts):
    textos = [(p.get("descripcion") or "").strip() for p in posts]
    textos = [t for t in textos if t]
    bio = perfil.get("biografia") or ""
    todo = " ".join([bio] + textos)
    tokens = re.findall(r"[a-záéíóúñü]+", todo.lower())
    n_tokens = max(len(tokens), 1)
    n_posts = max(len(posts), 1)
    n_desc = max(len(textos), 1)
    letras = [c for c in todo if c.isalpha()]
    por100 = lambda clave: 100 * _contar(tokens, LEX[clave]) / n_tokens

    me_gusta = [p["me_gusta"] for p in posts if p.get("me_gusta") is not None]
    coment = [p["comentarios"] for p in posts if p.get("comentarios") is not None]

    return {
        "n_posts": len(posts),
        "con_descripcion": len(textos) / n_posts,
        "palabras_por_desc": len(tokens) / n_desc,
        "diversidad_lexica": len(set(tokens)) / n_tokens,
        "hashtags_por_post": todo.count("#") / n_posts,
        "menciones_por_post": todo.count("@") / n_posts,
        "emojis_por_post": len(EMOJI.findall(todo)) / n_posts,
        "exclamaciones_por_post": todo.count("!") / n_posts,
        "preguntas_por_post": todo.count("?") / n_posts,
        "suspensivos_por_post": todo.count("…") / n_posts + todo.count("...") / n_posts,
        "mayusculas": sum(c.isupper() for c in letras) / max(len(letras), 1),
        "reels": sum(1 for p in posts if p.get("tipo") == "reel") / n_posts,
        "prom_me_gusta": sum(me_gusta) / len(me_gusta) if me_gusta else None,
        "prom_comentarios": sum(coment) / len(coment) if coment else None,
        **{f"lex_{k}": por100(k) for k in LEX},
    }


# ---------------------------------------------------------------------
# Camino 2: heurístico local
# ---------------------------------------------------------------------
def analizar_heuristico(perfil, posts, nota=""):
    f = calcular_rasgos_texto(perfil, posts)

    o = 50 + 20 * _norm(f["lex_cultura"], 2.0) + 12 * _norm(f["diversidad_lexica"], 0.55) \
        + 8 * _norm(f["palabras_por_desc"], 25)
    c = 50 + 15 * _norm(f["lex_orden"], 1.0) + 10 * _norm(f["con_descripcion"], 0.9) \
        + 8 * _norm(f["hashtags_por_post"], 3) - 8 * _norm(f["mayusculas"], 0.08)
    e = 50 + 12 * _norm(f["emojis_por_post"], 2) + 10 * _norm(f["exclamaciones_por_post"], 1) \
        + 8 * _norm(f["menciones_por_post"], 1.5) + 12 * _norm(f["lex_social"], 1.0)
    a = 50 + 20 * _norm(f["lex_positivo"], 2.0) - 15 * _norm(f["lex_conflicto"], 1.0)
    n = 50 + 18 * _norm(f["lex_negativo"], 1.0) + 6 * _norm(f["preguntas_por_post"], 0.5) \
        + 6 * _norm(f["suspensivos_por_post"], 0.3) - 8 * _norm(f["lex_positivo"], 2.0)

    ev = {
        "apertura": f"{f['lex_cultura']:.1f} palabras de ideas/cultura/datos por cada 100; "
                    f"diversidad léxica {f['diversidad_lexica']:.2f}.",
        "responsabilidad": f"{f['lex_orden']:.1f} palabras de trabajo/planificación por cada 100; "
                           f"{f['con_descripcion']*100:.0f}% de publicaciones con descripción y "
                           f"{f['hashtags_por_post']:.1f} hashtags por publicación.",
        "extraversion": f"{f['emojis_por_post']:.1f} emojis, {f['exclamaciones_por_post']:.1f} exclamaciones "
                        f"y {f['menciones_por_post']:.1f} menciones por publicación.",
        "amabilidad": f"{f['lex_positivo']:.1f} palabras de afecto/gratitud frente a "
                      f"{f['lex_conflicto']:.1f} de conflicto por cada 100.",
        "neuroticismo": f"{f['lex_negativo']:.1f} palabras de preocupación/riesgo por cada 100; "
                        f"{f['preguntas_por_post']:.1f} preguntas por publicación.",
    }
    puntajes = {"apertura": o, "responsabilidad": c, "extraversion": e,
                "amabilidad": a, "neuroticismo": n}
    rasgos = []
    for clave, nombre in RASGOS:
        p = int(round(_clamp(puntajes[clave], 10, 90)))
        rasgos.append({"clave": clave, "nombre": nombre, "puntaje": p,
                       "nivel": _nivel(p), "evidencia": ev[clave]})

    top = sorted(rasgos, key=lambda r: abs(r["puntaje"] - 50), reverse=True)[:2]
    resumen = ("Análisis heurístico sobre " + str(f["n_posts"]) + " publicaciones. Los rasgos más "
               "marcados son " + " y ".join(f"{r['nombre'].lower()} ({r['nivel'].lower()})" for r in top) + ".")
    estilo = (f"{f['palabras_por_desc']:.0f} palabras por descripción, "
              f"{f['reels']*100:.0f}% de contenido en reels"
              + (f", promedio de {f['prom_me_gusta']:.0f} me gusta y {f['prom_comentarios']:.0f} comentarios."
                 if f["prom_me_gusta"] is not None else "."))
    fortalezas = [f"{r['nombre']} {r['nivel'].lower()}" for r in rasgos
                  if r["clave"] != "neuroticismo" and r["nivel"] == "Alto"] or ["Perfil equilibrado sin rasgos extremos"]
    return {"rasgos": rasgos, "resumen": resumen, "estilo_comunicacion": estilo,
            "fortalezas": fortalezas, "limitaciones": (nota + " " + LIMITACIONES).strip(),
            "metodo": "heuristico", "modelo": None}


# ---------------------------------------------------------------------
# Camino 1: Gemini
# ---------------------------------------------------------------------
PROMPT = """Eres un analista de texto que estima rasgos del modelo Big Five (OCEAN) a partir de contenido
público de una cuenta de Instagram. Es un ejercicio académico: no es un diagnóstico.

Reglas:
- Basa cada puntaje (0 a 100, 50 = promedio) en evidencia observable del texto o de las métricas y cítala
  brevemente en "evidencia".
- No des puntajes extremos (<15 o >85) sin evidencia clara. La cuenta puede reflejar una imagen pública
  cuidada; tenlo en cuenta.
- Neuroticismo alto = mayor reactividad emocional / preocupación; bajo = serenidad.
- Responde SOLO con JSON válido, en español, con exactamente esta forma:
{{"rasgos": [{{"clave": "apertura|responsabilidad|extraversion|amabilidad|neuroticismo",
   "puntaje": 0, "evidencia": "..."}}],
  "resumen": "...", "estilo_comunicacion": "...", "fortalezas": ["...", "..."]}}
Incluye los cinco rasgos, en ese orden.

DATOS DE LA CUENTA
Nombre: {nombre}
Biografía: {bio}
Seguidores: {seguidores} | Seguidos: {seguidos} | Publicaciones totales: {total}

MÉTRICAS CALCULADAS
{metricas}

DESCRIPCIONES DE LAS PUBLICACIONES (me gusta / comentarios entre corchetes)
{descripciones}
"""


def _limpiar_json(texto):
    texto = re.sub(r"^```(?:json)?|```$", "", texto.strip(), flags=re.M).strip()
    return json.loads(texto)


def analizar_gemini(perfil, posts):
    from google import genai
    from google.genai import types

    f = calcular_rasgos_texto(perfil, posts)
    metricas = "\n".join(f"- {k}: {round(v, 2) if isinstance(v, float) else v}"
                         for k, v in f.items() if v is not None and not k.startswith("lex_"))
    descripciones = "\n".join(
        f"{i+1}. [{p.get('me_gusta')}/{p.get('comentarios')}] {(p.get('descripcion') or '')[:280]}"
        for i, p in enumerate(posts[:40]) if p.get("descripcion"))
    prompt = PROMPT.format(nombre=perfil.get("nombre"), bio=perfil.get("biografia"),
                           seguidores=perfil.get("seguidores"), seguidos=perfil.get("seguidos"),
                           total=perfil.get("total_publicaciones"), metricas=metricas,
                           descripciones=descripciones or "(sin descripciones)")

    cliente = genai.Client(api_key=config.GEMINI_API_KEY)
    respuesta = cliente.models.generate_content(
        model=config.GEMINI_MODEL, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3))
    datos = _limpiar_json(respuesta.text)

    por_clave = {r["clave"]: r for r in datos["rasgos"]}
    rasgos = []
    for clave, nombre in RASGOS:
        r = por_clave[clave]
        p = int(round(_clamp(float(r["puntaje"]))))
        rasgos.append({"clave": clave, "nombre": nombre, "puntaje": p,
                       "nivel": _nivel(p), "evidencia": str(r.get("evidencia", ""))})
    return {"rasgos": rasgos, "resumen": datos.get("resumen", ""),
            "estilo_comunicacion": datos.get("estilo_comunicacion", ""),
            "fortalezas": [str(x) for x in datos.get("fortalezas", [])],
            "limitaciones": LIMITACIONES, "metodo": "gemini", "modelo": config.GEMINI_MODEL}


# ---------------------------------------------------------------------
def analizar(perfil, posts):
    if config.GEMINI_API_KEY:
        try:
            return analizar_gemini(perfil, posts)
        except Exception as e:
            nota = f"(Gemini no respondió: {type(e).__name__}; se usó el análisis local.)"
            return analizar_heuristico(perfil, posts, nota)
    return analizar_heuristico(perfil, posts, "(Sin GEMINI_API_KEY: análisis local.)")
