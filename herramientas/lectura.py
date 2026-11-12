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
from bloques import AJUSTES_LECTURA as AJUSTES_NEUTROS, SEMILLA, VOZ_ID, VOZ_NOMBRE  # noqa: E402
from fonetica import (clave_difono, clave_fonetica, fonemas, normalizar_silaba, silabear,  # noqa: E402,F401
                      sin_tildes)
from generar import TOMAS, clave_toma, obtener_toma  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
from voces import BIBLIOTECA, LECTURA as SALIDA, VOZ  # noqa: E402
import prosodia as P  # noqa: E402

CONTEXTO = "Ella dijo que"   # previous_text: la palabra se dice a mitad de oración
PORTADOR = "todo"            # palabra que sigue y se corta (su "t" deja un silencio limpio)

# ----------------------------------------------------------------------------- vocabulario
FUNCION = ("el la los las un una unos unas mi mis tu tus su sus a al de del en con por para sin sobre "
           "y o pero que porque me te se le lo si ni nos les hasta desde entre hacia cuando donde tan").split()
CONTENIDO = {
    "pronombres": "yo tú él ella nosotros ellos este esta estos estas ese esa esos esas eso esto algo nadie alguien",
    "personas": ("mamá papá tío tía abuelo abuela hermano hermana amigo amiga niño niña maestra maestro bebé hijo hija "
                 "primo prima señor señora doctor doctora policía bombero vecino vecina rey reina princesa príncipe hada "
                 "pirata payaso gente familia niños niñas amigos amigas hermanos papás abuelos chicos chicas abuelita "
                 "abuelito bebés señorita profesor profesora cocinero granjero hermanito hermanita alumno alumnos "
                 "compañero compañera astronauta"),
    "cuerpo": "mano manos pie pies ojo ojos boca nariz oreja cabeza pelo diente dientes brazo pierna dedo cara corazón",
    "animales": ("vaca perro gato pato pájaro caballo pez ratón conejo oso león mono oveja pollito mariposa toro "
                 "dinosaurio ardilla elefante tortuga mariquita cocodrilo gallina perrito perrita gatito gatita cerdo "
                 "burro gallo pollo loro búho rana sapo ballena delfín tiburón pulpo cangrejo foca pingüino lobo zorro "
                 "tigre jirafa cebra camello canguro serpiente abeja hormiga araña mosca caracol paloma águila perros "
                 "gatos pájaros animales peces patos vacas pollitos ovejas conejito ratoncito pececito patito pajarito "
                 "caballito mariposas abejas hormigas dinosaurios dragón unicornio monstruo mascota"),
    "comida": ("pan leche fruta manzana helado comida tomate chocolate naranja sandía agua sopa arroz carne huevo "
               "huevos queso jugo galleta galletas torta pastel dulce dulces caramelo plátano banana uva uvas fresa "
               "pera piña limón zanahoria maíz pizza miel desayuno almuerzo cena frutas arepa empanada tortilla "
               "pescado ensalada papitas mango melón cereza coco durazno manzanas naranjas tomates helados bebida "
               "refresco té merienda postre hambre sed"),
    "casa_y_escuela": ("mesa cama libro juguete pelota globo regalo puerta ventana silla sofá cocina baño cuarto piso "
                       "cuchara plato vaso taza llave lámpara reloj teléfono televisión computadora cuaderno lápiz "
                       "colores papel tijeras mochila caja juguetes muñeca tambor guitarra piano dibujo cuento canción "
                       "música tarea clase recreo letra letras palabra palabras nombre número libros juegos casita "
                       "almohada manta jabón cepillo toalla espejo escalera columpio tobogán cometa trompo muñeco "
                       "peluche osito carrito bloques rompecabezas crayones pincel pintura cuadernos regla borrador "
                       "pizarra salón patio"),
    "transporte": "carro bicicleta helicóptero barco avión tren autobús camión cohete",
    "ropa": "zapato pantalón camisa vestido falda zapatos gorra sombrero abrigo botas",
    "naturaleza": ("sol luna flor árbol estrella lluvia nube pasto cielo tierra arena piedra hoja hojas planta flores "
                   "árboles bosque lago isla nieve viento estrellas arcoíris mundo nubes rayo trueno tormenta ola olas "
                   "concha montañas camino puente volcán cueva planeta espacio"),
    "lugares": ("casa escuela parque playa jardín campo río mar montaña ciudad calle tienda colegio hospital mercado "
                "zoológico granja pueblo lugar"),
    "verbos": ("es está son están soy estoy tiene tengo va voy vamos come como bebe juega juego corre salta duerme lee "
               "canta mira quiere quiero vive nada vuela camina toma llueve pinta dibuja escribe aprende hay era fue "
               "tenía hace hago puede puedo sabe dice ve veo oye habla hablo escucha comemos comen bebo juegan jugamos "
               "jugar comer correr saltar leer escribir dibujar pintar cantar bailar dormir nadar ir ver hacer jugaba "
               "corro corren duermo duermen leo leen canto cantan baila bailo bailan abre cierra sube baja entra sale "
               "llega busca encuentra ayuda ayudo lava limpia compra trae lleva da doy pone ríe llora abraza gusta "
               "gustan ama amo necesito piensa conoce vivo viven cuida patea sopla toca miro camino corrió saltó comió "
               "jugó vio llegó dijo estaba quieren queremos tienen tenemos van fuimos vi encanta encantan puedes "
               "quieres tienes vas eres estás somos sabes dices haces juegas comes corres miras ves despierta levanta "
               "baña viste peina ordena guarda saca regala presta comparte espera sigue empieza termina gana pierde cae "
               "cayó rompe arregla construye cuenta leyó escribió dibujó pintó cantó bailó durmió nadó voló caminó "
               "subió bajó abrió cerró llovió hizo puso trajo encontró ayudó compró quería estaban fueron jugaron "
               "comieron corrieron llegaron vinieron"),
    "adjetivos": ("grande pequeño pequeña bonito bonita feliz contento contenta alto rápido nuevo chico chica chiquito "
                  "gordo largo corto lindo linda bueno buena malo alegre triste enojado cansado limpio sucio caliente "
                  "frío fría rico rica suave mojado lleno fuerte lento nueva viejo vieja bajo alta grandes pequeños "
                  "bonitos bonitas felices contentos altos bajos rápida lenta mojada sucia llena vacío vacía tranquilo "
                  "valiente divertido divertida dormido despierto hermoso hermosa preciosa favorito favorita mágico "
                  "gigante peludo redondo cuadrado"),
    "colores": ("rojo azul verde amarillo blanco negro roja verdes amarilla blanca negra rosada morada anaranjado gris "
                "rosado morado café"),
    "numeros": "uno dos tres cuatro cinco seis siete ocho nueve diez",
    "tiempo": ("hoy ayer mañana ahora siempre tarde noche día vacaciones cumpleaños fiesta lunes martes miércoles "
               "jueves viernes sábado domingo semana año invierno verano luego después antes nunca ya temprano todavía "
               "hora horas minuto mes noches días fin navidad entonces"),
    "preguntas_y_saludos": "qué cómo dónde cuándo quién cuál hola adiós gracias perdón favor sí no",
    "otros": ("mucho muchos muy más aquí allá también todos juntos muchas poco pocos todo toda otro otra primero "
              "último mejor bien mal vez veces solo sola cerca lejos arriba abajo adentro afuera encima debajo detrás "
              "delante despacio bastante cosa cosas"),
}
CATEGORIA = {w: "funcion" for w in FUNCION}
for _cat, _ws in CONTENIDO.items():
    for _w in _ws.split():
        CATEGORIA[_w] = _cat
