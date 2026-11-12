"""Lectura encadenada: unir sílabas y armar oraciones en cualquier orden, sin que suene a robot.

Unidades (todas con la misma voz y ajustes):
  - palabras "medio": cómo suena la palabra dentro de una oración. Se graba "<palabra> todo" con el
    contexto "Ella dijo que..." y se corta donde termina la voz de la palabra (antes de la "t").
  - palabras "final": la palabra con cierre de oración ("<palabra>.").
  - sílabas: las de la biblioteca, recortadas (para leer "va - ca").
  - dífonos: transiciones entre sonidos (k-a, a-s...), cortadas de palabras inventadas (difonos.py).
    Arman cualquier palabra que no esté grabada o que el chico escriba mal, respetando el acento.

Empalmes entre palabras según los sonidos que se tocan (como al hablar):
  - antes de p, t, k, ch: un silencio corto (el cierre natural de esa consonante)
  - vocal + vocal ("de‿agua"): se funden con un solape largo
  - el resto: solape corto, con fundido de potencia constante (sin bajón de volumen)

Para que la app cargue rápido, las unidades van en 3 archivos (palabras, sílabas, dífonos) y un índice
(manifest_lectura.json) con dónde empieza cada una. Se cargan una vez y cada lectura se arma en memoria.

  python3 herramientas/lectura.py generar     # pide a ElevenLabs lo que falte (palabras; usa caché)
  python3 herramientas/difonos.py             # pide a ElevenLabs las palabras inventadas de los dífonos
  python3 herramientas/lectura.py armar       # corta, arma los 3 archivos + índice + ejemplos
  python3 herramientas/lectura.py verificar   # transcribe los ejemplos
"""
import io
import json
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import difonos as D  # noqa: E402
import recortar as R  # noqa: E402
from bloques import AJUSTES_NEUTROS, SEMILLA, VOZ_ID, VOZ_NOMBRE  # noqa: E402
from fonetica import (clave_difono, clave_fonetica, fonemas, normalizar_silaba, silabear,  # noqa: E402,F401
                      sin_tildes)
from generar import obtener_toma  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
from voces import BIBLIOTECA, LECTURA as SALIDA  # noqa: E402

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
for _cat, _ws in CONTENIDO.items():
    for _w in _ws.split():
        CATEGORIA[_w] = _cat
PALABRAS = list(CATEGORIA)

# ----------------------------------------------------------------------------- parámetros (iguales en lector.js)
PARAMS = {
    "hueco_oclusiva_ms": 40,      # antes de p, t, k, ch: el cierre natural de la consonante
    "solape_vocales_ms": 35,      # vocal + vocal: se funden ("de‿agua")
    "solape_vocal_ms": 20,        # consonante + vocal ("los‿ojos")
    "solape_ms": 15,              # el resto de los empalmes
    "pausa_coma_ms": 250,
    "pausa_punto_ms": 450,
    "pausa_entre_silabas_ms": 300,
    "pausa_entre_pasos_ms": 700,
    "fundido_difono_ms": dict(D.FUNDIDO_MS),
}
SEPARACION = 0.06   # silencio entre unidades dentro de cada archivo


def n_muestras(seg, sr):
    return int(seg * sr + 0.5)


# ----------------------------------------------------------------------------- generación de palabras
def peticiones():
    p = [(f"{w} {PORTADOR}", CONTEXTO) for w in PALABRAS]
    p += [(f"{w}.", CONTEXTO) for w in PALABRAS if CATEGORIA[w] != "funcion"]
    return p


def generar(voz=VOZ_ID):
    ps = peticiones()
    print(f"{len(ps)} peticiones, {sum(len(t) for t, _ in ps)} caracteres (las que ya están en caché no se cobran)")
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(lambda tp: obtener_toma(tp[0], AJUSTES_NEUTROS, tp[1], SEMILLA, voz=voz), ps))
    print("listo")


def _bordes(y, fi=0.004, fo=0.010):
    y = y.copy()
    a, b = int(fi * R.SR), int(fo * R.SR)
    y[:a] *= np.linspace(0, 1, a)
    y[-b:] *= np.linspace(1, 0, b)
    return y


def cortar_medio(w, voz=VOZ_ID):
    """La palabra dentro de la oración: desde que empieza la voz hasta que termina (sin el silencio de la t)."""
    audio, al, _, _ = obtener_toma(f"{w} {PORTADOR}", AJUSTES_NEUTROS, CONTEXTO, SEMILLA, voz=voz)
    x = R.leer_wav(io.BytesIO(audio))
    db = R.energia_db(x)
    fin_w = al["character_end_times_seconds"][len(w) - 1]
    ini_t = al["character_start_times_seconds"][len(w) + 1]
    a, b = R.t2f(min(fin_w, ini_t) - 0.05), R.t2f(max(fin_w, ini_t) + 0.06)
    cierre = a + int(np.argmin(db[a:b]))
    tope = db[:cierre].max()
    voz_on = np.where(db[:cierre] > tope - 30)[0]
    ini = max(0, voz_on[0] - 2)
    fin = voz_on[-1] + 3
    profundidad = float(db[a:b].max() - db[cierre])
    return _bordes(x[int(ini * R.HOP * R.SR):int(fin * R.HOP * R.SR)]), profundidad


