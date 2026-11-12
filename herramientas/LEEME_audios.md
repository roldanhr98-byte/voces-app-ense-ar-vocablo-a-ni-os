# Voces para la app: vocales, sílabas, palabras y frases en español

- **Voz:** Martin Osborne – Deep and Passionate (ElevenLabs, español de España)
- **Modelo:** `eleven_multilingual_v2`
- **Formato:** WAV PCM, 16 bits, mono, 48 kHz (sin pérdida)

Abrí **`escuchar.html`** en el navegador para escuchar todo: tocás una letra, sílaba o palabra y suena, igual que en la app.

---

## Qué hay adentro

| Carpeta | Contenido | Archivos |
|---|---|---|
| `00_renders_bloques_completos/` | Los 6 bloques completos, de corrido (el "render") | 6 |
| `01_vocales/` | `a.wav` … `u.wav` + `vocales_a_e_i_o_u.wav` (las 5 seguidas) | 6 |
| `02_silabas_directas/<letra>/` | `ba.wav be.wav bi.wav bo.wav bu.wav` + `familia_b.wav` (Ba-Be-Bi-Bo-Bu seguidas) | 22 letras × 6 |
| `03_silabas_inversas/<letra>/` | `al.wav el.wav …` + `familia_l.wav` | 13 letras × 6 |
| `04_grupos_consonanticos/<grupo>/` | `bra.wav bre.wav …` + `familia_br.wav` | 12 grupos × 6 |
| `05_combinaciones_vocalicas/` | `ai.wav ei.wav oi.wav …` | 14 |
| `06_palabras_diptongos_hiatos/` | `aereo.wav poeta.wav pais.wav …` | 21 |
| `07_palabras_cortas/` | `casa.wav perro.wav sol.wav …` | 48 |
| `08_palabras_medianas_y_largas/` | `computadora.wav … anticonstitucional.wav` | 40 |
| `09_palabras_r_y_rr/` | `rana.wav … carretera.wav` | 28 |
| `10_palabras_contraste_bv_sz_gj/` | `baca.wav vaca.wav casa.wav caza.wav gente.wav jirafa.wav …` | 39 |
| `11_frases_cortas/` | `01_el_sol_sale_por_la_manana.wav` … | 12 |
| `12_parrafos/` | `parrafo_1.wav` … `parrafo_5.wav` + `oraciones/p1_01_….wav` (cada oración suelta) | 5 + 13 |
| `13_preguntas/` | `01_donde_estas.wav` … | 8 |
| `14_exclamaciones/` | `01_que_alegria_verte.wav` … | 6 |
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

- Todo en minúsculas, sin tildes ni signos: `Pájaro` → `pajaro.wav`, `¿Dónde estás?` → `01_donde_estas.wav`.
- La **ñ se escribe `ny`**: `Ña` → `ny/nya.wav`, `Mañana` → `manyana.wav`.
- El texto original exacto (con tildes y ñ) está en `manifest.json` y en `manifest.csv`, con la duración de cada archivo.

### Ejemplo de uso en la app (JavaScript)

```js
// Al tocar la letra B: la familia completa
new Audio("audios/02_silabas_directas/b/familia_b.wav").play();

// Al tocar una sílaba o palabra puntual
new Audio("audios/02_silabas_directas/b/ba.wav").play();
new Audio("audios/07_palabras_cortas/casa.wav").play();

// Buscar por texto usando el manifest
const manifest = await (await fetch("audios/manifest.json")).json();
const porTexto = Object.fromEntries(manifest.map(m => [m.texto, m.archivo]));
new Audio("audios/" + porTexto["Pájaro"]).play();
```

## Cómo quedó cada clip

- **Silencio:** cada clip arranca con unos 40 ms de silencio y termina unos 120 ms después de la voz, con fundidos cortos para que no haya clics.
- **Volumen:** está igualado entre clips (voz activa a −20 dBFS, pico máximo −1 dBFS), así no suena uno fuerte y otro bajo.
- **Familias:** los archivos `familia_*.wav` son las 5 sílabas tal como se grabaron seguidas, con su pausa natural.

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

- **Af, Az:** tenían una vocal agregada ("afe", "a-ce…"). Se regrabaron con otra semilla.
- **Dra:** "Dra." es la abreviatura de *Doctora* y la voz leía "doctora". Se envió como "Drá." (suena "dra") y quedó bien.
- **Ac, Ec, Ic, Oc, Uc:** la voz decía "az" y "uke". Cada sílaba se tomó de la mejor de varias tomas (con K, que suena igual) y ahora suenan /ak/, /ek/, /ik/, /ok/, /uk/.
- **Sima, Tasa, Taza, Abrazar, Abrasar:** se regrabaron con otra semilla porque "Abrasar" arrancaba con una "a" de más.

## Notas de pronunciación (voz de España)

- **Z y C ante e/i** (za, ce, ci, zo, zu, az, ez…): suenan /θ/, como en España, distinto de la S. Si la app es para Latinoamérica, conviene probar otra voz con seseo.
- **LL e Y** suenan igual (yeísmo). **B y V** suenan igual, que es lo correcto en español.
- **Ag, Eg, Ig, Og, Ug:** la G final sale suave [ɣ], como en "i**g**norar" o "di**g**no". Es la pronunciación natural, pero conviene escucharlas por si preferís una G más marcada.

**Para escuchar con atención:** las familias inversas `03_silabas_inversas/g/` y `c/`, y `03_silabas_inversas/z/`.
