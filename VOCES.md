# Voces del proyecto

| Clave | Voz (ElevenLabs) | ID | Para | Estado |
|---|---|---|---|---|
| `martin` | Martin Osborne – Deep and Passionate | `Vpv1YgvVd6CHIzOTiTt8` | Varones | **Lista**: `voces/martin_osborne/` |
| `sara` | Sara Martin – Gentle and Layered | `KHCvMklQZZo0O30ERnVn` | Nenas | **Lista**: `voces/sara_martin/` |
| `salva` | Salva – The Spanish Narrator | `hyKxCTlAqtnW188CgltM` | Varones | Pendiente (anotada para más adelante) |
| `gabo` | Gabo – Deep, Evocative and Resonant | `o0SveC0zgHFuCsEO3vHR` | Varones | Pendiente (anotada para más adelante) |

Todas son de España (castellano): la z y la c ante e/i suenan /θ/.

**Otras versiones encontradas:**

- **Sara Martin:** "Young and Reflective" (`gD1IexrzCvsXPHUuT0s3`, más joven) y "Light, Intimate and Tender"
  (`Ir1QNHvhaJXbAGhT50w3`, pensada para narración íntima y romántica; no se usó por eso).
- **Gabo:** "Thoughtful, Moving, and Powerful" (`4yMqddmQqI9aTy9ysF9H`), con acento latinoamericano.

Para cambiar de versión, alcanza con cambiar el `id` en `herramientas/voces.py` y volver a generar.

## Hacer una voz nueva (por ejemplo Salva)

1. En `herramientas/voces.py`, quitá `"pendiente": True` de la voz.
2. Generá todo con esa voz. Cuesta unos 10.000 caracteres de ElevenLabs:

```bash
export VOZ=salva
python3 herramientas/generar.py            # biblioteca: 6 bloques (~4.700 caracteres)
python3 herramientas/recortar.py
python3 herramientas/verificar.py          # control de calidad con Scribe
python3 herramientas/lectura.py generar    # palabras para encadenar (~2.340)
python3 herramientas/difonos.py            # palabras inventadas para dífonos (~2.650)
python3 herramientas/lectura.py armar
python3 herramientas/lectura.py verificar
python3 herramientas/empaquetar.py         # trabajo/voces_salva.zip
```

3. Revisá lo que marque `verificar.py`. Con cada voz fallan cosas distintas: con Martin fueron Af, Az, Dra, Ac–Uc y
   Abrasar, y con Sara, Ac, Az y la palabra "a" de la lectura (salía "ia"). Para corregirlas se buscan semillas con `herramientas/buscar_semillas.py` o se arman
   tomas compuestas. Las correcciones de cada voz se anotan en su perfil de `voces.py` (`semilla_por_toma`,
   `tomas_compuestas`, `semilla_palabras`, `correcciones`). También va ahí `rango_f0`, el rango de tono de la voz,
   que sirve para igualar el tono en los empalmes.

## Créditos

El plan Starter tiene 39.941 caracteres por mes. Al 12 de noviembre de 2026, con Martin completa (con pruebas y
correcciones) y Sara completa, el contador de ElevenLabs marcaba 16.697. Ese contador se actualiza con atraso;
sumando lo enviado son unos 22.000. Se renuevan el 12 de diciembre. Para Salva y Gabo
(~10.000 cada una más correcciones) conviene esperar a la renovación o hacer una por mes.
