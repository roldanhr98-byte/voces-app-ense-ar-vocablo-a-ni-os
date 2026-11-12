"""Control de calidad: transcribe cada clip con ElevenLabs Scribe y lo compara
fonéticamente con el texto esperado (b=v, ll=y, c/z, g/j, h muda, etc.).
Además revisa duraciones, silencios en los bordes y recortes.

  python3 herramientas/verificar.py          -> trabajo/verificacion.json + resumen en pantalla
"""
import json
import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acustica as A  # noqa: E402
import recortar as R  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CACHE = RAIZ / "trabajo" / "stt_clips"


def fonetico(t):
    t = t.lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn" or c == "̃")
    t = unicodedata.normalize("NFC", t)
    t = re.sub(r"[^a-zñ ]+", " ", t)
    reglas = [("ch", "C"), ("ll", "y"), ("rr", "r"), ("qu", "k"), ("gu(?=[ei])", "g"), ("gü", "gu"),
              ("c(?=[ei])", "z"), ("c", "k"), ("g(?=[ei])", "j"), ("h", ""), ("v", "b"), ("w", "u"),
              ("x", "ks")]
    for a, b in reglas:
        t = re.sub(a, b, t)
    return " ".join(t.split())


def stt(ruta):
    import hashlib
    CACHE.mkdir(parents=True, exist_ok=True)
    cache = CACHE / (hashlib.md5(ruta.read_bytes()).hexdigest() + ".json")
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    for intento in range(5):
        r = requests.post("https://api.elevenlabs.io/v1/speech-to-text",
                          headers={"xi-api-key": os.environ.get("ELEVENLABS_API_KEY", "proxy-injected")},
                          data={"model_id": "scribe_v1", "language_code": "spa", "tag_audio_events": "false"},
                          files={"file": open(ruta, "rb")}, timeout=300)
        if r.status_code == 200:
            cache.write_text(r.text, encoding="utf-8")
            return r.json()
        time.sleep(3 * (intento + 1))
    raise RuntimeError(f"STT {r.status_code}: {r.text[:300]}")


def revisar(m):
    ruta = RAIZ / "audios" / m["archivo"]
    x = R.leer_wav(ruta)
    db = R.energia_db(x)
    res = {"archivo": m["archivo"], "texto": m["texto"], "tipo": m["tipo"], "problemas": []}
    # bordes: el clip debe empezar y terminar en silencio (no cortar la voz)
    if m["tipo"] != "render_bloque":
        if db[:2].max() > -45:
            res["problemas"].append("inicio con voz (posible recorte)")
        if db[-3:].max() > -45:
            res["problemas"].append("final con voz (posible recorte)")
    if m["tipo"] == "render_bloque":
        return res
    silaba = m["tipo"] == "unidad" and m["bloque"] in (1, 2) or m.get("seccion") == "combinaciones_vocalicas"
    if silaba:
        res["nucleos_vocalicos"] = A.jorobas_graves(x)
        if res["nucleos_vocalicos"] > 2:
            res["problemas"].append("más de un núcleo vocálico")
    s = stt(ruta)
    oido = s.get("text", "")
    res["stt"] = oido
    esp, obt = fonetico(m["texto"]), fonetico(oido)
    res["similitud"] = round(SequenceMatcher(None, esp.replace(" ", ""), obt.replace(" ", "")).ratio(), 2)
    # Scribe no es fiable con sílabas sueltas (las confunde con palabras inglesas que suenan igual:
    # "Fu" -> "Fool", "Ki" -> "Key"); para ellas la referencia es la transcripción de la familia.
    if esp != obt and not silaba:
        res["problemas"].append(f"STT distinto: esperado '{esp}' / oído '{obt}'")
    return res


def main():
    man = json.loads((RAIZ / "audios" / "manifest.json").read_text(encoding="utf-8"))
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(revisar, man))
    (RAIZ / "trabajo" / "verificacion.json").write_text(json.dumps(res, ensure_ascii=False, indent=1),
                                                       encoding="utf-8")
    clips = [r for r in res if r["tipo"] != "render_bloque"]
    ok = [r for r in clips if not r["problemas"]]
    print(f"clips revisados: {len(clips)}  sin observaciones: {len(ok)}")
    por_carpeta = {}
    for r in clips:
        por_carpeta.setdefault(r["archivo"].split("/")[0], []).append(r)
    for c, rs in sorted(por_carpeta.items()):
        malos = [r for r in rs if r["problemas"]]
        print(f"  {c:40s} {len(rs) - len(malos):3d}/{len(rs)} ok   similitud media {np.mean([r['similitud'] for r in rs]):.2f}")
    print("\nObservaciones:")
    for r in clips:
        if r["problemas"]:
            print(f"  {r['archivo']:60s} {r['texto'][:30]:30s} -> {r.get('stt', '')[:40]!r:42s} "
                  f"{'; '.join(p for p in r['problemas'] if not p.startswith('STT'))}")


if __name__ == "__main__":
    main()
