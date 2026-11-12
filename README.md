# Voces para la app de abecedario y pronunciación en español

Audios generados con ElevenLabs (voz **Martin Osborne – Deep and Passionate**, modelo `eleven_multilingual_v2`,
WAV 48 kHz mono 16 bits) para enseñar a los niños las vocales, las sílabas, las palabras y la pronunciación.

- **`probar_voces.html`**: página para importar el zip (o elegir esta carpeta) y probar letras, sílabas,
  palabras, frases y textos libres.
- **`biblioteca/`**: audios sueltos listos para la app (vocales, sílabas, palabras, frases), con `manifest.json`,
  `manifest.csv` y `README.md`.
- **`lectura/`**: lectura encadenada (unir sílabas y armar oraciones en cualquier orden): palabras en versión
  "medio" y "final", sílabas y dífonos, cada grupo en un solo archivo con su índice, más `lector.js` para la app y
  ejemplos. Detalle en [`lectura/README.md`](lectura/README.md). Se genera con `herramientas/lectura.py` y
  `herramientas/difonos.py`.
- **`herramientas/`**: scripts que generan, recortan, verifican y empaquetan los audios.
- **`fuente/`**: para cada bloque, el texto enviado, los ajustes de voz, las tomas y la alineación por carácter
  que devolvió ElevenLabs, que se usa para recortar.

Acá están los originales en WAV 48 kHz (sin pérdida). El zip para la app (`herramientas/empaquetar.py`) los convierte
a MP3: pesa unos 15 MB en lugar de 113 MB.

En [`biblioteca/README.md`](biblioteca/README.md) está el detalle de las carpetas, los nombres de archivo, cómo se grabó
y el control de calidad.

## Regenerar

```bash
pip install requests numpy
export ELEVENLABS_API_KEY=...            # tu clave de ElevenLabs
python3 herramientas/generar.py          # genera los 6 bloques (bloques 1-4 en tomas cortas)
python3 herramientas/recortar.py         # recorta cada unidad y arma biblioteca/ + manifest
python3 herramientas/verificar.py        # control de calidad con ElevenLabs Scribe
python3 herramientas/lectura.py generar   # palabras para encadenar (unos 2.300 caracteres)
python3 herramientas/difonos.py           # palabras inventadas para los dífonos (unos 2.650 caracteres)
python3 herramientas/lectura.py armar     # arma lectura/ (palabras, sílabas, dífonos, índice y ejemplos)
python3 herramientas/empaquetar.py       # probar_voces.html y zip unificado en MP3
```

- **Textos y carpetas:** se definen en `herramientas/bloques.py`. Ahí también están las tomas corregidas
  (`SEMILLA_POR_TOMA`, `TEXTO_TTS`, `TOMAS_COMPUESTAS`).
- **Otra voz:** basta con cambiar `VOZ_ID` en `bloques.py` y volver a correr todos los pasos.
- **Costo de volver a generar:** unos 4.700 caracteres de ElevenLabs la biblioteca y unos 5.000 la lectura. El audio puede variar un poco respecto de la
  versión entregada, así que conviene volver a verificarlo.
