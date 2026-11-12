# Lectura encadenada: unir sílabas y armar oraciones

Este paquete sirve para dos secciones de la app:

1. **Unir sílabas:** "va - ca" → "vaca" → "la - va - ca" → "la vaca come pasto".
2. **Armar oraciones:** el chico ordena palabras (o escribe) como quiera y la app lee lo que armó, de corrido.

No hay frases grabadas. `lector.js` arma la lectura en el momento, en cualquier orden, con tres tipos de piezas, todas
con la misma voz (Martin Osborne - Deep and Passionate, ElevenLabs `eleven_multilingual_v2`):

| Archivo | Qué tiene |
|---|---|
| `palabras_1.mp3` … `palabras_2.mp3` | 195 palabras frecuentes, en dos versiones: **medio** (como suena dentro de una oración) y **final** (cierre de oración). Van repartidas en varios archivos para que cada uno cargue rápido |
| `difonos.mp3` | Unos 525 **dífonos**: la transición de un sonido al siguiente (k-a, a-s, s-a…), con y sin acento. Arman cualquier palabra que no esté grabada |
| `silabas.mp3` | 254 sílabas de la biblioteca, para leer "va - ca" |
| `manifest_lectura.json` | Índice: en qué archivo está cada pieza, dónde empieza, cuánto dura, y los ajustes |
| `lector.js` | El lector para la app (JavaScript, Web Audio) |
| `ejemplos/` | Ejemplos armados con el lector |

En el zip las piezas van en **MP3** a 24 kHz y 48 kbps, que alcanza y sobra para voz. Los originales en WAV 48 kHz están
en GitHub.

## Probar

- **`ejemplos/`:** escuchalos directamente.
- **`probar_voces.html`** (en la carpeta de arriba): importás el zip y probás todo, incluidas las pestañas
  **Escribir** y **Armar oración**, que usan este lector. Las dos tienen un selector de **ritmo**.

## Cómo se logró que no suene robótico

- **Palabras "medio":** si se graba "me" sola, la voz la dice como una oración entera (0,45 s, con caída). Dentro de
  una frase real dura 0,1 s. Por eso cada palabra se grabó como "*palabra* todo", con el contexto "Ella dijo
  que…", y se cortó justo donde termina su voz, antes de la "t". Queda como suena a mitad de una oración.
- **Empalme "legato":** cada palabra conserva su final natural y la siguiente entra encima de ese final mientras se
  apaga, sin fundidos que bajen el volumen. No queda ni un hueco ni un corte seco: se escucha de corrido, como cuando
  alguien lee en voz alta.
- **Antes de p, t, k o ch:** queda un silencio de 30 ms, que es el cierre natural de esas consonantes al hablar.
- **Mismo tono en los empalmes:** cada palabra se dice con su propia melodía, así que al pegarlas el tono saltaba de
  una a otra. Ahora el principio y el final de cada palabra se llevan al tono base de la voz, sin tocar la melodía de
  adentro. Se usa TD-PSOLA, que cambia el tono sin cambiar la duración ni el timbre, y la corrección se limita a
  3 semitonos para no deformar palabras cortas.
- **Cierre de oración:** la última palabra, y la que va antes de un punto, usan su versión "final", que se apaga sola
  con la entonación de fin de oración.
- **Pausas sin cortes secos:** en una coma, o con el ritmo pausado, la palabra anterior se apaga suave (40 ms) en
  lugar de cortarse de golpe.
- **Palabras que no están grabadas:** se arman con dífonos, usando la versión acentuada en la sílaba que corresponde
  (hi-po-**pó**-ta-mo). Las palabras inventadas de donde salen los dífonos se procesan antes de cortarlas:
  - el tono de cada sonido se acerca a mitad de camino del tono base (forzarlo del todo le quitaba claridad);
  - el volumen en cada punto de corte se iguala al típico de ese sonido.

**Mediciones con Lumina** (10 oraciones variadas, por ejemplo "hoy me voy de vacaciones a la casa de mi tío"):

| | Antes (cortes con fundido) | Ahora (legato) | Leída de corrido por la voz |
|---|---|---|---|
| Bajón de volumen en la unión entre palabras (mediana) | 15,3 dB | 5,6 dB | 5,0 dB |
| Duración de "hoy me voy de vacaciones a la casa de mi tío" | 2,63 s | 2,61 s | 2,83 s (con silencios de borde) |
| Oraciones transcritas exactas por Scribe | — | 10/10 (también con ritmo pausado) | — |

El bajón entre palabras quedó como el de una lectura natural: ni el corte seco de antes ni palabras amontonadas.