def cortar_final(w, voz=VOZ_ID):
    x = R.leer_wav(io.BytesIO(obtener_toma(f"{w}.", AJUSTES_NEUTROS, CONTEXTO, SEMILLA, voz=voz)[0]))
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


# ----------------------------------------------------------------------------- mezcla (igual que lector.js)
def mezclar(piezas, sr):
    """piezas: [(audio, junta_muestras)]; junta > 0 = hueco de silencio antes, < 0 = solape con fundido."""
    pos, inicios = 0, []
    for k, (y, junta) in enumerate(piezas):
        if k == 0:
            ini = 0
        elif junta >= 0:
            ini = pos + junta
        else:
            n = min(-junta, len(piezas[k - 1][0]), len(y))
            ini = pos - n
        inicios.append(ini)
        pos = ini + len(y)
    out = np.zeros(max(pos, 0), dtype=np.float32)
    for k, (y, junta) in enumerate(piezas):
        ini = inicios[k]
        y = y.astype(np.float32)
        if k > 0 and junta < 0:
            n = min(-junta, len(piezas[k - 1][0]), len(y))
            if n > 0:
                ang = (np.arange(n, dtype=np.float32) + 0.5) / n * (np.pi / 2)
                out[ini:ini + n] *= np.cos(ang)
                y = y.copy()
                y[:n] *= np.sin(ang)
        out[ini:ini + len(y)] += y
    return out


def junta_palabras(prev_fin, sig_ini, sr):
    """Cuántas muestras de hueco (+) o solape (-) entre dos palabras según los sonidos que se tocan."""
    p = PARAMS
    if sig_ini in D.CORTE_EN_CIERRE:
        return n_muestras(p["hueco_oclusiva_ms"] / 1000, sr)
    if sig_ini in D.VOC:
        ms = p["solape_vocales_ms"] if prev_fin in D.VOC else p["solape_vocal_ms"]
        return -n_muestras(ms / 1000, sr)
    return -n_muestras(p["solape_ms"] / 1000, sr)


