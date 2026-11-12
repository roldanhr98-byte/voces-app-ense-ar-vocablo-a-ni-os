# Voces para la app: vocales, sílabas, palabras y frases en español

- **Voz:** Martin Osborne - Deep and Passionate (ElevenLabs, español de España)
- **Modelo:** `eleven_multilingual_v2`
- **Formato:** en el zip, MP3 mono de 64 kbps (48 kHz), liviano para la app. Los originales en WAV 48 kHz 16 bits
  (sin pérdida) están en GitHub, en la carpeta `biblioteca/`.

Para escuchar todo, abrí **`probar_voces.html`** (en la carpeta de arriba) e importá el zip: tocás una letra, sílaba o palabra y suena, igual que en la app.

---

## Qué hay adentro

| Carpeta | Contenido | Archivos |
|---|---|---|
| `00_renders_bloques_completos/` | Los 6 bloques completos, de corrido (el "render") | 6 |
| `01_vocales/` | `a.mp3` … `u.mp3` + `vocales_a_e_i_o_u.mp3` (las 5 seguidas) | 6 |
| `02_silabas_directas/<letra>/` | `ba.mp3 be.mp3 bi.mp3 bo.mp3 bu.mp3` + `familia_b.mp3` (Ba-Be-Bi-Bo-Bu seguidas) | 22 letras × 6 |
| `03_silabas_inversas/<letra>/` | `al.mp3 el.mp3 …` + `familia_l.mp3` | 13 letras × 6 |
| `04_grupos_consonanticos/<grupo>/` | `bra.mp3 bre.mp3 …` + `familia_br.mp3` | 12 grupos × 6 |
| `05_combinaciones_vocalicas/` | `ai.mp3 ei.mp3 oi.mp3 …` | 14 |
| `06_palabras_diptongos_hiatos/` | `aereo.mp3 poeta.mp3 pais.mp3 …` | 21 |
| `07_palabras_cortas/` | `casa.mp3 perro.mp3 sol.mp3 …` | 48 |
| `08_palabras_medianas_y_largas/` | `computadora.mp3 … anticonstitucional.mp3` | 40 |
| `09_palabras_r_y_rr/` | `rana.mp3 … carretera.mp3` | 28 |
| `10_palabras_contraste_bv_sz_gj/` | `baca.mp3 vaca.mp3 casa.mp3 caza.mp3 gente.mp3 jirafa.mp3 …` | 39 |
| `11_frases_cortas/` | `01_el_sol_sale_por_la_manana.mp3` … | 12 |
| `12_parrafos/` | `parrafo_1.mp3` … `parrafo_5.mp3` + `oraciones/p1_01_….mp3` (cada oración suelta) | 5 + 13 |
| `13_preguntas/` | `01_donde_estas.mp3` … | 8 |
| `14_exclamaciones/` | `01_que_alegria_verte.mp3` … | 6 |
| `manifest.json` / `manifest.csv` | Lista de todos los archivos con su texto original exacto | — |

**Total:** 469 clips individuales + 48 familias + 5 párrafos + 6 renders = 528 archivos.

### Letras de las sílabas directas

`b p m f v t d n ny(ñ) l r s j ch y c g z k w ll rr`

- `c/` → Ca, Que, Qui, Co, Cu (sonido K)
- `g/` → Ga, Gue, Gui, Go, Gu
- `z/` → Za, Ce, Ci, Zo, Zu
- `ny/` → Ña, Ñe, Ñi, Ño, Ñu
- `r/` → Ra… y `rr/` → Rra…

## Cómo están nombrados

- Todo en minúsculas, sin tildes ni signos: `Pájaro` → `pajaro.mp3`, `¿Dónde estás?` → `01_donde_estas.mp3`.
- La **ñ se escribe `ny`**: `Ña` → `ny/nya.mp3`, `Mañana` → `manyana.mp3`.
- El texto original exacto (con tildes y ñ) está en `manifest.json` y en `manifest.csv`, con la duración de cada archivo.

### Ejemplo de uso en la app (JavaScript)

```js
// Al tocar la letra B: la familia completa
new Audio("biblioteca/02_silabas_directas/b/familia_b.mp3").play();

// Al tocar una sílaba o palabra puntual
new Audio("biblioteca/02_silabas_directas/b/ba.mp3").play();
new Audio("biblioteca/07_palabras_cortas/casa.mp3").play();

// Buscar por texto usando el manifest
const manifest = await (await fetch("biblioteca/manifest.json")).json();
const porTexto = Object.fromEntries(manifest.map(m => [m.texto, m.archivo]));
new Audio("biblioteca/" + porTexto["Pájaro"]).play();
```