## Ritmo

Para chicos que recién empiezan, la lectura puede ir más lenta sin cortes secos:
`lector.p.pausa_extra_ms = 120` (pausado) o `250` (muy pausado) agrega esa pausa entre palabras, y cada palabra se
apaga suave antes de la pausa. Con `0` vuelve al ritmo normal. En `probar_voces.html` es el selector "Ritmo".

## Qué pasa con lo que escriben los chicos

- **Mayúsculas, tildes y signos:** no importan si no cambian la palabra. "tio", "Tío" y "TIO," suenan como "tío".
  Si la palabra sin tilde también existe ("esta" y "está", "como" y "cómo"), se lee la que está escrita.
- **Palabras que suenan igual:** si el chico escribe "baca" o "kasa", se usa el audio grabado de "vaca" o "casa",
  porque suenan igual (b = v, h muda, ll = y, c/qu/k).
- **Cualquier otra palabra:** se arma con dífonos. Se entiende bien, pero suena un poco menos natural que una palabra
  grabada entera. Por eso conviene que las palabras de las fichas estén en el banco.
- **Coma y punto:** agregan una pausa corta (coma) o más larga (punto).

## Velocidad y memoria

`Lector.crear()` descarga y decodifica los audios **una sola vez**, de a dos por vez. Después, cada lectura se arma en
memoria en 1 o 2 ms, sin esperas. Creá el lector al abrir la sección o al iniciar la app, no en cada toque.

En memoria, los audios se guardan como números enteros de 16 bits, la mitad de lo que ocupa el formato de Web Audio.
Con todo cargado ocupa unos 25 MB.

## Usarlo en la app (JavaScript)

```js
import { Lector } from "./lectura/lector.js";
const lector = await Lector.crear("lectura/");          // una vez, al iniciar

// Sección "armar oraciones": leer lo que ordenó o escribió el chico
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

// Más lento para los que empiezan (0 = normal)
lector.p.pausa_extra_ms = 120;

// Para mostrar cómo se va a leer cada palabra (grabada, suena igual o armada con dífonos)
lector.diagnostico("la baca come pazto");
```

- **Primer audio:** en celulares el audio solo arranca después de un toque del usuario (regla del navegador).
  Llamá a `leer…` desde el botón.
- **Si ya tenés un `AudioContext`**, pasalo con `Lector.crear("lectura/", { ctx })`.
- **Otro lenguaje (Flutter, Kotlin, Swift…):** la lógica completa está comentada en `lector.js`, que es corto.
  También está en Python, en `herramientas/lectura.py` y `herramientas/fonetica.py`: las dos versiones dan
  exactamente el mismo audio.

## Ajustes (en `manifest_lectura.json` → `parametros`)

| Parámetro | Valor | Efecto |
|---|---|---|
| `entrada_ms` | 10 | Cuánto antes de que termine la palabra anterior entra la siguiente |
| `solape_cola` | 0,5 | Qué parte del final que se apaga de la palabra anterior queda debajo de la siguiente (0 = nada, 1 = todo) |
| `hueco_oclusiva_ms` | 30 | Silencio antes de p, t, k, ch |
| `pausa_extra_ms` | 0 | Pausa extra entre palabras para leer más lento (120 = pausado, 250 = muy pausado) |
| `pausa_entre_silabas_ms` | 300 | Pausa en "va - ca" |
| `pausa_entre_pasos_ms` | 700 | Entre "va - ca" y "vaca", etc. |
| `pausa_coma_ms` / `pausa_punto_ms` | 250 / 450 | Pausas por signos |
| `fundido_difono_ms` | 12 / 3 / 8 | Fundido entre dífonos (en vocal / en p, t, k, ch / resto) |

## Agregar palabras

Agregá la palabra en `herramientas/lectura.py`: en `CONTENIDO`, en la categoría que corresponda, o en `FUNCION` si es
un artículo o un conector. Después ejecutá `python3 herramientas/lectura.py generar`, `armar` y por último
`herramientas/empaquetar.py`. Cada palabra cuesta unos 20 caracteres de ElevenLabs (versión medio + final).

## Limitaciones

- **Concatenación:** es un armado con piezas grabadas por separado. El ritmo ya es el de una lectura natural, pero la
  melodía es más pareja que la de una frase grabada de corrido.
- **Preguntas y exclamaciones:** se leen con entonación de afirmación. Para "¿…?" haría falta una versión
  "pregunta" de cada palabra final.
- **Voz de España:** la z y la c ante e/i suenan /θ/.
