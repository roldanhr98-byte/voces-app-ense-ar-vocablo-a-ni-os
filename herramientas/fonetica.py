"""Texto escrito -> sonidos del español (voz de España), con la sílaba acentuada.

Símbolos (un carácter por sonido):
  vocales  a e i o u
  p b t d k g f s m n l
  Z = z/ce/ci (θ)   J = j/ge/gi (x)   Y = y/ll (ʝ)   C = ch   N = ñ   r = r simple   R = rr / r inicial

Las mismas reglas están en lector.js (la app). Si se cambia algo acá, cambiarlo también allá.
"""
import re
import unicodedata

VOCALES = "aeiouáéíóúü"
FUERTES = "aeoáéíóú"   # a, e, o y cualquier vocal con tilde: forman hiato entre sí
INSEPARABLES = {"pr", "br", "tr", "dr", "cr", "kr", "gr", "fr", "pl", "bl", "cl", "kl", "gl", "fl"}
TILDE = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u"}
OCLUSIVAS_SORDAS = set("ptkC")


def sin_tildes(t):
    t = t.replace("ñ", "\0")
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    return t.replace("\0", "ñ")


def silabear(palabra):
    """Separa una palabra escrita en sílabas (reglas del español)."""
    w = palabra.lower()
    u, i = [], 0
    while i < len(w):
        if w[i:i + 2] in ("ch", "ll", "rr"):
            u.append(w[i:i + 2])
            i += 2
        elif w[i:i + 2] == "qu" or (w[i:i + 2] in ("gu", "gü") and i + 2 < len(w) and w[i + 2] in "eiéí"):
            u.append(w[i:i + 2])
            i += 2
        else:
            u.append(w[i])
            i += 1

    def es_vocal(x):
        return len(x) == 1 and x in VOCALES

    sil, actual = [], ""
    k = 0
    while k < len(u):
        x = u[k]
        if es_vocal(x):
            actual += x
            if k + 1 < len(u) and es_vocal(u[k + 1]):
                y = u[k + 1]
                hiato = (x in FUERTES and y in FUERTES) or x in "íú" or y in "íú"
                if hiato:
                    sil.append(actual)
                    actual = ""
            k += 1
            continue
        j = k
        while j < len(u) and not es_vocal(u[j]):
            j += 1
        grupo = u[k:j]
        if j == len(u) or not actual:
            actual += "".join(grupo)
        else:
            if len(grupo) == 1:
                corte = 0
            elif len(grupo) == 2:
                corte = 0 if "".join(grupo) in INSEPARABLES else 1
            elif len(grupo) == 3:
                corte = 1 if "".join(grupo[1:]) in INSEPARABLES else 2
            else:
                corte = 2
            actual += "".join(grupo[:corte])
            sil.append(actual)
            actual = "".join(grupo[corte:])
        k = j
    if actual:
        sil.append(actual)
    res = []
    for s in sil:
        if res and not any(c in VOCALES for c in s):
            res[-1] += s
        else:
            res.append(s)
    return res


def posicion_acento(palabra):
    """Índice (en la palabra escrita) de la vocal acentuada, o -1 si no tiene vocales."""
    w = palabra.lower()
    for i, c in enumerate(w):
        if c in "áéíóú":
            return i
    sil = silabear(w)
    if not sil:
        return -1
    base = sin_tildes(w)
    llana = base[-1] in "aeiouns" if base else True
    k = len(sil) - 2 if (llana and len(sil) > 1) else len(sil) - 1
    ini = sum(len(s) for s in sil[:k])
    s = sil[k]
    vocs = [j for j, c in enumerate(s) if c in "aeiou" and not (c == "u" and j > 0 and s[j - 1] in "qg"
                                                                  and j + 1 < len(s) and s[j + 1] in "ei")]
    if not vocs:
        return -1
    fuertes = [j for j in vocs if s[j] in "aeo"]
    j = fuertes[0] if fuertes else vocs[-1]
    return ini + j


