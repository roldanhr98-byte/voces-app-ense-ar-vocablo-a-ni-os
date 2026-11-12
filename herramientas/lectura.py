"""Paquete 2: lectura encadenada.

Sirve para dos secciones de la app:
  1. Unir sílabas:  "va - ca" -> "vaca" -> "la - va - ca" -> "la vaca come pasto"
  2. Armar oraciones con palabras en cualquier orden: la app lee lo que armó el chico, fluido.

No se graban frases: se graban PALABRAS sueltas preparadas para encadenarse, en dos versiones:
  - medio: la palabra tal como suena dentro de una oración (corta, sin caída final).
           Se graba "<palabra> todo" y se corta en el silencio de la "t", así la voz no la
           trata como fin de frase (las palabras chicas como "me", "de", "la" quedan cortas).
  - final: la palabra con cierre de oración ("<palabra>.").
Si una palabra no está grabada (o el chico la escribe mal), el lector la arma con sílabas.

  python3 herramientas/lectura.py generar     # pide a ElevenLabs lo que falte (usa caché)
  python3 herramientas/lectura.py armar       # corta, normaliza, copia sílabas, manifest, ejemplos
  python3 herramientas/lectura.py verificar   # transcribe los ejemplos y las palabras finales
  python3 herramientas/lectura.py zip
"""
import io
import json
import re
import shutil
import sys
import unicodedata
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import recortar as R  # noqa: E402
from bloques import AJUSTES_NEUTROS, SEMILLA, VOZ_ID, VOZ_NOMBRE  # noqa: E402
from generar import obtener_toma  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "audios_lectura"
BIBLIOTECA = RAIZ / "audios"
NOMBRE_ZIP = "lectura_encadenada_martin_osborne"

CONTEXTO = "Ella dijo que"   # previous_text: la palabra se dice a mitad de oración
PORTADOR = "todo"            # palabra que sigue y se corta (su "t" deja un silencio limpio)

# ----------------------------------------------------------------------------- vocabulario
FUNCION = ("el la los las un una unos unas mi mis tu tus su sus a al de del en con por para sin sobre "
           "y o pero que porque me te se le lo").split()
CONTENIDO = {
    "pronombres": "yo tú él ella nosotros ellos",
    "personas": "mamá papá tío tía abuelo abuela hermano hermana amigo amiga niño niña maestra maestro bebé",
    "animales": "vaca perro gato pato pájaro caballo pez ratón conejo oso león mono oveja pollito mariposa",
    "lugares": "casa escuela parque playa jardín campo río mar montaña ciudad calle tienda",
    "cosas": ("pasto sol luna agua flor árbol pelota libro juguete mesa cama pan leche fruta manzana helado "
              "comida carro bicicleta"),
    "verbos": ("es está son están soy estoy tiene tengo va voy vamos come como bebe juega juego corre salta "
               "duerme lee canta mira quiere quiero vive nada vuela camina"),
    "adjetivos": ("grande pequeño pequeña bonito bonita feliz contento contenta rojo azul verde amarillo "
                  "blanco negro alto rápido nuevo mucho muchos muy más"),
    "tiempo_y_otros": "hoy ayer mañana ahora siempre aquí allá no sí vacaciones día noche tarde también todos",
}
CATEGORIA = {w: "funcion" for w in FUNCION}
for cat, ws in CONTENIDO.items():
    for w in ws.split():
        CATEGORIA[w] = cat
PALABRAS = list(CATEGORIA)


# ----------------------------------------------------------------------------- texto
def sin_tildes(t):
    t = t.replace("ñ", "\0")
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    return t.replace("\0", "ñ")


def clave_fonetica(w):
    """Dos palabras con la misma clave suenan igual (b=v, h muda, ll=y, c/qu/k...). Respeta z/s (voz de España)."""
    t = sin_tildes(w.lower().replace("gü", "gw"))
    for a, b in [("ch", "C"), ("ll", "y"), ("rr", "R"), ("qu", "k"), ("gu(?=[ei])", "G"), ("g(?=[ei])", "j"),
                 ("G", "g"), ("c(?=[ei])", "z"), ("c", "k"), ("h", ""), ("v", "b"), ("w", "u"), ("x", "ks"),
                 ("y$", "i"), ("^r", "R")]:
        t = re.sub(a, b, t)
    return t