PALABRAS = list(CATEGORIA)

# ----------------------------------------------------------------------------- parámetros (iguales en lector.js)
PARAMS = {
    # Empalme "legato": cada palabra conserva su cola natural (no se corta de golpe) y la siguiente entra encima
    # de esa cola mientras se apaga, sumándose sin fundidos (como al hablar de corrido).
    "entrada_ms": 10,             # la palabra siguiente entra sobre su propio silencio inicial...
    "solape_cola": 0.5,           # ...y sobre esta fracción de la cola que se apaga de la anterior
    "hueco_oclusiva_ms": 30,      # antes de p, t, k, ch: la cola termina y queda el silencio del cierre
    "pausa_extra_ms": 0,          # pausa agregada entre palabras: subirla da una lectura más pausada (p. ej. 120)
    "pausa_coma_ms": 250,
    "pausa_punto_ms": 450,
    "pausa_entre_silabas_ms": 300,
    "pausa_entre_pasos_ms": 700,
    "fundido_difono_ms": dict(D.FUNDIDO_MS),
}
SEPARACION = 0.06   # silencio entre unidades dentro de cada archivo


def n_muestras(seg, sr):
    """Segundos -> muestras, redondeando al más cercano (igual para negativos; igual en lector.js)."""
    v = seg * sr
    return int(v + 0.5) if v >= 0 else -int(-v + 0.5)


