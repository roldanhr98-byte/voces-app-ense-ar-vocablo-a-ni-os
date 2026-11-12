# Voces del proyecto

| Clave | Voz (ElevenLabs) | ID | Acento | Estado |
|---|---|---|---|---|
| `lumina` | Lumina – Neutral and Clear | `x5IDPSl4ZUbhosMmVFTk` | Latinoamérica (neutro, con seseo) | **Principal**: `voces/lumina/`, con banco de lectura de 835 palabras |
| `martin` | Martin Osborne – Deep and Passionate | `Vpv1YgvVd6CHIzOTiTt8` | España | Lista: `voces/martin_osborne/`, con banco de 195 palabras |
| `sara` | Sara Martin – Gentle and Layered | `KHCvMklQZZo0O30ERnVn` | España | Lista: `voces/sara_martin/`, con banco de 195 palabras |
| `salva` | Salva – The Spanish Narrator | `hyKxCTlAqtnW188CgltM` | España | Pendiente (anotada para más adelante) |
| `gabo` | Gabo – Deep, Evocative and Resonant | `o0SveC0zgHFuCsEO3vHR` | España | Pendiente (anotada para más adelante) |

La voz que se usa si no se indica otra (`VOZ`) es `lumina`.

## Por qué Lumina

Se compararon 8 voces latinoamericanas de la biblioteca de ElevenLabs con la misma prueba: sílabas sueltas, palabras
sueltas y una oración armada pieza por pieza. En una lectura que se arma juntando grabaciones, lo más importante es que
la voz sea **pareja**: si el tono cambia mucho de una grabación a otra, al juntar las palabras se nota el empalme.

| Voz | Velocidad (sílabas/s) | Variación de tono entre grabaciones | Salto de tono típico en un empalme | Ruido de fondo |
|---|---|---|---|---|
| **Lumina** | 7,3 | **0,8 st** | 1,2 st | -85 dBFS |
| Isabella | 6,2 | 0,9 st | 1,2 st | -51 dBFS (se oye un soplido) |
| Mauro | 7,6 | 1,1 st | 1,0 st | -90 dBFS |
| Isabel | 7,6 | 1,2 st | 1,7 st | — |
| Ninoska | 6,3 | 2,1 st | 2,6 st | -81 dBFS |
| Cony | 6,8 | 2,2 st | 2,0 st | -59 dBFS |
| Gaby | 6,1 | 2,7 st | 2,7 st | — |
| David | 6,7 | 2,9 st | 3,7 st | -81 dBFS |

*st = semitonos: cuanto menos, más pareja.*

- **Lumina** es la más pareja, tiene el fondo limpio y suena clara y cálida, con acento neutro (Colombia). Como habla
  algo rápido, las palabras, las frases y la lectura se graban al 90 % de velocidad (unas 6,2 sílabas por segundo).
  Las letras y sílabas sueltas se graban al 100 %, porque a menos velocidad "Ba" se confundía con "Pa".
- **Acento:** Martin y Sara son de España, donde la z y la c ante e/i suenan /θ/. Para chicos de Latinoamérica
  conviene una voz con seseo como Lumina, que pronuncia como ellos.

**Correcciones de Lumina** (detalle en su perfil de `herramientas/voces.py`):

- **Ca:** la leía "sa"; se graba como "Ka", que suena igual.
- **Ja, Je, Ji, Jo, Ju:** sola, la J salía como "ch" del inglés (che, chi, cho, chu). Cada sílaba se grabó después de
  una palabra que la usa ("Jefe. Je.") y se recortó solo la sílaba.
- **Ac, Ic, Oc, Uc y At:** salían con una vocal agregada ("ace", "ate"). Se tomaron de tomas escritas con K, con tilde
  o con otra semilla.
- **Az:** leía "acento". Con seseo "az" suena igual que "as", así que se usa esa grabación.
- **Za, Ce, Ci, Zo, Zu:** salían pegadas. Se regrabaron con otra semilla.

**Otras versiones encontradas:**

- **Sara Martin:** "Young and Reflective" (`gD1IexrzCvsXPHUuT0s3`, más joven) y "Light, Intimate and Tender"
  (`Ir1QNHvhaJXbAGhT50w3`, pensada para narración íntima y romántica; no se usó por eso).
- **Gabo:** "Thoughtful, Moving, and Powerful" (`4yMqddmQqI9aTy9ysF9H`), con acento latinoamericano.

Para cambiar de versión, alcanza con cambiar el `id` en `herramientas/voces.py` y volver a generar.

## Hacer una voz nueva (por ejemplo Salva)

1. En `herramientas/voces.py`, quitá `"pendiente": True` de la voz.
2. Generá todo con esa voz:

```bash
export VOZ=salva
python3 herramientas/generar.py            # biblioteca: 6 bloques (~4.700 caracteres)
python3 herramientas/recortar.py
python3 herramientas/verificar.py          # control de calidad con Scribe
python3 herramientas/lectura.py generar    # banco de palabras para encadenar (~14.000 con las 835 palabras)
python3 herramientas/difonos.py            # palabras inventadas para dífonos (~2.650)
python3 herramientas/lectura.py armar
python3 herramientas/lectura.py verificar
python3 herramientas/empaquetar.py         # trabajo/voces_salva.zip
```

3. Revisá lo que marque `verificar.py`. Con cada voz fallan cosas distintas: con Martin fueron Af, Az, Dra, Ac–Uc y
   Abrasar; con Sara, Ac, Az y la palabra "a" de la lectura (salía "ia"); con Lumina, Ca, la familia J, Ac–Uc, At,
   Az y la familia Z. Para corregirlas se buscan semillas con `herramientas/buscar_semillas.py` o se arman tomas
   compuestas. Las correcciones de cada voz se anotan en su perfil de `voces.py` (`semilla_por_toma`,
   `tomas_compuestas`, `semilla_palabras`, `correcciones`). También van ahí `rango_f0`, el rango de tono de la voz,
   que sirve para igualar el tono en los empalmes, y `dialecto`, que elige las notas de pronunciación de los README.

`armar` solo usa las palabras que ya tienen grabación con esa voz: si se generó una parte del banco, el resto se lee
con dífonos y no se gasta nada de más.

## Créditos

El plan Starter tiene 39.941 caracteres por mes y se renueva el 12 de cada mes. En el período que termina el 12 de
diciembre de 2026 se usó casi todo:

- Martin completa, con pruebas y correcciones, y Sara completa: unos 22.000.
- Comparación de voces y Lumina completa, con el banco de lectura ampliado a 835 palabras: unos 17.500.

Una voz nueva completa cuesta unos 22.000 caracteres con el banco grande, o unos 10.000 con el banco de 195 palabras.
Conviene hacer una por mes.
