# Ley de Benford en seguidores

Revisa si las cifras de seguidores (o seguidos) de una muestra de cuentas siguen la **ley de Benford**.
Si siguen la curva natural, se interpreta como usuarios reales; si se desvían, como posibles cuentas falsas o bots.

## La idea

En muchos conjuntos de números "naturales" el primer dígito no es uniforme: el 1 aparece cerca del 30 % de las veces
y el 9 cerca del 5 %. La probabilidad teórica es `P(d) = log10(1 + 1/d)`.

| Dígito | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| % esperado | 30.1 | 17.6 | 12.5 | 9.7 | 7.9 | 6.7 | 5.8 | 5.1 | 4.6 |

Cuentas generadas de forma artificial tienden a tener cifras que no siguen ese patrón.

## Flujo (los 7 pasos)

1. **Popup:** `scraper_seguidores.py` entra al perfil y hace clic en *followers* o *following* (parámetro `lista`).
2. **Hover:** pasa el cursor por cada usuario del popup, lee la tarjeta flotante y toma su cifra de seguidores o seguidos
   (parámetro `metrica`). Si la tarjeta no aparece, usa como respaldo las respuestas de la API que Instagram descarga.
3. **Scroll:** baja el popup para cargar más usuarios hasta juntar la muestra (por defecto 200).
4. **Tabla:** `backend/benford.py` une usuario, cifra y primer dígito y guarda un CSV en `data/benford/`.
5. **Primer dígito:** `2,328 → 2`, `4,352 → 4`, `1,000 → 1`, `10 → 1`. Los ceros se excluyen (Benford va de 1 a 9).
   Se entienden formatos como `12.3K`, `12,3 mil` y `1.2M`.
6. **Conteo y gráfico:** se cuenta cuántas veces sale cada dígito y se grafican las barras observadas con la curva de Benford encima.
7. **Chi-cuadrado y diagnóstico:**

   `χ² = Σ (observado − esperado)² / esperado`, con esperado = `n · log10(1 + 1/d)` y 8 grados de libertad.

   | Resultado | Diagnóstico |
   |---|---|
   | `χ² ≤ 15.507` (p ≥ 0.05) | Se ajusta a Benford → distribución natural → usuarios reales / humanos |
   | `χ² > 15.507` (p < 0.05) | Se desvía → posibles cuentas falsas / bots (desviación fuerte si `χ² > 20.09`) |
   | Menos de 30 cuentas válidas | Muestra insuficiente, no se diagnostica |

## Cómo usarlo

**Desde la página:** pestaña *Ley de Benford*, escribir el usuario, elegir la lista, la cifra y la muestra, y pulsar *Analizar*.
Con *Volver a scrapear* desmarcado se reutiliza lo guardado en `data/benford/` (solo se recalcula el análisis).

**Desde la consola:**
```
python scraper_seguidores.py usuario followers followers 200
```
Genera `benford_<usuario>_followers_followers.csv` e imprime la tabla de frecuencias, el χ² y el diagnóstico.

**API:** `GET /api/benford/{usuario}?lista=followers&metrica=followers&muestra=200&refrescar=false`
y `GET /api/benford/descargar/{archivo}.csv`.

## Archivos

| Archivo | Qué hace |
|---|---|
| `scraper_seguidores.py` | Popup, hover y scroll con Playwright (misma cookie del `.env`) |
| `backend/benford.py` | Conversión de texto a número, primer dígito, conteo, χ², p-valor, diagnóstico y CSV |
| `backend/scraper.py` | Puente: ahora también llama a `scrapear_seguidores` (con el mismo candado) |
| `backend/app.py` | Rutas `/api/benford/...` |
| `backend/models.py` | Modelos de la respuesta |
| `frontend/static/js/benford.js` | Pestaña, gráfico y tablas |

## Limitaciones

- **Un indicio, no una prueba.** Benford no demuestra que una cuenta sea falsa; el diagnóstico es sobre la muestra, no sobre cuentas individuales.
- **Muestra no aleatoria:** son las primeras cuentas que carga Instagram, no una selección al azar.
- **Tamaño:** con menos de unas 110 cuentas el χ² pierde fiabilidad (frecuencias esperadas menores a 5).
- **Benford no siempre aplica:** funciona mejor con cifras que abarcan varios órdenes de magnitud; si casi todas las cuentas tienen cifras parecidas, puede desviarse aunque sean personas reales.
- **Lento y dependiente de Instagram:** son muchas interacciones (unos minutos para 200 cuentas), y si Instagram cambia su estructura la lectura de la tarjeta flotante deja de funcionar. En ese caso el scraper se detiene con un mensaje claro.
- **Riesgo para la cuenta de la cookie:** pasar el cursor por cientos de cuentas genera muchas peticiones; conviene usar una cuenta secundaria.

## Datos y ética

Se guardan nombres de usuario y cifras de cuentas de terceros solo en `data/benford/` (fuera de git) y con fines académicos.
No se deben publicar ni usar para señalar a personas concretas como bots.
