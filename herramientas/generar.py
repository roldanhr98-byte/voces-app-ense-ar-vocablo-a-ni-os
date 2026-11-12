"""Genera cada bloque completo con ElevenLabs (una llamada por bloque) y guarda
el audio crudo + la alineación por carácter que devuelve /with-timestamps.

Uso:
  ELEVENLABS_API_KEY=... python3 herramientas/generar.py            # todos los bloques
  ELEVENLABS_API_KEY=... python3 herramientas/generar.py 1 3        # solo bloques 1 y 3
  ... --forzar                                                      # regenerar aunque exista
"""
import base64
import json
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bloques import (BLOQUES, FORMATO, MODELO, SEMILLA, SEMILLA_POR_TOMA, TOMAS_COMPUESTAS,  # noqa: E402
                     VOZ_ID, VOZ_NOMBRE, construir_texto, texto_tts)

RAIZ = Path(__file__).resolve().parent.parent
CRUDO = RAIZ / "trabajo" / "crudo"
FUENTE = RAIZ / "fuente"
API = "https://api.elevenlabs.io/v1"


def clave():
    return os.environ.get("ELEVENLABS_API_KEY", "proxy-injected")


def tts_con_tiempos(texto, voice_settings, previous_text=None, next_text=None, semilla=SEMILLA, voz=None):
    cuerpo = {
        "text": texto,
        "model_id": MODELO,
        "seed": semilla,
        "apply_text_normalization": "off",  # evita que "I." se lea como número romano
        "voice_settings": voice_settings,
    }
    if previous_text:
        cuerpo["previous_text"] = previous_text
    if next_text:
        cuerpo["next_text"] = next_text
    for intento in range(5):
        r = requests.post(f"{API}/text-to-speech/{voz or VOZ_ID}/with-timestamps",
                          params={"output_format": FORMATO},
                          headers={"xi-api-key": clave()}, json=cuerpo, timeout=600)
        if r.status_code == 200:
            d = r.json()
            return base64.b64decode(d["audio_base64"]), d["alignment"], d.get("normalized_alignment"), cuerpo
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(5 * (intento + 1))
            continue
        raise RuntimeError(f"ElevenLabs {r.status_code}: {r.text[:500]}")
    raise RuntimeError("ElevenLabs: demasiados reintentos")


SR = 48000
PAUSA_ENTRE_TOMAS = 0.45  # silencio que se agrega entre tomas al armar el render del bloque


