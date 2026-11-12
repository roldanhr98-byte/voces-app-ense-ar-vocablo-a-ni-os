"""Dífonos: la transición de un sonido al siguiente (k-a, a-s, s-a...).

Se graban ~300 palabras inventadas con la misma voz y ajustes, y de cada una se cortan sus dífonos
(del medio de un sonido al medio del siguiente). Con ellos el lector arma cualquier palabra que no esté
grabada entera (o que el chico escriba mal), respetando la sílaba acentuada.

  patrón A  "ta C V C o"  (tapápo)  -> C-V acentuada y V acentuada-C
  patrón B  "C V C V ta"  (pepéta)  -> silencio-C, C-V y V-C sin acento
  grupos    "a C C a"     (asta, abra...)
  vocales   "ta V V ta"   (taita, taeta...)
  bordes    "ata", "tate", "tatá", "tatas"...  -> silencio-vocal, vocal-silencio, consonante final
"""
VOC = "aeiou"
CONS = ["p", "b", "t", "d", "k", "g", "f", "Z", "s", "J", "Y", "C", "m", "n", "N", "l", "r", "R"]


def escribir(c, v):
    """Cómo se escribe el sonido c delante de la vocal v."""
    suave = v in "ei"
    return {"k": "qu" if suave else "c", "g": "gu" if suave else "g", "Z": "c" if suave else "z",
            "J": "j", "Y": "y", "C": "ch", "N": "ñ", "R": "rr", "r": "r"}.get(c, c)


def corpus():
    palabras = []
    for c in CONS:
        for v in VOC:
            palabras.append("ta" + escribir(c, v) + v + escribir(c, "o") + "o")         # A: tapápo
    for c in CONS:
        for v in VOC:
            if c == "r":   # la r simple no va a principio de palabra
                palabras.append("a" + "r" + v + "r" + v + "ta")                            # arereta
            else:
                ini = "r" if c == "R" else escribir(c, v)
                palabras.append(ini + v + escribir(c, v) + v + "ta")                     # B: pepeta
    for v1 in VOC:
        for v2 in VOC:
            if v1 != v2:
                palabras.append("t" + v1 + v2 + "ta")                                    # taita, taeta
    grupos = ["pr", "br", "tr", "dr", "cr", "gr", "fr", "pl", "bl", "cl", "gl", "fl"]
    grupos += ["s" + x for x in ["p", "t", "c", "b", "d", "g", "f", "m", "n", "l", "r", "z", "j", "y", "ch"]]
    grupos += ["n" + x for x in ["t", "d", "c", "g", "s", "z", "f", "j", "y", "ch", "l", "r", "m"]] + ["mp", "mb"]
    grupos += ["l" + x for x in ["p", "t", "d", "c", "g", "s", "z", "f", "j", "m", "b", "r", "ch"]]
    grupos += ["r" + x for x in ["p", "t", "d", "c", "g", "s", "z", "f", "j", "m", "n", "l", "b", "y", "ch"]]
    grupos += ["ct", "cz", "x", "bs", "bt", "bd", "pt", "ps", "dm", "gn", "gm", "tm", "tl", "mn"]
    palabras += ["a" + g + "a" for g in grupos]
    for v1 in VOC:
        for v2 in VOC:
            if v1 != v2:
                palabras.append("ta" + v1 + v2 + "tá")                                   # taiotá: vocales sin acento
    palabras += [v + "ta" for v in VOC]                                                  # ata: silencio-vocal
    palabras += [v + "tata" for v in VOC]                                                # etata: vocal inicial sin acento
    palabras += ["tate", "tati", "tatu"]                                                 # vocal final sin acento
    palabras += ["tatá", "taté", "tatí", "tató", "tatú"]                                 # vocal final acentuada
    palabras += ["tatas", "tatan", "tatal", "tatar", "tatad", "tataz", "tataj"]          # consonante final
    return palabras


CONTEXTO = "Ahora vamos a practicar sonidos en español."


def tomas():
    """Tomas de 5 palabras inventadas, separadas por línea en blanco (como las sílabas de la biblioteca)."""
    p = corpus()
    return ["\n\n".join(w[0].upper() + w[1:] + "." for w in p[i:i + 5]) for i in range(0, len(p), 5)]


def generar(voz=None):
    import sys
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from bloques import AJUSTES_NEUTROS, SEMILLA
    from generar import obtener_toma
    ts = tomas()
    print(f"{len(ts)} tomas, {sum(len(t) for t in ts)} caracteres (las que ya están en caché no se cobran)")
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(lambda t: obtener_toma(t, AJUSTES_NEUTROS, CONTEXTO, SEMILLA, voz=voz), ts))
    print("listo")


if __name__ == "__main__":
    generar()


# ----------------------------------------------------------------------------- extracción y síntesis
CORTE_EN_CIERRE = set("ptkC")      # p, t, k, ch: se corta en el silencio del cierre
FUNDIDO_MS = {"v": 12, "c": 3, "o": 8}   # empalme en vocal / en cierre de p,t,k,ch / otros
SUSTITUTOS = {"R": "r", "r": "R", "N": "n", "Y": "J", "C": "t", "Z": "s", "J": "x", "x": "J"}


def clase(s):
    return "v" if s[0] in VOC else ("c" if s[0] in CORTE_EN_CIERRE else "o")


