# Voces para la app de abecedario y pronunciación en español

Audios generados con ElevenLabs (modelo `eleven_multilingual_v2`) para enseñar a los chicos las vocales, las sílabas,
las palabras y la pronunciación, y para leer en voz alta lo que arman o escriben:

| Voz | Acento | Carpeta | Zip para la app |
|---|---|---|---|
| **Lumina – Neutral and Clear** (principal) | Latinoamérica, neutro | `voces/lumina/` | `voces_lumina.zip` |
| Martin Osborne – Deep and Passionate | España | `voces/martin_osborne/` | `voces_martin_osborne.zip` |
| Sara Martin – Gentle and Layered | España | `voces/sara_martin/` | `voces_sara_martin.zip` |

**Lumina** es la voz principal: se eligió entre 8 voces latinoamericanas porque es la más pareja (la que mejor se
encadena) y pronuncia con seseo, como los chicos de Latinoamérica. Su banco de lectura tiene 835 palabras grabadas;
el de Martin y Sara, 195. La comparación, las voces pendientes (Salva y Gabo) y cómo agregar una nueva están en
[`VOCES.md`](VOCES.md).

## Estructura

- **`probar_voces.html`**: página para importar el zip de una o varias voces (o elegir la carpeta) y probar letras,
  sílabas, palabras, frases y textos libres. Con varias voces aparece un selector para compararlas.
- **`voces/<voz>/biblioteca/`**: audios sueltos (vocales, sílabas, palabras, frases), con `manifest.json`,
  `manifest.csv` y `README.md`.
- **`voces/<voz>/lectura/`**: lectura encadenada (unir sílabas y armar oraciones en cualquier orden). Tiene las
  palabras en versión "medio" y "final", las sílabas y los dífonos, cada grupo en un solo archivo con su índice,
  más `lector.js` para la app y ejemplos. Detalle en
  [`voces/lumina/lectura/README.md`](voces/lumina/lectura/README.md).
- **`voces/<voz>/fuente/`**: para cada bloque, el texto enviado, los ajustes, las tomas y la alineación por carácter
  que devolvió ElevenLabs.
- **`herramientas/`**: scripts que generan, recortan, verifican y empaquetan. La voz y sus correcciones se
  definen en `herramientas/voces.py`.

Acá están los originales en WAV 48 kHz (sin pérdida). El zip de cada voz (`herramientas/empaquetar.py`) los convierte
a MP3: el de Lumina pesa 17 MB en lugar de 218 MB.

## Regenerar una voz

```bash
pip install requests numpy
export ELEVENLABS_API_KEY=...              # tu clave de ElevenLabs
export VOZ=lumina                          # lumina, martin, sara (ver herramientas/voces.py)
python3 herramientas/generar.py            # biblioteca: 6 bloques (bloques 1-4 en tomas cortas)
python3 herramientas/recortar.py           # recorta cada unidad y arma voces/<voz>/biblioteca/
python3 herramientas/verificar.py          # control de calidad con ElevenLabs Scribe
python3 herramientas/lectura.py generar    # palabras para encadenar
python3 herramientas/difonos.py            # palabras inventadas para los dífonos
python3 herramientas/lectura.py armar      # arma voces/<voz>/lectura/
python3 herramientas/lectura.py verificar
python3 herramientas/empaquetar.py         # probar_voces.html y trabajo/voces_<voz>.zip en MP3
```

- **Textos y carpetas:** se definen en `herramientas/bloques.py`.
- **Correcciones de cada voz** (semillas, tomas compuestas): en su perfil de `herramientas/voces.py`.
- **Costo:** una voz completa cuesta unos 22.000 caracteres de ElevenLabs con el banco de 835 palabras (unos 10.000
  con el de 195). Con la caché de `trabajo/`, volver a armar no cuesta nada.