# ----------------------------------------------------------------------------- generación de palabras
def semilla(w, final=False):
    """Semilla de cada palabra. Algunas voces regraban una palabra con otra semilla (ver voces.py): la clave "w" vale
    para las dos versiones y "w." solo para la versión final."""
    sp = VOZ.get("semilla_palabras", {})
    return sp.get(f"{w}.", sp.get(w, SEMILLA)) if final else sp.get(w, SEMILLA)


def peticiones():
    p = [(f"{w} {PORTADOR}", CONTEXTO, semilla(w)) for w in PALABRAS]
    p += [(f"{w}.", CONTEXTO, semilla(w, final=True)) for w in PALABRAS if CATEGORIA[w] != "funcion"]
    return p


def grabada(w, voz=VOZ_ID):
    """True si las tomas de la palabra ya están en el caché (armar no genera nada nuevo ni gasta créditos)."""
    textos = [(f"{w} {PORTADOR}", False)] + ([(f"{w}.", True)] if CATEGORIA[w] != "funcion" else [])
    return all((TOMAS / f"{clave_toma(t, AJUSTES_NEUTROS, CONTEXTO, semilla(w, fin), voz=voz)}.wav").exists()
               for t, fin in textos)


SESEO = VOZ.get("dialecto") == "latinoamericano"   # z, ce, ci y s suenan igual: "pazto" se lee con "pasto"
PALABRAS_POR_ARCHIVO = 160   # el banco se reparte en varios audios: cada uno se decodifica rápido y con poca memoria


def generar(voz=VOZ_ID):
    ps = peticiones()
    print(f"{len(ps)} peticiones, {sum(len(t) for t, _, _ in ps)} caracteres (las que ya están en caché no se cobran)")
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(lambda tp: obtener_toma(tp[0], AJUSTES_NEUTROS, tp[1], tp[2], voz=voz), ps))
    print("listo")


def _bordes(y, fi=0.004, fo=0.010):
    y = y.copy()
    a, b = int(fi * R.SR), int(fo * R.SR)
    y[:a] *= np.linspace(0, 1, a)
    y[-b:] *= np.linspace(1, 0, b)
    return y


def cortar_medio(w, voz=VOZ_ID):
    """La palabra dentro de la oración: desde que empieza la voz hasta que termina (sin el silencio de la t)."""
    audio, al, _, _ = obtener_toma(f"{w} {PORTADOR}", AJUSTES_NEUTROS, CONTEXTO, semilla(w), voz=voz)
    x = R.leer_wav(io.BytesIO(audio))
    db = R.energia_db(x)
    fin_w = al["character_end_times_seconds"][len(w) - 1]
    ini_t = al["character_start_times_seconds"][len(w) + 1]
    a = min(max(0, R.t2f(min(fin_w, ini_t) - 0.05)), len(db) - 2)
    b = min(len(db), max(a + 2, R.t2f(max(fin_w, ini_t) + 0.06)))
    cierre = a + int(np.argmin(db[a:b]))
    tope = db[:cierre].max()
    voz_on = np.where(db[:cierre] > tope - 30)[0]
    ini = max(0, voz_on[0] - 2)
    fin = voz_on[-1] + 3
    profundidad = float(db[a:b].max() - db[cierre])
    return _bordes(x[int(ini * R.HOP * R.SR):int(fin * R.HOP * R.SR)]), profundidad


def cortar_final(w, voz=VOZ_ID):
    x = R.leer_wav(io.BytesIO(obtener_toma(f"{w}.", AJUSTES_NEUTROS, CONTEXTO, semilla(w, final=True), voz=voz)[0]))
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
def cola_seg(y, sr):
    """Segundos de la cola que se apaga al final de una palabra: desde el último tramo de 5 ms que está a menos
    de 9 dB de su voz típica hasta el final (máximo 80 ms). Igual en lector.js."""
    hop, win = int(0.005 * sr), int(0.010 * sr)
    n = (len(y) - win) // hop + 1
    if n < 4:
        return 0.0
    y = np.asarray(y, dtype=np.float64)
    idx = np.arange(win)[None, :] + hop * np.arange(n)[:, None]
    db = 20 * np.log10(np.sqrt((y[idx] ** 2).mean(axis=1)) + 1e-10)
    med = np.median(db[db > db.max() - 25])
    k = np.where(db >= med - 9)[0][-1]
    return min(0.08, (len(y) - (k + 1) * hop) / sr)


