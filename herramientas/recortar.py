"""Recorta cada bloque en unidades usando la alineación por carácter de ElevenLabs
refinada con detección de silencio, y organiza todo en carpetas.

  python3 herramientas/recortar.py            -> genera ./audios/ (+ manifest.json / manifest.csv)
"""
import csv
import json
import re
import shutil
import sys
import unicodedata
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bloques import BLOQUES  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
CRUDO = RAIZ / "trabajo" / "crudo"
FUENTE = RAIZ / "fuente"
SALIDA = RAIZ / "audios"

SR = 48000
HOP = 0.005            # resolución del análisis de energía (5 ms)
UMBRAL_DB = -55.0      # por debajo = silencio (el fondo de ElevenLabs está en ~ -88 dBFS)
PRE = 0.040            # margen antes del inicio de la voz
POST = 0.120           # margen después del final de la voz (cola natural)
FADE_IN = 0.008
FADE_OUT = 0.030
OBJETIVO_RMS_DB = -20.0  # nivel de voz activa de cada clip (normalización por clip)
TECHO_PICO_DB = -1.0     # pico máximo de cada clip


# ----------------------------------------------------------------------------- utilidades
def slug(t):
    t = t.lower().replace("ñ", "ny")
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]+", "_", t)
    return t.strip("_")


def leer_wav(p):
    with wave.open(p if hasattr(p, "read") else str(p)) as w:
        assert w.getframerate() == SR and w.getnchannels() == 1 and w.getsampwidth() == 2
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768.0