def fonemas(palabra, acentuada=True, posiciones=False):
    """Lista de (sonido, acentuado) para una palabra. acentuada=False para palabras átonas (la, de, mi...).
    Con posiciones=True devuelve (sonido, acentuado, i_ini, i_fin) con el tramo de letras de cada sonido."""
    w = palabra.lower()
    acento = posicion_acento(w) if acentuada else -1
    res = []
    i = 0

    def pon(s, a, ini, fin):
        res.append((s, a, ini, fin))

    while i < len(w):
        c = w[i]
        sig = w[i + 1] if i + 1 < len(w) else ""
        sig2 = w[i + 2] if i + 2 < len(w) else ""
        if w.startswith("ch", i):
            pon("C", False, i, i + 2); i += 2; continue
        if w.startswith("ll", i):
            pon("Y", False, i, i + 2); i += 2; continue
        if w.startswith("rr", i):
            pon("R", False, i, i + 2); i += 2; continue
        if c == "q":
            n = 2 if sig == "u" else 1
            pon("k", False, i, i + n); i += n; continue
        if c == "g" and sig == "u" and sig2 and sig2 in "eiéí":
            pon("g", False, i, i + 2); i += 2; continue
        if c == "g" and sig == "ü":
            pon("g", False, i, i + 1); pon("u", False, i + 1, i + 2); i += 2; continue
        if c in VOCALES:
            pon(TILDE.get(c, c), i == acento, i, i + 1); i += 1; continue
        if c == "c":
            pon("Z" if sig and sig in "eiéí" else "k", False, i, i + 1)
        elif c == "z":
            pon("Z", False, i, i + 1)
        elif c == "g":
            pon("J" if sig and sig in "eiéí" else "g", False, i, i + 1)
        elif c == "j":
            pon("J", False, i, i + 1)
        elif c == "h":
            pass
        elif c == "v":
            pon("b", False, i, i + 1)
        elif c == "w":
            pon("u", False, i, i + 1)
        elif c == "x":
            if i == 0:
                pon("s", False, i, i + 1)
            else:
                pon("k", False, i, i + 1); pon("s", False, i, i + 1)
        elif c == "y":
            if i == len(w) - 1 or not (sig in VOCALES):
                pon("i", i == acento, i, i + 1)
            else:
                pon("Y", False, i, i + 1)
        elif c == "ñ":
            pon("N", False, i, i + 1)
        elif c == "r":
            pon("R" if i == 0 or w[i - 1] in "nls" else "r", False, i, i + 1)
        elif c == "k":
            pon("k", False, i, i + 1)
        elif c in "pbtdfsmnl":
            pon(c, False, i, i + 1)
        i += 1
    return res if posiciones else [(s, a) for s, a, _, _ in res]


def clave_fonetica(w):
    """Dos palabras con la misma clave suenan igual (b=v, h muda, ll=y, c/qu/k...). Respeta z/s (voz de España)."""
    t = sin_tildes(w.lower().replace("gü", "gw"))
    for a, b in [("ch", "C"), ("ll", "y"), ("rr", "R"), ("qu", "k"), ("gu(?=[ei])", "G"), ("g(?=[ei])", "j"),
                 ("G", "g"), ("c(?=[ei])", "z"), ("c", "k"), ("h", ""), ("v", "b"), ("w", "u"), ("x", "ks"),
                 ("y$", "i"), ("^r", "R")]:
        t = re.sub(a, b, t)
    return t


def normalizar_silaba(s):
    """Escribe la sílaba como está en el inventario: sin tildes ni h muda, ge->je, ze->ce, y final->i."""
    t = sin_tildes(s.lower()).replace("ch", "C").replace("h", "").replace("C", "ch")
    t = re.sub(r"^g(?=[ei])", "j", t)
    t = t.replace("gü", "gu").replace("ü", "u")
    t = re.sub(r"^z(?=[ei])", "c", t)
    if len(t) > 1 and t.endswith("y"):
        t = t[:-1] + "i"
    return t


def difonos_de(fon):
    """[(sonido, acentuado)] -> claves de dífonos, con silencio "_" al principio y al final."""
    seq = [("_", False)] + list(fon) + [("_", False)]
    return [clave_difono(a, b) for a, b in zip(seq, seq[1:])]


def clave_difono(a, b):
    def k(x):
        s, ac = x
        return s + ("1" if ac and s in "aeiou" else "")
    return f"{k(a)}-{k(b)}"
