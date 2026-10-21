# Scraper de Instagram con Playwright

Script en Python que saca información de un perfil de Instagram y la guarda en un archivo JSON. Se hizo como trabajo de la materia de Arquitectura de Software, usando Playwright y la cookie de sesión (`sessionid`) para entrar a la cuenta.

Solo es para fines académicos. Instagram no permite el scraping automatizado en sus términos de uso, así que conviene usar una cuenta secundaria y no ejecutarlo muchas veces seguidas.

## Qué datos saca

Del perfil:

- nombre
- nombre de perfil (usuario)
- seguidores
- seguidos
- total de publicaciones
- biografía

De cada publicación (entre 25 y 50):

- código y tipo (publicación normal o reel)
- url de la publicación
- descripción
- me gusta
- comentarios
- url de la imagen

La `url` abre la publicación en Instagram y `imagen_url` es el enlace al archivo de la imagen. Ese enlace caduca con el tiempo, por eso a veces deja de abrir.

## Requisitos

- Python 3.8 o superior
- playwright
- python-dotenv
- Una cuenta de Instagram para sacar la cookie

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

El `requirements.txt` tiene solo dos líneas:

```
playwright
python-dotenv
```

## Cómo conseguir el sessionid

1. Iniciar sesión en instagram.com desde Chrome.
2. Abrir las herramientas de desarrollador con F12.
3. Ir a la pestaña Application y luego a Cookies, en `https://www.instagram.com`.
4. Copiar el valor de la fila `sessionid`.

Esa cookie funciona como una contraseña, así que no hay que compartirla ni subirla a GitHub.

## Configuración

La cookie se guarda en un archivo `.env` que no se sube al repositorio. Para crearlo:

```bash
copy .env.example .env
```

Luego se abre `.env` y se pega la cookie:

```
IG_SESSIONID=aqui_va_la_cookie
```

El usuario a analizar y la cantidad de publicaciones se cambian directamente en `scraper_ig.py`:

```python
USUARIO = "nombre_del_perfil"
CANTIDAD_POSTS = 50
```

## Uso

```bash
python scraper_ig.py
```

Se abre una ventana de Chromium, entra al perfil y va bajando sola. Al final se crea el archivo `resultados.json`. En la terminal se ve algo así:

```
 Ingresando al perfil de @usuario...
Datos del perfil con: Método 1 (capturado)
  12 publicaciones encontradas
  24 publicaciones encontradas
  ...
Publicaciones con métricas: 50 de 50
 Realizado. 50 publicaciones guardadas en resultados.json
```

## Ejemplo de resultado

```json
{
    "perfil": {
        "nombre": "Nombre Apellido",
        "nombre_de_perfil": "usuario",
        "seguidores": 2589,
        "seguidos": 2441,
        "total_publicaciones": 349,
        "biografia": "Texto de la biografía"
    },
    "publicaciones": [
        {
            "codigo": "ABC123xyz",
            "tipo": "reel",
            "url": "https://www.instagram.com/reel/ABC123xyz/",
            "descripcion": "Texto de la publicación",
            "me_gusta": 356,
            "comentarios": 4,
            "imagen_url": "https://..."
        }
    ]
}
```

## Cómo funciona

El script abre Chromium, le pone la cookie `sessionid` al navegador y entra al perfil. Antes de entrar activa una función que revisa todas las respuestas que Instagram descarga por su cuenta.

Para los datos del perfil se usan dos métodos:

1. **Método 1.** Entre esas respuestas hay unas de `graphql` que traen los datos del perfil. La función `buscar_usuario` recorre el JSON hasta encontrar el bloque que tiene la biografía y los seguidores. Con esto los números salen exactos y como enteros.
2. **Método 2.** Si lo anterior no funciona, se leen las metaetiquetas de la página (`og:title` y `og:description`) con expresiones regulares. Aquí los números pueden salir abreviados, como `12.3K`.

Primero se llenan los datos con el Método 2 y después, si el Método 1 consiguió algo, esos valores se reemplazan por los exactos.

Para las publicaciones se hace scroll hasta juntar la cantidad pedida, guardando cada una por su código para que no se repitan. Los me gusta y los comentarios no aparecen en la cuadrícula del perfil. En vez de abrir cada publicación (que son muchas peticiones y puede dar error 429), se aprovechan las mismas respuestas `graphql` que Instagram descarga al hacer scroll. La función `buscar_publicaciones` las va guardando y al final `agregar_metricas` completa cada publicación.

Entre acciones se usan pausas y distancias de scroll aleatorias para que no se vea tan seguido, y no se hacen peticiones directas a la API de Instagram.

## Problemas que pueden salir

- **Falta IG_SESSIONID:** no existe el archivo `.env` o está vacío.
- **Error 429 o aviso de esperar unos minutos:** Instagram limitó las peticiones. Hay que esperar un rato y cambiar de red.
- **Timeout o redirección al login:** la cookie venció o está mal copiada. Se copia una nueva.
- **Perfil privado:** solo funciona si la cuenta de la cookie ya lo sigue.
- **Sale "Método 2 (respaldo)":** no se capturó la respuesta de `graphql`. El script sigue funcionando, pero los números salen como texto.
- **"Publicaciones con métricas: 0":** Instagram cambió el nombre de los campos y hay que revisar la pestaña Network de las herramientas de desarrollador.

## Limitaciones

- Depende de cómo esté hecha la página de Instagram, y eso cambia sin avisar.
- No saca cuántas veces se compartió una publicación, porque Instagram no lo muestra públicamente.
- Si el dueño oculta los me gusta, ese dato queda en `null`.
- No funciona con perfiles privados que no se siguen.

## Seguridad

La cookie solo debe estar en el `.env`, que está en el `.gitignore`. Lo único que se sube es `.env.example`, que tiene un texto de relleno. El `.gitignore` incluye:

```
.venv/
.idea/
__pycache__/
.env
resultado*.json
debug.png
```