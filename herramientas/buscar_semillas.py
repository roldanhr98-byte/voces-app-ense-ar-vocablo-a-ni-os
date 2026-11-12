"""Prueba varias semillas para una toma defectuosa y puntúa cada candidata.

  python3 herramientas/buscar_semillas.py "Az. Ez. Iz. Oz. Uz." [semillas...]

Criterios (automáticos):
  - pausas: todas las unidades separadas por silencio real (no quedan pegadas)
  - jorobas: cada sílaba con un solo núcleo vocálico (sin vocal agregada al final)
  - stt: la transcripción de la toma coincide con el texto (comparación fonética tolerante)
"""
import io
import json
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acustica as A  # noqa: E402
import recortar as R  # noqa: E402
from bloques import BLOQUES, texto_tts  # noqa: E402
from generar import TOMAS, clave_toma, obtener_toma, tomas_del_bloque  # noqa: E402
from verificar import fonetico  # noqa: E402

SEMILLAS = [1234, 7, 42, 99, 2024, 31337]


def grueso(t):
    """Fonética tolerante a ensordecimiento de consonantes finales y a c/z/s."""
    t = fonetico(t)
    for a, b in [("[bp](?=\\b)", "P"), ("[dt](?=\\b)", "T"), ("[gk](?=\\b)", "K"), ("[zs](?=\\b)", "S")]:
        t = re.sub(a, b, t)
    return t.replace("z", "s")


def stt_bytes(datos):
    import time
    for intento in range(6):
        r = requests.post("https://api.elevenlabs.io/v1/speech-to-text", headers={"xi-api-key": "proxy-injected"},
                          data={"model_id": "scribe_v1", "language_code": "spa", "tag_audio_events": "false"},
                          files={"file": ("t.wav", datos, "audio/wav")}, timeout=300)
        if r.status_code == 200:
            return r.json().get("text", "")
        time.sleep(3 * (intento + 1))
    r.raise_for_status()


def evaluar(texto, ajustes, prev, semilla, es_silaba):
    audio, al, _, _ = obtener_toma(texto, ajustes, prev, semilla)
    x = R.leer_wav(io.BytesIO(audio)) if False else None
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        f.write(audio)
        f.flush()
        x = R.leer_wav(f.name)
    db = R.energia_db(x)
    unidades = texto.split("\n\n")
    pos, spans = 0, []
    for u in unidades:
        i = texto.index(u, pos)
        spans.append(R.tiempos_alineados(al, i, i + len(u)))
        pos = i + len(u)
    segs = R.segmentar(db, spans, 0, len(x) / R.SR)
    pegadas = sum(1 for k in range(len(segs) - 1) if segs[k][1] >= segs[k + 1][0])
    clips = [R.extraer(x, *s)[0] for s in segs]
    jor = [A.jorobas_graves(c) if len(c) > 2400 else 0 for c in clips] if es_silaba else []
    oido = stt_bytes(audio)
    esperado = " ".join(u.rstrip(".") for u in unidades)
    ok_stt = grueso(oido) == grueso(esperado)
    unit_stt = []
    if not es_silaba:  # palabras: verificar cada una por separado
        for c in clips:
            with tempfile.NamedTemporaryFile(suffix=".wav") as f:
                R.escribir_wav(Path(f.name), c)
                unit_stt.append(stt_bytes(open(f.name, "rb").read()))
    malas_u = [u for u, s in zip(unidades, unit_stt) if grueso(s) != grueso(u)]
    puntaje = (ok_stt * 3 + (pegadas == 0) * 3 + (sum(j == 1 for j in jor) if jor else 0)
               - len(malas_u) * 2)
    return dict(semilla=semilla, puntaje=puntaje, pegadas=pegadas, jorobas=jor, stt=oido, stt_ok=ok_stt,
                unidades_mal=malas_u, durs=[round(s[1] - s[0], 2) for s in segs])


def buscar(clave_texto, semillas=SEMILLAS):
    for b in BLOQUES:
        if not b.get("por_tomas"):
            continue
        for texto, prev, _ in tomas_del_bloque(b):
            if " ".join(texto.split()) == clave_texto:
                es_silaba = b["id"] in (1, 2)
                res = [evaluar(texto, b["voice_settings"], prev, s, es_silaba) for s in semillas]
                for r in sorted(res, key=lambda r: -r["puntaje"]):
                    print(json.dumps(r, ensure_ascii=False))
                return res
    raise SystemExit(f"toma no encontrada: {clave_texto}")


if __name__ == "__main__":
    sem = [int(s) for s in sys.argv[2:]] or SEMILLAS
    buscar(sys.argv[1], sem)