def trozos(lista, maximo=5):
    """Divide una lista en trozos parejos de como mucho `maximo` elementos."""
    n = -(-len(lista) // maximo)
    base, extra = divmod(len(lista), n)
    res, i = [], 0
    for k in range(n):
        t = base + (1 if k < extra else 0)
        res.append(lista[i:i + t])
        i += t
    return res


def tomas_del_bloque(b):
    """Lista de (texto_toma, previous_text, semilla). Una toma = una familia o un grupo de <= 5 unidades."""
    tomas = []
    for sec in b["secciones"]:
        contexto = sec.get("contexto", b["previous_text"])
        if sec["modo"] == "familias":
            grupos = [us for _, us in sec["items"]]
        else:
            grupos = trozos(sec["items"])
        for g in grupos:
            texto = "\n\n".join(texto_tts(u) for u in g)
            tomas.append((texto, contexto, SEMILLA_POR_TOMA.get(" ".join(texto.split()), SEMILLA)))
    return tomas


TOMAS = RAIZ / "trabajo" / "tomas"


def clave_toma(texto, ajustes, previous_text, semilla, next_text=None, voz=None):
    import hashlib
    lista = [MODELO, voz or VOZ_ID, FORMATO, texto, previous_text, semilla, ajustes]
    if next_text is not None:
        lista.append(next_text)
    datos = json.dumps(lista, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(datos.encode("utf-8")).hexdigest()[:16]


def obtener_toma(texto, ajustes, previous_text, semilla, next_text=None, voz=None):
    """Genera una toma corta (o la reutiliza del caché trabajo/tomas/)."""
    TOMAS.mkdir(parents=True, exist_ok=True)
    k = clave_toma(texto, ajustes, previous_text, semilla, next_text, voz)
    wav, js = TOMAS / f"{k}.wav", TOMAS / f"{k}.json"
    if wav.exists() and js.exists():
        d = json.loads(js.read_text(encoding="utf-8"))
        return wav.read_bytes(), d["alineacion"], None, d["peticion"]
    audio, al, aln, cuerpo = tts_con_tiempos(texto, ajustes, previous_text, next_text, semilla=semilla, voz=voz)
    wav.write_bytes(audio)
    js.write_text(json.dumps({"alineacion": al, "peticion": cuerpo}, ensure_ascii=False), encoding="utf-8")
    return audio, al, aln, cuerpo


def toma_compuesta(texto, fuentes, ajustes, previous_text):
    """Arma una toma con unidades tomadas de otras tomas (ver TOMAS_COMPUESTAS en bloques.py).
    Devuelve lo mismo que obtener_toma: (wav_bytes, alineacion, None, descripcion)."""
    import io
    import numpy as np
    import recortar as R
    unidades = texto.split("\n\n")
    assert len(unidades) == len(fuentes)
    pausa = int(0.55 * SR)
    piezas = []
    al = {"characters": [], "character_start_times_seconds": [], "character_end_times_seconds": []}
    t = 0.0
    for k, (u, (src, semilla, idx)) in enumerate(zip(unidades, fuentes)):
        audio, a_src, _, _ = obtener_toma(src, ajustes, previous_text, semilla)
        x = R.leer_wav(io.BytesIO(audio))
        src_us = src.split("\n\n")
        assert len(src_us[idx]) == len(u), (src_us[idx], u)
        pos, spans, inis = 0, [], []
        for v in src_us:
            i = src.index(v, pos)
            spans.append(R.tiempos_alineados(a_src, i, i + len(v)))
            inis.append(i)
            pos = i + len(v)
        ini, fin, li, ld = R.segmentar(R.energia_db(x), spans, 0.0, len(x) / SR)[idx]
        a, b = max(li, ini - 0.06), min(ld, fin + 0.20)
        pieza = x[int(round(a * SR)):int(round(b * SR))]
        if k:
            for _ in range(2):
                al["characters"].append("\n")
                al["character_start_times_seconds"].append(round(t, 3))
                al["character_end_times_seconds"].append(round(t + pausa / SR, 3))
            piezas.append(np.zeros(pausa))
            t += pausa / SR
        dur = len(pieza) / SR
        for j, ch in enumerate(u):
            s0 = a_src["character_start_times_seconds"][inis[idx] + j] - a
            e0 = a_src["character_end_times_seconds"][inis[idx] + j] - a
            al["characters"].append(ch)
            al["character_start_times_seconds"].append(round(t + min(max(s0, 0), dur), 3))
            al["character_end_times_seconds"].append(round(t + min(max(e0, 0), dur), 3))
        piezas.append(pieza)
        t += dur
    y = np.clip(np.round(np.concatenate(piezas) * 32767), -32768, 32767).astype(np.int16)
    buf = io.BytesIO()
    import wave
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y.tobytes())
    desc = {"toma_compuesta": [{"texto_fuente": f[0], "semilla": f[1], "unidad": f[2]} for f in fuentes],
            "voice_settings": ajustes, "previous_text": previous_text, "model_id": MODELO}
    return buf.getvalue(), al, None, desc


def wav_a_muestras(datos):
    import io
    import wave
    with wave.open(io.BytesIO(datos)) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2
        return w.readframes(w.getnframes())


def muestras_a_wav(pcm, ruta):
    import wave
    with wave.open(str(ruta), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm)


def generar_bloque(b, forzar=False):
    CRUDO.mkdir(parents=True, exist_ok=True)
    FUENTE.mkdir(parents=True, exist_ok=True)
    wav, js = CRUDO / f"{b['archivo']}.wav", FUENTE / f"{b['archivo']}.json"
    if wav.exists() and js.exists() and not forzar:
        print(f"[bloque {b['id']}] ya existe, se omite")
        return
    texto, unidades = construir_texto(b)
    print(f"[bloque {b['id']}] {len(texto)} caracteres, {len(unidades)} unidades... ", end="", flush=True)

    if not b.get("por_tomas"):
        # bloque entero en una sola llamada
        audio, alin, alin_norm, cuerpo = tts_con_tiempos(texto, b["voice_settings"], b["previous_text"])
        assert alin["characters"] == list(texto), "la alineación no coincide con el texto"
        wav.write_bytes(audio)
        tomas_meta = [{"texto": texto, "inicio_s": 0.0, "peticion": cuerpo}]
    else:
        # bloque en tomas cortas (familias / grupos de 5) -> render = tomas unidas con pausa fija
        from concurrent.futures import ThreadPoolExecutor
        tomas = tomas_del_bloque(b)
        assert "\n\n".join(t for t, _, _ in tomas) == texto
        with ThreadPoolExecutor(3) as ex:
            def una(tp):
                clave = " ".join(tp[0].split())
                if clave in TOMAS_COMPUESTAS:
                    return toma_compuesta(tp[0], TOMAS_COMPUESTAS[clave], b["voice_settings"], tp[1])
                return obtener_toma(tp[0], b["voice_settings"], tp[1], tp[2])
            res = list(ex.map(una, tomas))
        pcm, alin = b"", {"characters": [], "character_start_times_seconds": [], "character_end_times_seconds": []}
        silencio = b"\x00\x00" * int(PAUSA_ENTRE_TOMAS * SR)
        tomas_meta = []
        for k, ((t, _, _), (audio, al, _, cuerpo)) in enumerate(zip(tomas, res)):
            assert al["characters"] == list(t), f"alineación distinta en toma {k}"
            if k:
                fin_prev = len(pcm) / 2 / SR
                pcm += silencio
                ini = len(pcm) / 2 / SR
                for _ in range(2):  # el "\n\n" entre tomas ocupa la pausa agregada
                    alin["characters"].append("\n")
                    alin["character_start_times_seconds"].append(round(fin_prev, 3))
                    alin["character_end_times_seconds"].append(round(ini, 3))
            off = len(pcm) / 2 / SR
            alin["characters"] += al["characters"]
            alin["character_start_times_seconds"] += [round(s + off, 3) for s in al["character_start_times_seconds"]]
            alin["character_end_times_seconds"] += [round(e + off, 3) for e in al["character_end_times_seconds"]]
            tomas_meta.append({"texto": t, "inicio_s": round(off, 3), "peticion": cuerpo})
            pcm += wav_a_muestras(audio)
        assert alin["characters"] == list(texto)
        muestras_a_wav(pcm, wav)
        alin_norm, cuerpo = None, None

    js.write_text(json.dumps({
        "bloque": b["id"], "nombre": b["nombre"], "voz_id": VOZ_ID, "voz": VOZ_NOMBRE,
        "modelo": MODELO, "formato": FORMATO, "voice_settings": b["voice_settings"],
        "tomas": tomas_meta, "unidades": unidades, "alineacion": alin, "alineacion_normalizada": alin_norm,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"ok ({len(tomas_meta)} toma/s)")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ids = {int(a) for a in args} or {b["id"] for b in BLOQUES}
    for b in BLOQUES:
        if b["id"] in ids:
            generar_bloque(b, forzar="--forzar" in sys.argv)