def escribir_wav(p, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    y = np.clip(np.round(x * 32767.0), -32768, 32767).astype(np.int16)
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(y.tobytes())


def energia_db(x):
    hop, win = int(HOP * SR), int(2 * HOP * SR)
    n = max(1, (len(x) - win) // hop + 1)
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    rms = np.sqrt((x[idx] ** 2).mean(axis=1))
    return 20 * np.log10(rms + 1e-10)


def corridas_silencio(db, f0, f1):
    """Corridas [a, b) de frames silenciosos dentro de [f0, f1)."""
    sil = db[f0:f1] < UMBRAL_DB
    res, i = [], 0
    while i < len(sil):
        if sil[i]:
            j = i
            while j < len(sil) and sil[j]:
                j += 1
            res.append((f0 + i, f0 + j))
            i = j
        else:
            i += 1
    return res


def t2f(t):
    return int(round(t / HOP))


def f2t(f):
    return f * HOP


def tiempos_alineados(alin, ini, fin):
    """Inicio de la primera letra y final de la última letra (ignora signos)."""
    chars = alin["characters"]
    letras = [k for k in range(ini, fin) if chars[k].isalnum()]
    return alin["character_start_times_seconds"][letras[0]], alin["character_end_times_seconds"][letras[-1]]


def segmentar(db, spans, t_lo, t_hi):
    """Para una secuencia de unidades alineadas devuelve, por unidad:
    (inicio_voz, fin_voz, limite_izq, limite_der) en segundos."""
    nf = len(db)
    f_lo, f_hi = t2f(t_lo), min(nf, t2f(t_hi))
    n = len(spans)
    ini_voz, fin_voz = [0.0] * n, [0.0] * n
    lim_izq, lim_der = [t_lo] * n, [t_hi] * n

    # inicio de la primera unidad
    s0 = spans[0][0]
    a, b = max(f_lo, t2f(s0 - 0.6)), min(f_hi, t2f(s0 + 0.15))
    runs = corridas_silencio(db, a, b)
    ini_voz[0] = f2t(runs[-1][1]) if runs else f2t(a)
    if runs and runs[-1][1] == b:  # todo silencio en la ventana: buscar la voz hacia adelante
        k = b
        while k < f_hi and db[k] < UMBRAL_DB:
            k += 1
        ini_voz[0] = f2t(k)

    # fronteras entre unidades
    for i in range(n - 1):
        e_i, s_j = spans[i][1], spans[i + 1][0]
        a, b = max(f_lo, t2f(min(e_i, s_j) - 0.15)), min(f_hi, t2f(max(e_i, s_j) + 0.15))
        runs = [r for r in corridas_silencio(db, a, b) if r[1] - r[0] >= 2]
        if runs:
            r = max(runs, key=lambda r: r[1] - r[0])
            fin_voz[i], ini_voz[i + 1] = f2t(r[0]), f2t(r[1])
            medio = f2t((r[0] + r[1]) / 2)
        else:
            m = a + int(np.argmin(db[a:b]))
            fin_voz[i] = ini_voz[i + 1] = medio = f2t(m)
        lim_der[i], lim_izq[i + 1] = medio, medio

    # final de la última unidad
    e_n = spans[-1][1]
    a, b = max(f_lo, t2f(e_n - 0.15)), min(f_hi, t2f(e_n + 1.0))
    runs = [r for r in corridas_silencio(db, a, b) if r[1] - r[0] >= 12 or r[1] == b]
    fin_voz[-1] = f2t(runs[0][0]) if runs else f2t(b)
    return list(zip(ini_voz, fin_voz, lim_izq, lim_der))


def extraer(x, ini_voz, fin_voz, lim_izq, lim_der):
    a_t = max(lim_izq, ini_voz - PRE)
    b_t = min(lim_der, fin_voz + POST)
    a, b = int(round(a_t * SR)), int(round(b_t * SR))
    y = x[max(0, a):min(len(x), b)].copy()
    falta = int(round((ini_voz - PRE) * SR))
    if falta < 0 and lim_izq <= 0:  # la voz arranca en el sample 0: completar el margen con silencio
        y = np.concatenate([np.zeros(-falta), y])
    return y, a_t, b_t


def finalizar(y):
    """Fundidos en los bordes + normalización de nivel por clip."""
    y = y.copy()
    fi, fo = int(FADE_IN * SR), int(FADE_OUT * SR)
    y[:fi] *= np.linspace(0, 1, fi)
    y[-fo:] *= np.linspace(1, 0, fo)
    db = energia_db(y)
    activos = db[db > db.max() - 25]
    rms_activo = 10 * np.log10(np.mean(10 ** (activos / 10)))
    pico = 20 * np.log10(np.abs(y).max() + 1e-12)
    ganancia = min(OBJETIVO_RMS_DB - rms_activo, TECHO_PICO_DB - pico)
    return y * 10 ** (ganancia / 20), ganancia


# ----------------------------------------------------------------------------- principal
def main():
    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    manifiesto = []

    def guardar(rel, y, meta):
        y2, g = finalizar(y)
        escribir_wav(SALIDA / rel, y2)
        meta.update(archivo=rel, duracion_ms=int(round(len(y2) / SR * 1000)), ganancia_db=round(g, 2),
                    orden=len(manifiesto))
        manifiesto.append(meta)

    for b in BLOQUES:
        datos = json.loads((FUENTE / f"{b['archivo']}.json").read_text(encoding="utf-8"))
        x = leer_wav(CRUDO / f"{b['archivo']}.wav")
        db = energia_db(x)
        alin, unidades = datos["alineacion"], datos["unidades"]
        dur = len(x) / SR

        # render completo del bloque (misma ganancia para todo el bloque)
        guardar(f"00_renders_bloques_completos/{b['archivo']}.wav", x,
                dict(tipo="render_bloque", bloque=b["id"], texto=b["nombre"]))

        # secuencia principal (unidades de primer nivel)
        top = [u for u in unidades if not u.get("dentro_de_parrafo")]
        spans = [tiempos_alineados(alin, u["ini"], u["fin"]) for u in top]
        segs = segmentar(db, spans, 0.0, dur)
        for u, sp, sg in zip(top, spans, segs):
            u["_seg"], u["_span"] = sg, sp
        # oraciones dentro de cada párrafo
        for u in top:
            if u.get("es_parrafo"):
                hijas = [h for h in unidades if h.get("dentro_de_parrafo") and h["parrafo"] == u["parrafo"]]
                sp_h = [tiempos_alineados(alin, h["ini"], h["fin"]) for h in hijas]
                ini_p, fin_p, li, ld = u["_seg"]
                sg_h = segmentar(db, sp_h, max(li, ini_p - 0.05), min(ld, fin_p + 0.2))
                sg_h[0] = (ini_p, sg_h[0][1], li, sg_h[0][3])
                sg_h[-1] = (sg_h[-1][0], fin_p, sg_h[-1][2], ld)
                for h, s, g in zip(hijas, sp_h, sg_h):
                    h["_seg"], h["_span"] = g, s

        secciones = {s["id"]: s for s in b["secciones"]}
        for u in unidades:
            sec = secciones[u["seccion"]]
            carpeta = sec["carpeta"]
            if sec["modo"] == "familias":
                rel = (f"{carpeta}/{slug(u['unidad'])}.wav" if sec.get("familia_en_raiz")
                       else f"{carpeta}/{u['grupo']}/{slug(u['unidad'])}.wav")
            elif sec["modo"] == "plano":
                rel = f"{carpeta}/{slug(u['unidad'])}.wav"
            elif sec["modo"] == "frases":
                rel = f"{carpeta}/{u['indice']:02d}_{slug(u['unidad'])[:60].rstrip('_')}.wav"
            elif u.get("es_parrafo"):
                rel = f"{carpeta}/parrafo_{u['parrafo']}.wav"
            else:
                rel = (f"{carpeta}/oraciones/p{u['parrafo']}_{u['oracion']:02d}_"
                       f"{slug(u['unidad'])[:55].rstrip('_')}.wav")
            meta = dict(tipo="parrafo" if u.get("es_parrafo") else "unidad", bloque=b["id"],
                        seccion=u["seccion"], grupo=u.get("grupo"), texto=u["unidad"])
            y, a_t, b_t = extraer(x, *u["_seg"])
            meta.update(inicio_en_render_s=round(a_t, 3), fin_en_render_s=round(b_t, 3))
            guardar(rel, y, meta)

        # familias completas (ej. "Ba. Be. Bi. Bo. Bu.") recortadas de la toma continua
        for sec in b["secciones"]:
            if sec["modo"] != "familias":
                continue
            for grupo, us in sec["items"]:
                fam = [u for u in unidades if u["seccion"] == sec["id"] and u.get("grupo") == grupo]
                y, a_t, b_t = extraer(x, fam[0]["_seg"][0], fam[-1]["_seg"][1],
                                      fam[0]["_seg"][2], fam[-1]["_seg"][3])
                nombre = (f"{sec['carpeta']}/{grupo}_" + "_".join(slug(u["unidad"]) for u in fam) + ".wav"
                          if sec.get("familia_en_raiz") else f"{sec['carpeta']}/{grupo}/familia_{grupo}.wav")
                meta = dict(tipo="familia", bloque=b["id"], seccion=sec["id"], grupo=grupo,
                            texto=". ".join(u["unidad"] for u in fam) + ".")
                meta.update(inicio_en_render_s=round(a_t, 3), fin_en_render_s=round(b_t, 3))
                guardar(nombre, y, meta)

    manifiesto.sort(key=lambda m: m["orden"])
    (SALIDA / "manifest.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=1), encoding="utf-8")
    campos = ["archivo", "texto", "tipo", "bloque", "seccion", "grupo", "duracion_ms", "inicio_en_render_s",
              "fin_en_render_s"]
    with open(SALIDA / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos, extrasaction="ignore")
        w.writeheader()
        w.writerows(manifiesto)
    print(f"{len(manifiesto)} archivos en {SALIDA}")


if __name__ == "__main__":
    main()