# ----------------------------------------------------------------------------- lector (igual que lector.js)
class Lector:
    def __init__(self, base=SALIDA):
        self.base = Path(base)
        self.m = json.loads((self.base / "manifest_lectura.json").read_text(encoding="utf-8"))
        self.sr = self.m["sr"]
        self.audios = {k: R.leer_wav(self.base / v).astype(np.float32) for k, v in self.m["audios"].items()}
        self.por_tilde, self.por_clave = {}, {}
        for w, d in self.m["palabras"].items():
            self.por_tilde.setdefault(sin_tildes(w), w)
            self.por_clave.setdefault(d["clave"], w)

    def _corte(self, archivo, ini_dur):
        a = n_muestras(ini_dur[0], self.sr)
        return self.audios[archivo][a:a + n_muestras(ini_dur[1], self.sr)]

    def buscar(self, w):
        w = w.lower()
        if w in self.m["palabras"]:
            return w
        return self.por_tilde.get(sin_tildes(w)) or self.por_clave.get(clave_fonetica(w))

    def difonos(self, fon):
        seq = [("_", False)] + list(fon) + [("_", False)]
        piezas = []
        for (s1, a1), (s2, a2) in zip(seq, seq[1:]):
            d = self._buscar_difono(s1, a1, s2, a2)
            if d is None:
                continue
            y = self._corte("difonos", d[:2])
            if piezas:
                ms = PARAMS["fundido_difono_ms"][D.clase(d[2])]
                piezas.append((y, -n_muestras(ms / 1000, self.sr)))
            else:
                piezas.append((y, 0))
        return mezclar(piezas, self.sr) if piezas else np.zeros(0, dtype=np.float32)

    def _buscar_difono(self, s1, a1, s2, a2):
        inv = self.m["difonos"]
        for x1, x2 in [(a1, a2), (not a1, a2), (a1, not a2), (not a1, not a2)]:
            k = clave_difono((s1, x1), (s2, x2))
            if k in inv:
                return inv[k]
        for t1, t2 in [(D.SUSTITUTOS.get(s1, s1), s2), (s1, D.SUSTITUTOS.get(s2, s2))]:
            for x1, x2 in [(a1, a2), (not a1, a2), (a1, not a2)]:
                k = clave_difono((t1, x1), (t2, x2))
                if k in inv:
                    return inv[k]
        return None

    def palabra(self, w, final):
        """(audio, primer_sonido, último_sonido) de una palabra."""
        pal = self.buscar(w)
        if pal:
            d = self.m["palabras"][pal]
            fon = fonemas(pal)
            y = self._corte("palabras", d["final"] if final and "final" in d else d["medio"])
        else:
            fon = fonemas(w)
            y = self.difonos(fon)
        if not fon:
            return None
        return y, fon[0][0], fon[-1][0]

    def oracion(self, texto):
        tokens = re.findall(r"[^\W\d_]+|[.,;:!?¡¿]", texto)
        total = sum(1 for t in tokens if t[0].isalpha())
        piezas, vistas, ultimo, pausa = [], 0, None, 0
        for t in tokens:
            if not t[0].isalpha():
                if piezas and t in ",;:":
                    pausa = max(pausa, n_muestras(PARAMS["pausa_coma_ms"] / 1000, self.sr))
                elif piezas and t in ".!?":
                    pausa = max(pausa, n_muestras(PARAMS["pausa_punto_ms"] / 1000, self.sr))
                continue
            vistas += 1
            r = self.palabra(t, vistas == total)
            if r is None or not len(r[0]):
                continue
            y, ini, fin = r
            junta = 0 if not piezas else (pausa if pausa else junta_palabras(ultimo, ini, self.sr))
            piezas.append((y, junta))
            ultimo, pausa = fin, 0
        return mezclar(piezas, self.sr) if piezas else np.zeros(0, dtype=np.float32)

    def silaba(self, s):
        t = normalizar_silaba(s)
        if t in self.m["silabas"]:
            return self._corte("silabas", self.m["silabas"][t])
        return self.difonos(fonemas(s))   # sílaba que no está grabada: con dífonos

    def silabeo(self, texto):
        piezas = []
        for w in re.findall(r"[^\W\d_]+", texto.lower()):
            for s in silabear(w):
                y = self.silaba(s)
                if len(y):
                    piezas.append((y, n_muestras(PARAMS["pausa_entre_silabas_ms"] / 1000, self.sr) if piezas else 0))
        return mezclar(piezas, self.sr) if piezas else np.zeros(0, dtype=np.float32)

    def secuencia(self, pasos):
        piezas = []
        for tipo, texto in pasos:
            y = self.silabeo(texto) if tipo == "silabas" else self.oracion(texto)
            if len(y):
                piezas.append((y, n_muestras(PARAMS["pausa_entre_pasos_ms"] / 1000, self.sr) if piezas else 0))
        return mezclar(piezas, self.sr) if piezas else np.zeros(0, dtype=np.float32)

    def diagnostico(self, texto):
        res = []
        for w in re.findall(r"[^\W\d_]+", texto):
            pal = self.buscar(w)
            if pal and sin_tildes(pal) == sin_tildes(w.lower()):
                res.append((w, "grabada", pal))
            elif pal:
                res.append((w, "suena_igual", pal))
            else:
                res.append((w, "difonos", "-".join(silabear(w))))
        return res


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
    ("08_palabras_nuevas", [("oracion", "el dinosaurio come tomate y chocolate")]),
    ("09_unir_silabas_tortuga", [("silabas", "tortuga"), ("palabra", "tortuga"),
                                 ("oracion", "la tortuga camina en el jardín")]),
]
TEXTO_ESPERADO = {
    "01_unir_silabas_vaca": "va ca vaca la va ca la vaca come pasto",
    "02_oracion": "hoy me voy de vacaciones a la casa de mi tío",
    "03_oracion_desordenada": "a la casa de mi tío hoy me voy de vacaciones",
    "04_otro_orden": "de vacaciones me voy hoy a la casa de mi tío",
    "05_mal_escrita": "la vaca come pazto",
    "06_oracion_parque": "el perro juega con la pelota en el parque",
    "07_unir_silabas_casa": "ca sa casa mi ca sa mi casa es grande",
    "08_palabras_nuevas": "el dinosaurio come tomate y chocolate",
    "09_unir_silabas_tortuga": "tor tu ga tortuga la tortuga camina en el jardín",
}


# ----------------------------------------------------------------------------- armado del paquete
def _archivo_unidades(unidades, sr):
    """Junta unidades en un solo audio con silencio entre medio. Devuelve (audio, {nombre: [ini, dur]}, marcas)."""
    sep = np.zeros(n_muestras(SEPARACION, sr), dtype=np.float32)
    partes, indice, pos = [np.zeros(n_muestras(0.2, sr), dtype=np.float32)], {}, n_muestras(0.2, sr)
    marcas = []
    for nombre, y in unidades:
        y = y.astype(np.float32)
        indice[nombre] = [round(pos / sr, 5), round(len(y) / sr, 5)]
        if len(marcas) < 3:
            sobre = np.where(np.abs(y) > 0.05)[0]
            if len(sobre):
                marcas.append(round((pos + sobre[0]) / sr, 5))
        partes += [y, sep]
        pos += len(y) + len(sep)
    return np.concatenate(partes), indice, marcas


