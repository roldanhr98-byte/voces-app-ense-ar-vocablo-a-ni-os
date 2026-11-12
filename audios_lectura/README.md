# Lectura encadenada: unir sílabas y armar oraciones

Este paquete sirve para dos secciones de la app:

1. **Unir sílabas:** "va - ca" → "vaca" → "la - va - ca" → "la vaca come pasto".
2. **Armar oraciones:** el chico ordena palabras como quiera y la app lee lo que armó, fluido y sin cortes de robot.

No hay frases grabadas. Hay **palabras sueltas preparadas para encadenarse** y **sílabas**. El archivo `lector.js` las
junta en el momento, en cualquier orden.

- **Voz:** Martin Osborne – Deep and Passionate (ElevenLabs, `eleven_multilingual_v2`).
- **Formato:** WAV 48 kHz, mono, 16 bits.

## Probar

- **`ejemplos/`:** oraciones ya armadas por el lector. Escuchalas directamente.
- **`probar.html`:** tocás palabras, las mezclás o escribís lo que quieras, y la escuchás. Para que funcione, abrí
  una terminal en esta carpeta, ejecutá `python3 -m http.server` y entrá a `http://localhost:8000/probar.html`.

## Qué hay adentro

| Carpeta / archivo | Qué es |
|---|---|
| `palabras/medio/` | 165 palabras con entonación de **mitad de oración**: cortas y sin caída final |
| `palabras/final/` | 131 palabras con entonación de **cierre de oración** (las palabras chicas como "de" o "la" no la necesitan) |
| `silabas/` | 254 sílabas (vocales, directas, inversas, grupos, combinaciones) tomadas de la biblioteca anterior, recortadas para unirse |
| `ejemplos/` | Ejemplos armados con el lector |
| `manifest_lectura.json` | Índice: palabra → archivos, sílaba → archivo, y los parámetros de empalme |
| `lector.js` | El lector para la app (JavaScript, Web Audio) |
| `probar.html` | Página de prueba |

## Cómo se logró que suene fluido

- **Palabra "medio":** si se graba "me" sola, la voz la dice como una oración completa (0,45 s, con caída).
  Dentro de una frase real dura 0,1 s. Por eso cada palabra se grabó como "*palabra* todo", con el contexto
  "Ella dijo que…", y se cortó justo en el silencio de la "t". Queda la palabra tal como suena en medio de una
  oración. Con eso, "hoy me voy de vacaciones a la casa de mi tío" armada palabra por palabra dura 4,3 s, contra
  5,8 s grabando las palabras sueltas (la lectura natural de corrido dura 3,6 s).
- **Palabra "final":** la última palabra de la oración usa su versión con cierre ("…de mi tío.").
- **Empalmes:** 10 ms entre palabras, con fundidos de 6 ms, para que no haya clics.
- **Volumen:** una sola ganancia para todas las palabras, así "de" o "la" quedan naturalmente más suaves que
  "vacaciones".

## Qué pasa con lo que escriben los chicos

- **Mayúsculas, tildes y signos:** no importan. "tio", "Tío" y "TIO," suenan como "tío".
- **Palabras que suenan igual:** si el chico escribe "baca" o "kasa", la app usa el audio de "vaca" o "casa", porque
  suenan exactamente igual (b = v, h muda, ll = y, c/qu/k).
- **Palabras que no están en el banco:** se arman con sílabas ("fiesta" → fies-ta). Se entienden ("fiesta",
  "pantalón" y "zapato" se transcribieron bien), pero suenan menos naturales y no siempre marcan bien el acento de
  la palabra ("tomate" puede sonar "tómate"). Por eso conviene que todas las palabras de las fichas estén en el banco.
- **Coma y punto:** agregan una pausa corta (coma) o más larga (punto).

## Usarlo en la app (JavaScript)

```js
import { Lector } from "./audios_lectura/lector.js";
const lector = await Lector.crear("audios_lectura/");

// Sección "armar oraciones": leer lo que ordenó el chico
await lector.leerOracion(fichasEnOrden.join(" "));

// Sección "unir sílabas"
await lector.leerSecuencia([
  ["silabas", "vaca"], ["palabra", "vaca"],
  ["silabas", "la vaca"], ["oracion", "la vaca come pasto"],
]);

// Partes sueltas
await lector.leerSilabas("vaca");   // va - ca
await lector.leerPalabra("vaca");   // vaca
lector.detener();
```

- **Primer audio:** en celulares el audio solo arranca después de un toque del usuario (regla del navegador).
  Llamá a `leer…` desde el botón.
- **Otro lenguaje (Flutter, Kotlin, Swift…):** la lógica es corta y está comentada en `lector.js`:
  1. Buscar cada palabra: igual, sin tildes o por sonido.
  2. Usar la versión "final" para la última palabra y la versión "medio" para las demás.
  3. Unir con 10 ms de pausa.
  4. Si la palabra no existe, silabear y unir sílabas.

## Ajustes (en `manifest_lectura.json` → `parametros`)

| Parámetro | Valor | Efecto |
|---|---|---|
| `pausa_entre_palabras_ms` | 10 | Más alto = lectura más pausada |
| `pausa_entre_silabas_ms` | 300 | Pausa en "va - ca" |
| `pausa_entre_pasos_ms` | 700 | Entre "va - ca" y "vaca", etc. |
| `pausa_coma_ms` / `pausa_punto_ms` | 250 / 450 | Pausas por signos |
| `fundido_ms` | 6 | Suavizado en cada empalme |
| `solape_coda_ms` / `fusion_recorte` | 30 / 0.35 | Cómo se funden las piezas al armar una sílaba que no está grabada ("pa" + "an" → "pan") |

## Agregar palabras

Agregá la palabra en `herramientas/lectura.py` (lista `CONTENIDO` o `FUNCION`) y ejecutá
`python3 herramientas/lectura.py generar` y después `armar`. Cada palabra cuesta unos 15 caracteres de ElevenLabs
(versión medio + final).

## Limitaciones

- **Concatenación:** es un armado con palabras grabadas por separado. Suena mucho más natural que unir sílabas o
  sonidos sueltos, pero no tan perfecto como una frase grabada de corrido. Entre palabras se nota un ritmo un poco
  más parejo que al hablar.
- **Preguntas y exclamaciones:** se leen con la entonación de una afirmación. Para "¿…?" haría falta una versión
  "pregunta" de cada palabra final.
- **Voz de España:** la z y la c ante e/i suenan /θ/.