def mezclar(piezas, sr):
    """piezas: [(audio, junta_muestras)] o [(audio, junta, "sumar")].
    junta > 0 = hueco de silencio antes; < 0 = solape: con fundido de potencia constante (empalmes de dífonos)
    o, con "sumar", superpuesto sin fundidos (empalme legato entre palabras)."""
    piezas = [(p[0], p[1], p[2] if len(p) > 2 else None) for p in piezas]
    pos, inicios = 0, []
    for k, (y, junta, _) in enumerate(piezas):
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
    for k, (y, junta, modo) in enumerate(piezas):
        ini = inicios[k]
        y = y.astype(np.float32)
        if k > 0 and junta < 0 and modo != "sumar":
            n = min(-junta, len(piezas[k - 1][0]), len(y))
            if n > 0:
                ang = (np.arange(n, dtype=np.float32) + 0.5) / n * (np.pi / 2)
                out[ini:ini + n] *= np.cos(ang)
                y = y.copy()
                y[:n] *= np.sin(ang)
        out[ini:ini + len(y)] += y
    return out


def apagar(y, sr, ms=40):
    """Apaga suave (coseno, 40 ms) el final de una palabra que termina seca ("medio" o armada con dífonos) cuando
    después viene una pausa. Igual en lector.js."""
    n = min(len(y), n_muestras(ms / 1000, sr))
    z = np.array(y, dtype=np.float64)
    if n > 0:
        z[len(z) - n:] *= 0.5 + 0.5 * np.cos(np.pi * (np.arange(n) + 0.5) / n)
    return z.astype(np.float32)


def junta_palabras(prev_audio, sig_ini, sr):
    """Muestras de hueco (+) o solape (-) entre dos palabras (empalme legato, ver PARAMS)."""
    p = PARAMS
    extra = p["pausa_extra_ms"] / 1000
    if sig_ini in D.CORTE_EN_CIERRE:
        return n_muestras(p["hueco_oclusiva_ms"] / 1000 + extra, sr)
    return n_muestras(extra - p["entrada_ms"] / 1000 - p["solape_cola"] * cola_seg(prev_audio, sr), sr)


# ----------------------------------------------------------------------------- lector (igual que lector.js)
class Lector:
    def __init__(self, base=SALIDA):
        self.base = Path(base)
        self.m = json.loads((self.base / "manifest_lectura.json").read_text(encoding="utf-8"))
        self.sr = self.m["sr"]
        self.seseo = bool(self.m.get("seseo"))
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
        return self.por_tilde.get(sin_tildes(w)) or self.por_clave.get(clave_fonetica(w, self.seseo))

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
        """(audio, primer_sonido, último_sonido, termina_natural) de una palabra. termina_natural: se usó la versión
        "final", que se apaga sola; la "medio" y las armadas con dífonos terminan secas."""
        pal = self.buscar(w)
        natural = False
        if pal:
            d = self.m["palabras"][pal]
            fon = fonemas(pal)
            natural = bool(final and "final" in d)
            y = self._corte(d.get("archivo", "palabras"), d["final"] if natural else d["medio"])
        else:
            fon = fonemas(w)
            y = self.difonos(fon)
        if not fon:
            return None
        return y, fon[0][0], fon[-1][0], natural

    def oracion(self, texto):
        tokens = re.findall(r"[^\W\d_]+|[.,;:!?¡¿]", texto)
        total = sum(1 for t in tokens if t[0].isalpha())
        piezas, vistas, pausa, seca = [], 0, 0, False
        for i, t in enumerate(tokens):
            if not t[0].isalpha():
                if piezas and t in ",;:":
                    pausa = max(pausa, n_muestras(PARAMS["pausa_coma_ms"] / 1000, self.sr))
                elif piezas and t in ".!?":
                    pausa = max(pausa, n_muestras(PARAMS["pausa_punto_ms"] / 1000, self.sr))
                continue
            vistas += 1
            # versión "final" en la última palabra y antes de un punto (cierra la oración, se apaga sola)
            sig = tokens[i + 1] if i + 1 < len(tokens) else ""
            r = self.palabra(t, vistas == total or sig in (".", "!", "?"))
            if r is None or not len(r[0]):
                continue
            y, ini, fin, natural = r
            junta = 0 if not piezas else (pausa if pausa else junta_palabras(piezas[-1][0], ini, self.sr))
            if piezas and seca and (pausa or PARAMS["pausa_extra_ms"] > 0):
                piezas[-1] = (apagar(piezas[-1][0], self.sr), piezas[-1][1], piezas[-1][2])
            piezas.append((y, junta, "sumar"))
            pausa, seca = 0, not natural
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
    "05_mal_escrita": "la vaca come pasto" if SESEO else "la vaca come pazto",
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