def armar(voz=VOZ_ID, voz_nombre=VOZ_NOMBRE):
    for viejo in ["palabras", "silabas", "ejemplos"]:
        if (SALIDA / viejo).exists():
            shutil.rmtree(SALIDA / viejo)
    SALIDA.mkdir(exist_ok=True)
    man = {"voz": voz_nombre, "voz_id": voz, "sr": R.SR, "parametros": PARAMS,
           "audios": {"palabras": "palabras.wav", "silabas": "silabas.wav", "difonos": "difonos.wav"},
           "marcas": {}, "palabras": {}, "silabas": {}, "difonos": {}}

    # 1) palabras
    crudos, avisos = {}, []
    for w in PALABRAS:
        y, prof = cortar_medio(w, voz)
        if prof < 15:
            avisos.append(f"corte poco limpio en '{w}' (baja {prof:.0f} dB)")
        crudos[(w, "medio")] = y
        if CATEGORIA[w] != "funcion":
            crudos[(w, "final")] = cortar_final(w, voz)
    g = -20.0 - float(np.median([rms_activo(y) for y in crudos.values()]))
    unidades = []
    for (w, var), y in crudos.items():
        gg = min(g, -1.0 - 20 * np.log10(np.abs(y).max() + 1e-12))
        unidades.append((f"{w}|{var}", y * 10 ** (gg / 20)))
    audio, idx, marcas = _archivo_unidades(unidades, R.SR)
    R.escribir_wav(SALIDA / "palabras.wav", audio)
    man["marcas"]["palabras"] = marcas
    for w in PALABRAS:
        d = {"categoria": CATEGORIA[w], "clave": clave_fonetica(w), "medio": idx[f"{w}|medio"]}
        if f"{w}|final" in idx:
            d["final"] = idx[f"{w}|final"]
        man["palabras"][w] = d

    # 2) sílabas de la biblioteca
    unidades, vistos = [], set()
    for carpeta in ["01_vocales", "02_silabas_directas", "03_silabas_inversas", "04_grupos_consonanticos",
                    "05_combinaciones_vocalicas"]:
        for f in sorted((BIBLIOTECA / carpeta).rglob("*.wav")):
            if f.stem.startswith("familia") or f.stem.startswith("vocales"):
                continue
            nombre = f.stem.replace("ny", "ñ")
            if nombre not in vistos:
                vistos.add(nombre)
                unidades.append((nombre, recorte_justo(R.leer_wav(f))))
    audio, man["silabas"], man["marcas"]["silabas"] = _archivo_unidades(unidades, R.SR)
    R.escribir_wav(SALIDA / "silabas.wav", audio)

    # 3) dífonos
    inv = D.extraer(voz)
    nombres = sorted(inv)
    audio, idx, man["marcas"]["difonos"] = _archivo_unidades([(k, inv[k][0]) for k in nombres], R.SR)
    R.escribir_wav(SALIDA / "difonos.wav", audio)
    man["difonos"] = {k: idx[k] + [inv[k][1]] for k in nombres}

    man["ejemplos"] = [{"archivo": f"ejemplos/{n}.wav", "texto": " → ".join(t for _, t in pasos)}
                       for n, pasos in EJEMPLOS]
    (SALIDA / "manifest_lectura.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")

    # 4) ejemplos con el mismo lector que usa la app
    lec = Lector(SALIDA)
    for nombre, pasos in EJEMPLOS:
        R.escribir_wav(SALIDA / "ejemplos" / f"{nombre}.wav", lec.secuencia(pasos))
    for f in ["lector.js", "README.md"]:
        shutil.copy(RAIZ / "herramientas" / "lectura_app" / f, SALIDA / f)
    print(f"{len(man['palabras'])} palabras, {len(man['silabas'])} sílabas, {len(man['difonos'])} dífonos, "
          f"ganancia palabras {g:+.1f} dB")
    for a in avisos:
        print("  aviso:", a)


def verificar():
    import buscar_semillas as B
    from verificar import fonetico
    print("Ejemplos:")
    for nombre, _ in EJEMPLOS:
        oido = B.stt_bytes((SALIDA / "ejemplos" / f"{nombre}.wav").read_bytes())
        ok = fonetico(oido).replace(" ", "") == fonetico(TEXTO_ESPERADO[nombre]).replace(" ", "")
        print(f"  {'OK' if ok else '--'} {nombre:26s} {oido}")


if __name__ == "__main__":
    accion = sys.argv[1] if len(sys.argv) > 1 else "armar"
    {"generar": generar, "armar": armar, "verificar": verificar}[accion]()
