# Voces de la app: guía rápida

Este zip tiene todo lo de la voz **Martin Osborne**, organizado en una sola carpeta.

| Qué | Para qué |
|---|---|
| `probar_voces.html` | Página para escuchar y probar todo |
| `biblioteca/` | Audios sueltos: vocales, sílabas, palabras, frases, preguntas y los renders de cada bloque |
| `lectura/` | Audios para **unir sílabas** y **armar oraciones** en cualquier orden, más `lector.js` (el código que los junta) |

## 1. Probar los audios

1. Abrí `probar_voces.html` con doble clic (Chrome, Edge, Safari o Firefox actualizados).
2. Tocá **Importar zip** y elegí **este mismo zip**. No hace falta descomprimirlo. Si ya lo descomprimiste, usá
   **Elegir carpeta descomprimida** y elegí la carpeta `voces_martin_osborne`.
3. Usá las pestañas:
   - **Letras y sílabas:** cada vocal y sílaba. La ficha con la letra en grande lee la familia (Ba, Be, Bi, Bo, Bu).
   - **Palabras y frases:** palabras, frases, preguntas, exclamaciones y los bloques completos.
   - **Escribir:** escribís lo que quieras y la app lo lee, de corrido o por sílabas. Abajo te muestra cómo resolvió
     cada palabra: **grabada**, **suena igual** (por ejemplo "baca" → "vaca") o **por sílabas** (no está grabada).
   - **Armar oración:** tocás palabras en cualquier orden y la app lee la oración que quedó.

En el celular, abrí la página publicada (el enlace que te pasé) y tocá **Importar zip** para elegir el zip
descargado.

## 2. Usarlos en tu app

Copiá las carpetas `biblioteca/` y `lectura/` a la carpeta de recursos de tu app (por ejemplo `assets/` o
`public/`). Los renders de `biblioteca/00_renders_bloques_completos/` son solo de referencia: no hace falta
copiarlos.

```js
// Un audio suelto: letra, sílaba o palabra
new Audio("biblioteca/02_silabas_directas/b/ba.wav").play();

// Unir sílabas y leer lo que arman los chicos
import { Lector } from "./lectura/lector.js";
const lector = await Lector.crear("lectura/");
await lector.leerSecuencia([["silabas", "vaca"], ["palabra", "vaca"],
                            ["silabas", "la vaca"], ["oracion", "la vaca come pasto"]]);
await lector.leerOracion("a la casa de mi tío hoy me voy de vacaciones");   // cualquier orden
```

**Si usás Antigravity,** podés pegarle esto:

> Copiá las carpetas `biblioteca/` y `lectura/` del zip a los recursos de la app. Para tocar una letra o una sílaba
> reproducí el archivo de `biblioteca/` (la ruta está en `biblioteca/manifest.json`). Para leer textos o unir
> sílabas usá `lectura/lector.js` (instrucciones en `lectura/README.md`). Si la app no es web, traducí la lógica de
> `lector.js`: buscar la palabra (igual, sin tildes o por sonido), usar la versión "final" para la última palabra y
> "medio" para las demás, unir con 10 ms de pausa y, si no existe, armarla por sílabas.

Hay más detalle en `biblioteca/README.md` y `lectura/README.md`.