def armar(voz=VOZ_ID, voz_nombre=VOZ_NOMBRE, tono_palabras=True, tono_difonos="parcial", nivel_difonos=True,
          solapes=None, fraccion=0.5):
    for viejo in ["palabras", "silabas", "ejemplos"]:
        if (SALIDA / viejo).exists():
            shutil.rmtree(SALIDA / viejo)
    SALIDA.mkdir(exist_ok=True)
    for f in SALIDA.glob("palabras*.wav"):
        f.unlink()
    if solapes:
        PARAMS.update(solapes)
    man = {"voz": voz_nombre, "voz_id": voz, "sr": R.SR, "seseo": SESEO, "parametros": PARAMS,
           "audios": {}, "marcas": {}, "palabras": {}, "silabas": {}, "difonos": {}}

    # 1) palabras (solo las que tienen grabación de esta voz; el resto se arma con dífonos)
    palabras = [w for w in PALABRAS if grabada(w, voz)]
    if len(palabras) < len(PALABRAS):
        print(f"palabras sin grabar con esta voz: {len(PALABRAS) - len(palabras)} (se leen con dífonos)")
    crudos, avisos = {}, []
    for w in palabras:
        y, prof = cortar_medio(w, voz)
        if prof < 15:
            avisos.append(f"corte poco limpio en '{w}' (baja {prof:.0f} dB)")
        crudos[(w, "medio")] = y
        if CATEGORIA[w] != "funcion":
            crudos[(w, "final")] = cortar_final(w, voz)
    # tono base de la voz: la mediana del tono de las palabras "medio"
    rango = VOZ["rango_f0"]
    tonos = []
    for (w, var), y in crudos.items():
        if var == "medio":
            f = P.f0(y.astype(np.float64), R.SR, *rango)
            tonos += list(P.a_st(f[f > 0]))
    base_hz = float(P.de_st(np.median(tonos)))
    # bordes al tono base (la melodía de adentro se conserva; dos pasadas para que converja) y sin la cola que se apaga
    b_st = P.a_st(base_hz)
    for (w, var), y in list(crudos.items()):
        y = y.astype(np.float64)
        bordes = (b_st, b_st) if var == "medio" else (b_st, None)
        if tono_palabras:
            for _ in range(2):   # como máximo 3 semitonos: más que eso en una palabra corta deja un "arranque" raro
                y = P.ajustar_tono(y, R.SR, rango, bordes=bordes, max_st=3.0)
        crudos[(w, var)] = y
    man["tono_base_hz"] = round(base_hz, 1)
    man["rango_tono_hz"] = [round(rango[0], 1), round(rango[1], 1)]
    g = -20.0 - float(np.median([rms_activo(y) for y in crudos.values()]))
    for k in range(0, len(palabras), PALABRAS_POR_ARCHIVO):
        grupo = palabras[k:k + PALABRAS_POR_ARCHIVO]
        archivo = f"palabras_{k // PALABRAS_POR_ARCHIVO + 1}"
        unidades = []
        for w in grupo:
            for var in ["medio", "final"]:
                if (w, var) in crudos:
                    y = crudos[(w, var)]
                    gg = min(g, -1.0 - 20 * np.log10(np.abs(y).max() + 1e-12))
                    unidades.append((f"{w}|{var}", y * 10 ** (gg / 20)))
        audio, idx, marcas = _archivo_unidades(unidades, R.SR)
        R.escribir_wav(SALIDA / f"{archivo}.wav", audio)
        man["audios"][archivo] = f"{archivo}.wav"
        man["marcas"][archivo] = marcas
        for w in grupo:
            d = {"categoria": CATEGORIA[w], "clave": clave_fonetica(w, SESEO), "archivo": archivo,
                 "medio": idx[f"{w}|medio"]}
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
    man["audios"]["silabas"] = "silabas.wav"

    # 3) dífonos
    inv = D.extraer(voz, base_hz=base_hz, rango=rango, tono=tono_difonos, nivel=nivel_difonos, fraccion=fraccion)
    nombres = sorted(inv)
    audio, idx, man["marcas"]["difonos"] = _archivo_unidades([(k, inv[k][0]) for k in nombres], R.SR)
    R.escribir_wav(SALIDA / "difonos.wav", audio)
    man["audios"]["difonos"] = "difonos.wav"
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
