# Voces para la app de abecedario y pronunciación en español

Audios generados con ElevenLabs (voz **Martin Osborne – Deep and Passionate**, modelo `eleven_multilingual_v2`,
WAV 48 kHz mono 16 bits) para enseñar a los niños las vocales, las sílabas, las palabras y la pronunciación.

- **`audios/`**: todos los audios listos para la app, recortados y organizados por carpeta, con `manifest.json`,
  `manifest.csv`, `README.md` y `escuchar.html` (página para probarlos). Es el mismo contenido del zip entregado.
- **`herramientas/`**: scripts que generan, recortan, verifican y empaquetan los audios.
- **`fuente/`**: para cada bloque, el texto enviado, los ajustes de voz, las tomas y la alineación por carácter
  que devolvió ElevenLabs, que se usa para recortar.

En [`audios/README.md`](audios/README.md) está el detalle de las carpetas, los nombres de archivo, cómo se grabó
y el control de calidad.

## Regenerar

```bash
pip install requests numpy
export ELEVENLABS_API_KEY=...            # tu clave de ElevenLabs
python3 herramientas/generar.py          # genera los 6 bloques (bloques 1-4 en tomas cortas)
python3 herramientas/recortar.py         # recorta cada unidad y arma audios/ + manifest
python3 herramientas/verificar.py        # control de calidad con ElevenLabs Scribe
python3 herramientas/empaquetar.py       # README, escuchar.html y zip
```

- **Textos y carpetas:** se definen en `herramientas/bloques.py`. Ahí también están las tomas corregidas
  (`SEMILLA_POR_TOMA`, `TEXTO_TTS`, `TOMAS_COMPUESTAS`).
- **Otra voz:** basta con cambiar `VOZ_ID` en `bloques.py` y volver a correr los cuatro pasos.
- **Costo de volver a generar:** unos 4.700 caracteres de ElevenLabs. El audio puede variar un poco respecto de la
  versión entregada, así que conviene volver a verificarlo.
