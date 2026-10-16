# Scraper de Instagram con Playwright

Script en Python que extrae datos y métricas de un perfil de Instagram usando **Playwright** y autenticación por **cookie de sesión (`sessionid`)**. El resultado se guarda en un archivo **JSON**.

> **Uso académico.** Instagram prohíbe el scraping automatizado en sus términos de uso. Usa una **cuenta secundaria**, extrae solo datos públicos y no abuses del número de ejecuciones.

---

## Objetivo

Automatizar la extracción de información de una cuenta de Instagram sin usar extensiones de navegador ni herramientas de terceros que ya tengan el scraping resuelto.

##  Datos que extrae

**Datos generales del perfil**

| Campo | Descripción |
|---|---|
| `nombre` | Nombre visible del perfil |
| `nombre_de_perfil` | Usuario (`@usuario`) |
| `seguidores` | Número de seguidores |
| `seguidos` | Número de cuentas que sigue |
| `total_publicaciones` | Total de publicaciones del perfil |
| `biografia` | Biografía del perfil |

**Publicaciones (entre 25 y 50)**

| Campo | Descripción |
|---|---|
| `codigo` | Identificador único de la publicación |
| `tipo` | `p` (publicación) o `reel` |
| `url` | Enlace directo |
| `descripcion` | Texto alternativo de la imagen |
| `imagen_url` | URL de la imagen |

---

## Requisitos

- Python **3.8 o superior**
- Librería **Playwright** (permitida por el enunciado)
- Una cuenta de Instagram (recomendado: secundaria) para obtener la cookie `sessionid`

##  Instalación

```bash
# 1. (Opcional) crear entorno virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

# 2. Instalar Playwright y el navegador
pip install playwright
playwright install chromium
```

##  Cómo obtener tu `sessionid`

1. Inicia sesión en [instagram.com](https://www.instagram.com) desde Chrome.
2. Pulsa **F12** → pestaña **Application** (Aplicación).
3. En el menú izquierdo: **Cookies** → `https://www.instagram.com`.
4. Busca la fila **`sessionid`** y copia su **Value**.

>  La cookie equivale a tu contraseña.
 Si se expone, cierra esa sesión desde *Configuración → Cuentas → Dónde iniciaste sesión*.

##  Configuración

Edita estas variables al inicio de `scraper_ig.py`:

```python
USUARIO = "usuario_a_scrapear"          # Perfil a scrapear (sin @)
SESSION_ID = "PEGA_AQUI_TU_SESSIONID"   # Cookie sessionid
CANTIDAD_POSTS = 50                     # Entre 25 y 50
ARCHIVO_SALIDA = "resultados.json"      # Archivo de salida
```

## ▶ Ejecución

```bash
python scraper_ig.py
```

Se abrirá Chromium, entrará al perfil, hará scroll solo y en la terminal verás:

```
 Entrando al perfil de @usuario...
    25 publicaciones encontradas
    40 publicaciones encontradas
   ...
Ralizado. 50 publicaciones guardadas en resultados.json
```

##  Ejemplo de salida (`resultados.json`)

```json
{
    "perfil": {
        "nombre": "Nombre Apellido",
        "nombre_de_perfil": "usuario",
        "seguidores": 1523,
        "seguidos": 210,
        "total_publicaciones": 87,
        "biografia": "Texto de la biografía"
    },
    "publicaciones": [
        {
            "codigo": "ABC123xyz",
            "tipo": "p",
            "url": "https://www.instagram.com/p/ABC123xyz/",
            "descripcion": "Texto alternativo de la imagen",
            "imagen_url": "https://..."
        }
    ]
}
```

---

##  Cómo funciona

```
1. Abre Chromium (visible) con Playwright
2. Inyecta la cookie sessionid  →  Instagram lo reconoce como sesión iniciada
3. Activa el interceptor de respuestas ANTES de navegar
4. Entra al perfil
5. Extrae los datos del perfil con dos métodos:
     ├── Método 2 (respaldo): metaetiquetas y cabecera
     └── Método 1: respuesta interna interceptada (datos exactos)
6. Hace scroll con pausas aleatorias y junta las publicaciones
7. Guarda todo en un archivo JSON
```

### Métodos para obtener los datos del perfil

| Método | Qué hace | Ventaja | Desventaja |
|---|---|---|---|
| **Método 1: API interna (interceptación)** | Intercepta la respuesta `web_profile_info` que la propia página ya descarga | Números exactos y biografía completa; no genera peticiones extra | No siempre ocurre |
| **Método 2: Metaetiquetas (respaldo)** | Lee las metaetiquetas Open Graph y el texto de la cabecera | Casi siempre disponible | Números abreviados (`1.2M`) y biografía aproximada |

El Método 2 llena los datos primero. Si el Método 1 capturó la respuesta, **sustituye** esos valores por los exactos.

### Estructura del código

| Pieza | Función |
|---|---|
| Configuración | Perfil, cookie, cantidad de posts y archivo de salida |
| `interceptar_respuesta_perfil` | Captura la respuesta interna de Instagram (Método 1) |
| `pausa` | Espera aleatoria de 2 a 4 segundos |
| `obtener_perfil` | Extrae los datos generales del perfil |
| `obtener_posts` | Scroll infinito y recolección de publicaciones sin repetir |
| `main` | Orquesta el flujo y guarda el JSON |

### Medidas para evitar bloqueos

- Navegador real y visible (no *headless*).
- Pausas y distancias de scroll aleatorias.
- No se hacen peticiones directas a la API: solo se lee lo que la página ya descarga.
- Máximo 50 publicaciones por ejecución.

---

## Posibles problemas

| Problema | Causa probable | Solución |
|---|---|---|
| Error `429` o aviso de "espera unos minutos" | Demasiadas peticiones | Espera 20–30 min, cambia de red y reduce las ejecuciones |
| Timeout esperando el `header` | Cookie inválida/expirada o perfil no cargó | Copia un `sessionid` nuevo |
| Instagram redirige al login | `sessionid` incorrecta o vencida | Vuelve a iniciar sesión y copia la cookie |
| Perfil privado | La cuenta de la cookie no lo sigue | Solo funciona si ya lo sigue |
| Seguidores con formato `1.2M` | Se usó el Método 2 | Es normal; el Método 1 trae el número exacto |
| El script dejó de funcionar | Instagram cambió su estructura | Ajustar selectores y patrones |

##  Limitaciones

- Depende de la estructura actual de Instagram, que puede cambiar sin aviso.
- No extrae likes ni comentarios, porque no aparecen en la cuadrícula del perfil (habría que abrir cada publicación, lo que aumenta el riesgo de bloqueo).
- No funciona con perfiles privados que la cuenta de la cookie no siga.

##  Mejoras futuras

- Guardar la cookie en un archivo `.env` en vez de dejarla en el código.
- Exportar también a CSV o Excel.
- Añadir likes y comentarios abriendo cada publicación con pausas largas.
- Reintentos automáticos y manejo de errores más detallado.

## Buenas prácticas de seguridad

- Nunca subir  `sessionid` a un repositorio. Si usas Git, agrega a `.gitignore`:
  ```
  .env
  resultados.json
  ```
- Usa una cuenta secundaria.
- Cierra la sesión de la cookie al terminar de probar.

## Licencia y aviso

Proyecto con fines **educativos**. El autor no se responsabiliza del uso indebido ni de las restricciones que Instagram pueda aplicar a la cuenta utilizada.