def nombre_archivo(w):
    return R.slug(w) + ("_tilde" if w != sin_tildes(w) and sin_tildes(w) in PALABRAS else "")


VOCALES = "aeiouáéíóúü"
FUERTES = "aeoáéíóú"   # a, e, o y cualquier vocal con tilde: forman hiato entre sí
INSEPARABLES = {"pr", "br", "tr", "dr", "cr", "kr", "gr", "fr", "pl", "bl", "cl", "kl", "gl", "fl"}


def silabear(palabra):
    """Separa una palabra escrita en sílabas (reglas del español)."""
    w = palabra.lower()
    # unidades: dígrafos como una sola consonante
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

    # núcleos: grupos de vocales (separando hiatos)
    sil, actual = [], ""
    k = 0
    while k < len(u):
        x = u[k]
        if es_vocal(x):
            actual += x
            # ¿hiato con la siguiente vocal?
            if k + 1 < len(u) and es_vocal(u[k + 1]):
                y = u[k + 1]
                hiato = (x in FUERTES and y in FUERTES) or x in "íú" or y in "íú"
                if hiato:
                    sil.append(actual)
                    actual = ""
            k += 1
            continue
        # consonantes entre vocales
        j = k
        while j < len(u) and not es_vocal(u[j]):
            j += 1
        grupo = u[k:j]
        if j == len(u) or not actual:  # al final de la palabra o al inicio
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
    # sílaba sin vocal (raro) se pega a la anterior
    res = []
    for s in sil:
        if res and not any(c in VOCALES for c in s):
            res[-1] += s
        else:
            res.append(s)
    return res


def normalizar_silaba(s):
    """Escribe la sílaba como está en el inventario: sin tildes ni h muda, ge->je, ze->ce, y final->i."""
    t = sin_tildes(s.lower()).replace("ch", "C").replace("h", "").replace("C", "ch")
    t = re.sub(r"^g(?=[ei])", "j", t)
    t = t.replace("gü", "gu").replace("ü", "u")
    t = re.sub(r"^z(?=[ei])", "c", t)
    if len(t) > 1 and t.endswith("y"):
        t = t[:-1] + "i"
    return t


# ----------------------------------------------------------------------------- generación
def peticiones(voz=VOZ_ID):
    p = [(f"{w} {PORTADOR}", CONTEXTO) for w in PALABRAS]
    p += [(f"{w}.", CONTEXTO) for w in PALABRAS if CATEGORIA[w] != "funcion"]
    return p


def generar(voz=VOZ_ID):
    ps = peticiones(voz)
    print(f"{len(ps)} peticiones, {sum(len(t) for t, _ in ps)} caracteres (las que ya están en caché no se cobran)")
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(lambda tp: obtener_toma(tp[0], AJUSTES_NEUTROS, tp[1], SEMILLA, voz=voz), ps))
    print("listo")


def _wav(audio):
    return R.leer_wav(io.BytesIO(audio))


def _bordes(y, fi=0.004, fo=0.010):
    y = y.copy()
    a, b = int(fi * R.SR), int(fo * R.SR)
    y[:a] *= np.linspace(0, 1, a)
    y[-b:] *= np.linspace(1, 0, b)
    return y


def cortar_medio(w, voz=VOZ_ID):
    audio, al, _, _ = obtener_toma(f"{w} {PORTADOR}", AJUSTES_NEUTROS, CONTEXTO, SEMILLA, voz=voz)
    x = _wav(audio)
    db = R.energia_db(x)
    fin_w = al["character_end_times_seconds"][len(w) - 1]
    ini_t = al["character_start_times_seconds"][len(w) + 1]
    a, b = R.t2f(min(fin_w, ini_t) - 0.05), R.t2f(max(fin_w, ini_t) + 0.06)
    corte = a + int(np.argmin(db[a:b]))
    act = np.where(db[:corte] > db.max() - 40)[0]
    ini = max(0, act[0] - 2)
    profundidad = float(db[a:b].max() - db[corte])  # cuánto baja la energía en el corte (silencio de la t)
    return _bordes(x[int(ini * R.HOP * R.SR):int((corte + 1) * R.HOP * R.SR)]), profundidad


def cortar_final(w, voz=VOZ_ID):
    x = _wav(obtener_toma(f"{w}.", AJUSTES_NEUTROS, CONTEXTO, SEMILLA, voz=voz)[0])
    db = R.energia_db(x)
    act = np.where(db > db.max() - 40)[0]
    y = x[int(max(0, act[0] - 2) * R.HOP * R.SR):int(min(len(db), act[-1] + 8) * R.HOP * R.SR)]
    return _bordes(y, fo=0.030)


