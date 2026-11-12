# Lectura encadenada: unir sílabas y armar oraciones

Este paquete sirve para dos secciones de la app:

1. **Unir sílabas:** "va - ca" → "vaca" → "la - va - ca" → "la vaca come pasto".
2. **Armar oraciones:** el chico ordena palabras (o escribe) como quiera y la app lee lo que armó, fluido.

No hay frases grabadas. `lector.js` arma la lectura en el momento, en cualquier orden, con tres tipos de piezas, todas
con la misma voz (Sara Martin - Gentle and Layered, ElevenLabs `eleven_multilingual_v2`):

| Archivo | Qué tiene |
|---|---|
| `palabras.mp3` | 195 palabras frecuentes en dos versiones: **medio** (como suena dentro de una oración) y **final** (cierre de oración) |
| `difonos.mp3` | Unos 525 **dífonos**: la transición de un sonido al siguiente (k-a, a-s, s-a…), con y sin acento. Arman cualquier palabra que no esté grabada |
| `silabas.mp3` | 254 sílabas de la biblioteca, para leer "va - ca" |
| `manifest_lectura.json` | Índice: dónde empieza y cuánto dura cada pieza dentro de esos archivos, y los ajustes |
| `lector.js` | El lector para la app (JavaScript, Web Audio) |
| `ejemplos/` | Ejemplos armados con el lector |

En el zip las piezas van en **MP3** a 24 kHz y 48 kbps, que alcanza y sobra para voz. Los tres
archivos suman unos 2,5 MB. Los originales en WAV 48 kHz están en GitHub.

## Probar

- **`ejemplos/`:** escuchalos directamente.
- **`probar_voces.html`** (en la carpeta de arriba): importás el zip y probás todo, incluidas las pestañas
  **Escribir** y **Armar oración**, que usan este lector.

## Cómo se logró que no suene robótico

- **Palabras "medio":** si se graba "me" sola, la voz la dice como una oración entera (0,45 s, con caída). Dentro de
  una frase real dura 0,1 s. Por eso cada palabra se grabó como "*palabra* todo", con el contexto "Ella dijo
  que…", y se cortó justo donde termina su voz, antes de la "t". Queda como suena a mitad de una oración.
- **Mismo tono en los empalmes:** cada palabra se dice con su propia melodía, así que al pegarlas el tono saltaba de
  una a otra y se notaba el corte. Ahora el principio y el final de cada palabra se llevan al tono base de la voz,
  sin tocar la melodía de adentro. Se usa TD-PSOLA, que cambia el tono sin cambiar la duración ni el timbre, y la
  corrección se limita a 3 semitonos para no deformar palabras cortas.
- **Sin bajón de volumen:** se quita la cola que se apaga al final de las palabras que terminan en vocal, y los
  empalmes usan fundido de potencia constante.
- **Empalmes según los sonidos que se tocan**, como al hablar:
  - antes de p, t, k o ch: un silencio de 40 ms, que es el cierre natural de esa consonante;
  - vocal con vocal ("de‿agua"): se funden con un solape de 20 ms (con más, se pierden palabras cortas como "hoy");
  - el resto: solape de 15–20 ms.
- **Última palabra:** usa su versión "final", con el cierre de oración.
- **Palabras que no están grabadas:** se arman con dífonos, usando la versión acentuada en la sílaba que corresponde
  (to-**ma**-te). Las palabras inventadas de donde salen los dífonos se procesan antes de cortarlas:
  - el tono de cada sonido se acerca a mitad de camino del tono base (forzarlo del todo le quitaba claridad);
  - el volumen en cada punto de corte se iguala al típico de ese sonido.

**Mediciones** con la oración "hoy me voy de vacaciones a la casa de mi tío" y palabras armadas con dífonos:

| | Martin | Sara |
|---|---|---|
| Oración armada (la misma leída de corrido) | 3,29 s, 3 silencios cortos (3,28 s, 3 silencios) | 2,33 s, 3 silencios cortos |
| Salto de tono entre palabras | sin tono medible en los bordes | 0,3 semitonos (antes 3,5) |
| Salto de volumen entre palabras | 7,7 dB (antes 17) | 1,5 dB (antes 13) |
| Salto de tono dentro de palabras armadas (mediana) | 1,0 semitonos (antes 2,2) | 2,1 semitonos (antes 5,0) |
| Salto de volumen dentro de palabras armadas | 1,5 dB (antes 5,3) | 1,4 dB (antes 4,1) |
| 10 oraciones variadas transcritas exactas | 10/10 | 10/10 |

## Qué pasa con lo que escriben los chicos

- **Mayúsculas, tildes y signos:** no importan. "tio", "Tío" y "TIO," suenan como "tío".
- **Palabras que suenan igual:** si el chico escribe "baca" o "kasa", se usa el audio grabado de "vaca" o "casa",
  porque suenan igual (b = v, h muda, ll = y, c/qu/k).
- **Cualquier otra palabra:** se arma con dífonos. Se entiende bien, pero suena un poco menos natural que una palabra
  grabada entera. Por eso conviene que las palabras de las fichas estén en el banco.
- **Coma y punto:** agregan una pausa corta (coma) o más larga (punto).

## Velocidad

`Lector.crear()` descarga y decodifica los tres archivos **una sola vez**: unos 0,2 s en la prueba con la página.
Después, cada lectura se arma en memoria en 1 o 2 ms, sin esperas. Antes, cada palabra se descomprimía y
decodificaba por separado, una tras otra, y eso era lo que tardaba. Creá el lector al abrir la sección o al
iniciar la app, no en cada toque.

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

// Para mostrar cómo se va a leer cada palabra (grabada, suena igual o armada con dífonos)
lector.diagnostico("la baca come pazto");
```

- **Primer audio:** en celulares el audio solo arranca después de un toque del usuario (regla del navegador).
  Llamá a `leer…` desde el botón.
- **Memoria:** el lector trabaja a 24 kHz y ocupa unos 40 MB con todo cargado. Si ya tenés un `AudioContext`, pasalo
  con `Lector.crear("lectura/", { ctx })`.
- **Otro lenguaje (Flutter, Kotlin, Swift…):** la lógica completa está comentada en `lector.js`, que es corto.
  También está en Python, en `herramientas/lectura.py` y `herramientas/fonetica.py`: las dos versiones dan
  exactamente el mismo audio.

## Ajustes (en `manifest_lectura.json` → `parametros`)

| Parámetro | Valor | Efecto |
|---|---|---|
| `hueco_oclusiva_ms` | 40 | Silencio antes de p, t, k, ch |
| `solape_vocales_ms` | 35 | Cuánto se funden vocal + vocal |
| `solape_vocal_ms` / `solape_ms` | 20 / 15 | Resto de los empalmes (más alto = más pegado) |
| `pausa_entre_silabas_ms` | 300 | Pausa en "va - ca" |
| `pausa_entre_pasos_ms` | 700 | Entre "va - ca" y "vaca", etc. |
| `pausa_coma_ms` / `pausa_punto_ms` | 250 / 450 | Pausas por signos |
| `fundido_difono_ms` | 12 / 3 / 8 | Fundido entre dífonos (en vocal / en p,t,k,ch / resto) |

## Agregar palabras

Agregá la palabra en `herramientas/lectura.py` (lista `CONTENIDO` o `FUNCION`) y ejecutá
`python3 herramientas/lectura.py generar`, después `armar` y por último `herramientas/empaquetar.py`. Cada palabra
cuesta unos 15 caracteres de ElevenLabs (versión medio + final).

## Limitaciones

- **Concatenación:** es un armado con piezas grabadas por separado. El ritmo ya es casi el de una lectura natural,
  pero la melodía es más pareja que la de una frase grabada de corrido.
- **Preguntas y exclamaciones:** se leen con entonación de afirmación. Para "¿…?" haría falta una versión
  "pregunta" de cada palabra final.
- **Voz de España:** la z y la c ante e/i suenan /θ/.