def extraer(voz=None, con_origen=False, refinar_vocales=True):
    """Corta los dífonos de las tomas del caché. Devuelve {clave: (audio, sonido_ini, sonido_fin)}
    (con_origen=True agrega la palabra inventada de la que salió y todos los candidatos)."""
    import io
    import sys
    from pathlib import Path
    import numpy as np
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import recortar as R
    from bloques import AJUSTES_NEUTROS, SEMILLA
    from fonetica import fonemas, clave_difono
    from generar import obtener_toma

    candidatos = {}
    for t in tomas():
        audio, al, _, _ = obtener_toma(t, AJUSTES_NEUTROS, CONTEXTO, SEMILLA, voz=voz)
        x = R.leer_wav(io.BytesIO(audio))
        db = R.energia_db(x)
        st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
        pos = 0
        for w in t.split("\n\n"):
            w = w.rstrip(".")
            i0 = t.index(w, pos)
            pos = i0 + len(w)
            fon = fonemas(w.lower(), posiciones=True)
            # tramos de tiempo de cada sonido
            tramos = []
            for k, (s, ac, a, b) in enumerate(fon):
                t0, t1 = st[i0 + a], en[i0 + b - 1]
                if k > 0 and fon[k - 1][2] == a:          # x = k + s: comparten letra
                    m = (t0 + t1) / 2
                    tramos[-1] = (tramos[-1][0], m)
                    t0 = m
                tramos.append((t0, t1))
            # inicio y fin de voz de la palabra
            wa, wb = R.t2f(st[i0] - 0.15), R.t2f(en[i0 + len(w) - 1] + 0.3)
            seg = db[max(0, wa):wb]
            act = np.where(seg > seg.max() - 40)[0]
            v_ini = max(0.0, (max(0, wa) + act[0]) * R.HOP - 0.010)
            v_fin = (max(0, wa) + act[-1] + 1) * R.HOP + 0.030
            # gain: voz activa de la palabra a -20 dBFS
            pal = x[int(v_ini * R.SR):int(v_fin * R.SR)]
            dbp = R.energia_db(pal)
            act_db = dbp[dbp > dbp.max() - 25]
            g = 10 ** ((-20 - 10 * np.log10(np.mean(10 ** (act_db / 10)))) / 20)
            # punto de corte de cada sonido
            cortes = []
            for (s, ac, a, b), (t0, t1) in zip(fon, tramos):
                if s in CORTE_EN_CIERRE:
                    fa = max(0, R.t2f(t0 - 0.02))
                    fb = min(len(db), max(fa + 1, R.t2f(t0 + 0.7 * (t1 - t0))))
                    cortes.append((fa + int(np.argmin(db[fa:fb]))) * R.HOP + 0.0025)
                elif refinar_vocales and s in VOC:
                    # centro de la zona de máxima energía de la vocal (su núcleo), no el centro de la alineación
                    fa = max(0, R.t2f(t0 - 0.015))
                    fb = min(len(db), max(fa + 1, R.t2f(t1 + 0.015)))
                    seg = db[fa:fb]
                    meseta = np.where(seg >= seg.max() - 3)[0]
                    cortes.append((fa + (meseta[0] + meseta[-1]) / 2) * R.HOP)
                else:
                    cortes.append((t0 + t1) / 2)
            seq = [("_", False, v_ini)] + [(s, ac, c) for (s, ac, _, _), c in zip(fon, cortes)] + [("_", False, v_fin)]
            for (s1, a1, c1), (s2, a2, c2) in zip(seq, seq[1:]):
                if c2 - c1 < 0.02:
                    continue
                y = x[int(c1 * R.SR):int(c2 * R.SR)] * g
                candidatos.setdefault(clave_difono((s1, a1), (s2, a2)), []).append((y, s1, s2, w))
    inventario = {}
    for k, cs in candidatos.items():
        durs = np.array([len(c[0]) for c in cs])
        elegido = cs[int(np.argmin(np.abs(durs - np.median(durs))))]
        inventario[k] = (elegido + (cs,)) if con_origen else elegido[:3]
    return inventario


def _buscar(inv, s1, a1, s2, a2):
    from fonetica import clave_difono
    for x1, x2 in [(a1, a2), (not a1, a2), (a1, not a2), (not a1, not a2)]:
        k = clave_difono((s1, x1), (s2, x2))
        if k in inv:
            return inv[k]
    for t1, t2 in [(SUSTITUTOS.get(s1, s1), s2), (s1, SUSTITUTOS.get(s2, s2))]:
        for x1, x2 in [(a1, a2), (not a1, a2), (a1, not a2)]:
            k = clave_difono((t1, x1), (t2, x2))
            if k in inv:
                return inv[k]
    return None


def sintetizar(inv, fon, sr=48000):
    """[(sonido, acentuado)] -> audio, uniendo dífonos con fundido cruzado en el sonido compartido."""
    import numpy as np
    seq = [("_", False)] + list(fon) + [("_", False)]
    piezas = []
    for (s1, a1), (s2, a2) in zip(seq, seq[1:]):
        d = _buscar(inv, s1, a1, s2, a2)
        if d is not None:
            piezas.append(d)
    if not piezas:
        return np.zeros(0)
    out = piezas[0][0].copy()
    for y, s_ini, _ in piezas[1:]:
        n = min(int(FUNDIDO_MS[clase(s_ini)] / 1000 * sr), len(out), len(y))
        if n > 0:
            ang = np.linspace(0, np.pi / 2, n)
            mezcla = out[-n:] * np.cos(ang) + y[:n] * np.sin(ang)
            out = np.concatenate([out[:-n], mezcla, y[n:]])
        else:
            out = np.concatenate([out, y])
    return out