def recorte_justo(y, pre=0.010, post=0.040):
    db = R.energia_db(y)
    act = np.where(db > db.max() - 40)[0]
    a = max(0, int((act[0] * R.HOP - pre) * R.SR))
    b = min(len(y), int(((act[-1] + 2) * R.HOP + post) * R.SR))
    return _bordes(y[a:b], fo=0.020)


def rms_activo(y):
    db = R.energia_db(y)
    act = db[db > db.max() - 25]
    return 10 * np.log10(np.mean(10 ** (act / 10)))


# ----------------------------------------------------------------------------- lector (igual que lector.js)
PARAMS = {
    "pausa_entre_palabras_ms": 10,
    "fundido_ms": 6,
    "pausa_coma_ms": 250,
    "pausa_punto_ms": 450,
    "pausa_entre_silabas_ms": 300,
    "pausa_entre_pasos_ms": 700,
    "solape_coda_ms": 30,
    "fusion_recorte": 0.35,
}


class Lector:
    def __init__(self, base=SALIDA):
        self.base = Path(base)
        self.m = json.loads((self.base / "manifest_lectura.json").read_text(encoding="utf-8"))
        self.cache = {}
        self.por_tilde = {}
        self.por_clave = {}
        for w, d in self.m["palabras"].items():
            self.por_tilde.setdefault(sin_tildes(w), w)
            self.por_clave.setdefault(d["clave"], w)

    def _a(self, rel):
        if rel not in self.cache:
            self.cache[rel] = R.leer_wav(self.base / rel)
        return self.cache[rel]

    def buscar(self, w):
        w = w.lower()
        for k, d in ((w, None), (sin_tildes(w), self.por_tilde), (clave_fonetica(w), self.por_clave)):
            pal = k if d is None else d.get(k)
            if pal in self.m["palabras"]:
                return pal
        return None

    def silaba(self, s):
        """Lista de (audio, solape_seg) para una sílaba escrita."""
        inv = self.m["silabas"]
        t = normalizar_silaba(s)
        if t in inv:
            return [(self._a(inv[t]), 0.0)]
        m = re.match(r"^([^aeiou]*)([aeiou]+)([^aeiou]*)$", t)
        if not m:
            return []
        ataque, nucleo, coda = m.groups()
        piezas = []
        if ataque + nucleo in inv:
            piezas.append((self._a(inv[ataque + nucleo]), 0.0))
        else:
            if ataque + nucleo[0] in inv:
                piezas.append((self._a(inv[ataque + nucleo[0]]), 0.0))
            resto = nucleo[1:]
            if resto:
                clave = resto if resto in inv else resto[-1]
                if clave in inv:
                    piezas.append((self._a(inv[clave]), PARAMS["solape_coda_ms"] / 1000))
        if coda:
            vc = nucleo[-1] + coda[0]
            if vc in inv:
                piezas.append((self._a(inv[vc]), PARAMS["solape_coda_ms"] / 1000))
        return piezas

    def _palabra_audio(self, w, final):
        pal = self.buscar(w)
        if pal:
            d = self.m["palabras"][pal]
            return [(self._a(d["final"] if final and d.get("final") else d["medio"]), 0.0)]
        piezas = []
        for s in silabear(w):
            piezas += self.silaba(s)
        return piezas

    @staticmethod
    def unir(piezas, pausa):
        sr = R.SR
        f = int(PARAMS["fundido_ms"] / 1000 * sr)
        out = np.zeros(0)
        ultimo = 0
        for k, (y, solape) in enumerate(piezas):
            if k == 0:
                out = y.copy()
                ultimo = len(y)
                continue
            if solape > 0:  # fusión: la vocal compartida suena una sola vez ("pa" + "an" -> "pan")
                fr = PARAMS["fusion_recorte"]
                out = out[:len(out) - int(fr * ultimo)]
                y = y[int(fr * len(y)):]
                n = min(int(solape * sr), len(out), len(y))
                y = y.copy()
                out[-n:] *= np.linspace(1, 0, n)
                y[:n] *= np.linspace(0, 1, n)
                out[-n:] += y[:n]
                out = np.concatenate([out, y[n:]])
            else:
                out = np.concatenate([out, np.zeros(int(pausa * sr)), y])
            ultimo = len(y)
        if len(out) > f:
            out[-f:] *= np.linspace(1, 0, f)
        return out

    def oracion(self, texto):
        tokens = re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ]+|[.,;:!?¡¿]", texto)
        palabras = [t for t in tokens if t[0].isalnum()]
        bloques, piezas, vistas = [], [], 0
        for t in tokens:
            if not t[0].isalnum():
                if piezas and t in ",;:":
                    piezas.append((np.zeros(int(PARAMS["pausa_coma_ms"] / 1000 * R.SR)), 0.0))
                elif piezas and t in ".!?":
                    piezas.append((np.zeros(int(PARAMS["pausa_punto_ms"] / 1000 * R.SR)), 0.0))
                continue
            vistas += 1
            es_final = vistas == len(palabras)
            pw = self._palabra_audio(t, es_final)
            if pw:
                # las sílabas de una palabra armada van pegadas entre sí
                bloques_palabra = self.unir(pw, 0.0) if len(pw) > 1 else pw[0][0]
                piezas.append((bloques_palabra, 0.0))
        return self.unir(piezas, PARAMS["pausa_entre_palabras_ms"] / 1000)

    def silabeo(self, texto):
        """Lee por sílabas: "la vaca" -> la - va - ca."""
        piezas = []
        for w in re.findall(r"[\wáéíóúüñ]+", texto.lower()):
            for s in silabear(w):
                ps = self.silaba(s)
                if ps:
                    piezas.append((self.unir(ps, 0.0), 0.0))
        return self.unir(piezas, PARAMS["pausa_entre_silabas_ms"] / 1000)

    def secuencia(self, pasos):
        """pasos: lista de ("silabas"|"palabra"|"oracion", texto)."""
        audios = []
        for tipo, texto in pasos:
            audios.append((self.silabeo(texto) if tipo == "silabas" else self.oracion(texto), 0.0))
        return self.unir(audios, PARAMS["pausa_entre_pasos_ms"] / 1000)


