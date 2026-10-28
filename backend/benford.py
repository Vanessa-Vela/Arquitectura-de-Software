"""Ley de Benford aplicada a la cifra de seguidores/seguidos de una muestra de cuentas.

Pasos (los mismos del enunciado):
  1. texto -> número            (texto_a_numero)
  2. aislar el primer dígito    (primer_digito)
  3. contar del 1 al 9          (analizar)
  4. chi-cuadrado contra Benford y diagnóstico
"""
import csv
import math
import re

DIGITOS = list(range(1, 10))
BENFORD = {d: math.log10(1 + 1 / d) for d in DIGITOS}   # 30.1 % para el 1 ... 4.6 % para el 9

GL = 8                    # 9 dígitos - 1
CRITICO_5 = 15.507        # chi-cuadrado con 8 gl, alfa = 0.05
CRITICO_1 = 20.090        # alfa = 0.01
MINIMO_VALIDOS = 30       # menos que esto no se diagnostica
MINIMO_RECOMENDADO = 110  # con menos, la frecuencia esperada del 9 baja de 5 y el chi² pierde fiabilidad
MUESTRA_PEDIDA = 200

_MULT = {"k": 1e3, "mil": 1e3, "m": 1e6, "mill": 1e6}


def texto_a_numero(texto):
    """'2,328' -> 2328 | '12.3K' -> 12300 | '12,3 mil' -> 12300 | '1.2M' -> 1200000.
    Devuelve None si no se entiende."""
    if texto is None:
        return None
    if isinstance(texto, (int, float)):
        return int(texto)
    m = re.match(r"\s*(\d[\d.,]*)\s*(mill|mil|k|m)?", str(texto).strip().lower())
    if not m:
        return None
    num, sufijo = m.groups()
    try:
        if sufijo:
            # con sufijo el separador es decimal: 12,3 mil / 12.3K
            num = num.replace(",", "") if ("," in num and "." in num) else num.replace(",", ".")
            valor = float(num) * _MULT[sufijo]
        else:
            # sin sufijo los separadores son de miles: 2,328 / 2.328
            valor = float(re.sub(r"[.,]", "", num))
    except ValueError:
        return None
    return int(round(valor))


def primer_digito(valor):
    """Primer dígito significativo: 2328 -> 2, 1000 -> 1, 10 -> 1. El 0 no cuenta (Benford va de 1 a 9)."""
    if valor is None or valor <= 0:
        return None
    return int(str(int(valor))[0])


def construir_tabla(registros):
    """Une cada usuario con su cifra y su primer dígito (la tabla del paso 4)."""
    tabla = []
    for r in registros:
        valor = texto_a_numero(r.get("valor_texto"))
        tabla.append({"usuario": r["usuario"], "valor_texto": r.get("valor_texto"),
                      "valor": valor, "primer_digito": primer_digito(valor)})
    return tabla


def chi_cuadrado(conteos):
    """Suma de (observado - esperado)^2 / esperado sobre los 9 dígitos."""
    n = sum(conteos)
    esperados = [n * BENFORD[d] for d in DIGITOS]
    chi2 = sum((o - e) ** 2 / e for o, e in zip(conteos, esperados))
    return chi2, esperados


def p_valor(chi2, gl=GL):
    """P(X >= chi2) para gl par, en forma cerrada (sin scipy)."""
    x = chi2 / 2
    return math.exp(-x) * sum(x ** j / math.factorial(j) for j in range(gl // 2))


def analizar(registros):
    tabla = construir_tabla(registros)
    digitos = [t["primer_digito"] for t in tabla if t["primer_digito"] is not None]
    n = len(digitos)
    conteos = [digitos.count(d) for d in DIGITOS]

    advertencias = [
        "El orden de la lista de Instagram no es aleatorio: la muestra son las primeras cuentas que cargaron.",
        "Benford es un indicio estadístico, no una prueba de que una cuenta sea falsa.",
    ]
    if len(tabla) < MUESTRA_PEDIDA:
        advertencias.insert(0, f"Se analizaron {n} cuentas con cifra válida; el enunciado pide al menos {MUESTRA_PEDIDA}.")
    if 0 < n < MINIMO_RECOMENDADO:
        advertencias.insert(0, "Muestra pequeña: algunas frecuencias esperadas son menores a 5 y el chi-cuadrado es poco fiable.")

    res = {"n_total": len(tabla), "n_validos": n, "n_excluidos": len(tabla) - n,
           "gl": GL, "valor_critico": CRITICO_5, "valor_critico_1": CRITICO_1,
           "advertencias": advertencias, "tabla": tabla}

    if n < MINIMO_VALIDOS:
        res.update(digitos=[], chi2=None, p_valor=None, ajusta=None,
                   veredicto="Muestra insuficiente para diagnosticar",
                   interpretacion=f"Se necesitan al menos {MINIMO_VALIDOS} cuentas con cifra válida y hay {n}.")
        return res

    chi2, esperados = chi_cuadrado(conteos)
    p = p_valor(chi2)
    ajusta = chi2 <= CRITICO_5

    if ajusta:
        veredicto = "Se ajusta a Benford: distribución natural → usuarios reales / humanos"
        interpretacion = (f"χ² = {chi2:.2f} es menor al valor crítico {CRITICO_5} (p = {p:.3f}): "
                          "no hay evidencia de que las cifras se aparten del comportamiento natural.")
    else:
        fuerte = chi2 > CRITICO_1
        veredicto = "Se desvía de Benford: distribución no natural → posibles cuentas falsas / bots"
        interpretacion = (f"χ² = {chi2:.2f} supera el valor crítico {CRITICO_5} (p = {p:.4f})"
                          + (f" e incluso el de 0.01 ({CRITICO_1}): desviación fuerte." if fuerte else ".")
                          + " Las cifras no siguen la distribución esperada.")

    res.update(
        digitos=[{"digito": d, "observado": conteos[i], "observado_pct": round(100 * conteos[i] / n, 2),
                  "esperado": round(esperados[i], 2), "esperado_pct": round(100 * BENFORD[d], 2)}
                 for i, d in enumerate(DIGITOS)],
        chi2=round(chi2, 3), p_valor=round(p, 5), ajusta=ajusta,
        veredicto=veredicto, interpretacion=interpretacion)
    return res


def guardar_csv(tabla, ruta):
    """CSV con usuario, cifra y primer dígito (utf-8-sig para que Excel lo abra bien)."""
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["usuario", "valor_texto", "valor", "primer_digito"])
        w.writeheader()
        w.writerows(tabla)