## Cómo quedó cada clip

- **Silencio:** cada clip arranca con unos 40 ms de silencio y termina unos 120 ms después de la voz, con fundidos cortos para que no haya clics.
- **Volumen:** está igualado entre clips (voz activa a −20 dBFS, pico máximo −1 dBFS), así no suena uno fuerte y otro bajo.
- **Familias:** los archivos `familia_*.mp3` son las 5 sílabas tal como se grabaron seguidas, con su pausa natural.

## Cómo se grabó

**Ajustes de la voz:**

- **Bloques 1 a 5 (neutros):** estabilidad 0.80, similitud 0.90, estilo 0.0, velocidad 1.0, *speaker boost* activado y semilla 1234. La normalización de texto está desactivada, para que "I." no se lea como número romano.
- **Bloque 6 (preguntas y exclamaciones):** se generó aparte, con estabilidad 0.75 y estilo 0.10, porque necesita entonación.

**Bloques 1 a 4 (sílabas y palabras) en tomas cortas.** Primero se grabó cada bloque entero de una vez. Con 110 sílabas seguidas, la voz las leyó como una lista apurada:

- pausas de 0,16 s;
- "Ja" sonaba "ya";
- palabras de 0,15 s.

Por eso se rehízo cada bloque en tomas de hasta 5 unidades: cada familia (Ba-Be-Bi-Bo-Bu) es una toma, y cada toma de palabras tiene hasta 5 palabras. Todas usan la misma voz, los mismos ajustes y la misma semilla. Así cada sílaba se pronuncia clara (unos 0,45 s por sílaba), con pausas de 0,5 a 1 s. El render de cada bloque son esas tomas unidas, con 0,45 s de silencio entre una y otra.

**Bloques 5 y 6 (frases):** se grabaron de una sola vez, porque ahí la lectura salió natural.

## Control de calidad

1. **Transcripción automática:** cada familia de sílabas, palabra, frase y oración se transcribió con ElevenLabs Scribe y se comparó con el texto. Todas las palabras, frases, preguntas y exclamaciones coinciden. Las únicas diferencias son confusiones conocidas de Scribe, y se comprobó con el espectrograma que el audio está bien: "Pera" → "Espera", "Taza" → "Data", "Té" → "T", "Loro" → "Loto".
2. **Control acústico:** se revisó cada clip para detectar vocales agregadas (por ejemplo "afe" en lugar de "af"), sílabas pegadas y cortes en la voz.
3. **Espectrogramas:** se revisaron a mano los casos dudosos (J frente a Y, Z frente a S, sílabas inversas).

**Tomas corregidas:**

- **Dra:** "Dra." es la abreviatura de *Doctora* y la voz la leía "doctora". Se envía como "Drá." (suena "dra").
- **Af, Az:** tenían una vocal agregada ("afe", "a-ce…"). Se regrabaron con otra semilla.
- **Dra, Dre…:** con la semilla original "Dra" y "Dre" quedaban pegadas. Se regrabó con otra semilla.
- **Ac, Ec, Ic, Oc, Uc:** la voz decía "az" y "uke". Cada sílaba se tomó de la mejor de varias tomas (con K, que suena igual) y ahora suenan /ak/, /ek/, /ik/, /ok/, /uk/.
- **Sima, Tasa, Taza, Abrazar, Abrasar:** se regrabaron con otra semilla porque "Abrasar" arrancaba con una "a" de más.

## Notas de pronunciación (voz de España)

- **Z y C ante e/i** (za, ce, ci, zo, zu, az, ez…): suenan /θ/, como en España, distinto de la S. Si la app es para Latinoamérica, conviene probar otra voz con seseo.
- **LL e Y** suenan igual (yeísmo). **B y V** suenan igual, que es lo correcto en español.
- **Ag, Eg, Ig, Og, Ug:** la G final sale suave [ɣ], como en "i**g**norar" o "di**g**no". Es la pronunciación natural, pero conviene escucharlas por si preferís una G más marcada.

**Para escuchar con atención:** las familias inversas `03_silabas_inversas/g/` y `c/`, y `03_silabas_inversas/z/`.