EJEMPLOS = [
    ("01_unir_silabas_vaca", [("silabas", "vaca"), ("palabra", "vaca"), ("silabas", "la vaca"),
                              ("oracion", "la vaca come pasto")]),
    ("02_oracion", [("oracion", "hoy me voy de vacaciones a la casa de mi tío")]),
    ("03_oracion_desordenada", [("oracion", "a la casa de mi tío hoy me voy de vacaciones")]),
    ("04_otro_orden", [("oracion", "de vacaciones me voy hoy a la casa de mi tío")]),
    ("05_mal_escrita", [("oracion", "la baca come pazto")]),
    ("06_oracion_parque", [("oracion", "el perro juega con la pelota en el parque")]),
    ("07_unir_silabas_casa", [("silabas", "casa"), ("palabra", "casa"), ("silabas", "mi casa"),
                              ("oracion", "mi casa es grande")]),
]
TEXTO_ESPERADO = {
    "01_unir_silabas_vaca": "va ca vaca la va ca la vaca come pasto",
    "02_oracion": "hoy me voy de vacaciones a la casa de mi tío",
    "03_oracion_desordenada": "a la casa de mi tío hoy me voy de vacaciones",
    "04_otro_orden": "de vacaciones me voy hoy a la casa de mi tío",
    "05_mal_escrita": "la vaca come pazto",
    "06_oracion_parque": "el perro juega con la pelota en el parque",
    "07_unir_silabas_casa": "ca sa casa mi ca sa mi casa es grande",
}


# ----------------------------------------------------------------------------- armado del paquete
def armar(voz=VOZ_ID, voz_nombre=VOZ_NOMBRE):
    if SALIDA.exists():
        shutil.rmtree(SALIDA)
    man = {"voz": voz_nombre, "voz_id": voz, "sr": R.SR, "parametros": PARAMS, "palabras": {}, "silabas": {}}

    # 1) palabras: cortar y medir
    crudos, avisos = {}, []
    for w in PALABRAS:
        y, prof = cortar_medio(w, voz)
        if prof < 15:
            avisos.append(f"corte poco limpio en '{w}' (baja {prof:.0f} dB)")
        crudos[(w, "medio")] = y
        if CATEGORIA[w] != "funcion":
            crudos[(w, "final")] = cortar_final(w, voz)
    # una sola ganancia para todas las palabras (respeta que "de" o "la" suenen más suaves)
    g = -20.0 - float(np.median([rms_activo(y) for y in crudos.values()]))
    for (w, var), y in crudos.items():
        pico = 20 * np.log10(np.abs(y).max() + 1e-12)
        gg = min(g, -1.0 - pico)
        rel = f"palabras/{var}/{nombre_archivo(w)}.wav"
        R.escribir_wav(SALIDA / rel, y * 10 ** (gg / 20))
        d = man["palabras"].setdefault(w, {"categoria": CATEGORIA[w], "clave": clave_fonetica(w)})
        d[var] = rel
        d[f"dur_{var}_ms"] = int(len(y) / R.SR * 1000)

    # 2) sílabas: copia recortada de la biblioteca (ya verificadas)
    for carpeta in ["01_vocales", "02_silabas_directas", "03_silabas_inversas", "04_grupos_consonanticos",
                    "05_combinaciones_vocalicas"]:
        for f in sorted((BIBLIOTECA / carpeta).rglob("*.wav")):
            if f.stem.startswith("familia") or f.stem.startswith("vocales"):
                continue
            nombre = f.stem.replace("ny", "ñ")
            if nombre in man["silabas"]:
                continue
            rel = f"silabas/{f.stem}.wav"
            R.escribir_wav(SALIDA / rel, recorte_justo(R.leer_wav(f)))
            man["silabas"][nombre] = rel

    (SALIDA / "manifest_lectura.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")

    # 3) ejemplos armados con el mismo lector que usa la app
    lec = Lector(SALIDA)
    for nombre, pasos in EJEMPLOS:
        R.escribir_wav(SALIDA / "ejemplos" / f"{nombre}.wav", lec.secuencia(pasos))

    # 4) lector.js, página de prueba y README
    for f in ["lector.js", "README.md"]:
        shutil.copy(RAIZ / "herramientas" / "lectura_app" / f, SALIDA / f)
    import html as _h
    pasos_txt = {"silabas": "sílabas", "palabra": "palabra", "oracion": "oración"}
    ej = "".join(f'<div><b>{_h.escape(" → ".join(f"{t} ({pasos_txt[k]})" for k, t in pasos))}</b>'
                 f'<audio controls preload="none" src="ejemplos/{n}.wav"></audio></div>' for n, pasos in EJEMPLOS)
    pagina = (RAIZ / "herramientas" / "lectura_app" / "probar.html").read_text(encoding="utf-8")
    (SALIDA / "probar.html").write_text(pagina.replace("<!--EJEMPLOS-->", ej), encoding="utf-8")
    print(f"{len(man['palabras'])} palabras, {len(man['silabas'])} sílabas, ganancia {g:+.1f} dB")
    for a in avisos:
        print("  aviso:", a)


def verificar():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import buscar_semillas as B
    from verificar import fonetico
    print("Ejemplos:")
    for nombre, _ in EJEMPLOS:
        oido = B.stt_bytes((SALIDA / "ejemplos" / f"{nombre}.wav").read_bytes())
        ok = fonetico(oido).replace(" ", "") == fonetico(TEXTO_ESPERADO[nombre]).replace(" ", "")
        print(f"  {'OK' if ok else '--'} {nombre:26s} {oido}")
    print("Palabras (versión final):")
    man = json.loads((SALIDA / "manifest_lectura.json").read_text(encoding="utf-8"))
    malas = []

    def una(item):
        w, d = item
        if "final" not in d:
            return None
        oido = B.stt_bytes((SALIDA / d["final"]).read_bytes())
        return None if fonetico(oido).replace(" ", "") == fonetico(w) else (w, oido)
    with ThreadPoolExecutor(4) as ex:
        malas = [r for r in ex.map(una, man["palabras"].items()) if r]
    print(f"  {sum('final' in d for d in man['palabras'].values()) - len(malas)} coinciden; distintas: {malas}")


def empaquetar(destino=None):
    destino = Path(destino) if destino else RAIZ / "trabajo" / f"{NOMBRE_ZIP}.zip"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(SALIDA.rglob("*")):
            if f.is_file():
                z.write(f, f"{NOMBRE_ZIP}/{f.relative_to(SALIDA)}")
    print(f"zip: {destino} ({destino.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else "armar"
    {"generar": generar, "armar": armar, "verificar": verificar, "zip": empaquetar}[accion]()
