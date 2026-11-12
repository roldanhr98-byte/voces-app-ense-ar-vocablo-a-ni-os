"""Definición de los 6 bloques de texto y de cómo se organiza cada unidad en carpetas.

Cada bloque se genera en UNA sola llamada a ElevenLabs (máxima consistencia de voz)
y después se recorta en unidades (letra, sílaba, palabra, frase).

Estructura:
  BLOQUES = [ {id, nombre, archivo, previous_text, voice_settings, secciones:[...]}, ... ]
  seccion = {id, carpeta, modo, items}
    modo "familias": items = [(grupo, [unidades...]), ...]  -> carpeta/grupo/unidad.wav + familia_<grupo>.wav
    modo "plano":    items = [unidades...]                   -> carpeta/unidad.wav
    modo "frases":   items = [frases...]                     -> carpeta/NN_frase.wav
    modo "parrafos": items = [[oraciones...], ...]           -> carpeta/parrafo_N.wav + carpeta/oraciones/pN_NN_oracion.wav
"""

MODELO = "eleven_multilingual_v2"
import sys as _sys  # noqa: E402
from pathlib import Path as _Path  # noqa: E402
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from voces import VOZ as _VOZ  # noqa: E402  (voz elegida con la variable VOZ; ver voces.py)

VOZ_ID = _VOZ["id"]
VOZ_NOMBRE = _VOZ["nombre"]
FORMATO = "wav_48000"  # WAV PCM 16 bits, mono, 48 kHz (sin pérdida)
SEMILLA = 1234
# Tomas regeneradas con otra semilla y tomas compuestas: propias de cada voz (voces.py).
SEMILLA_POR_TOMA = _VOZ["semilla_por_toma"]
TOMAS_COMPUESTAS = _VOZ["tomas_compuestas"]

# Texto que se envía a la voz cuando difiere de la unidad escrita (el archivo conserva el nombre original).
TEXTO_TTS = {
    "Dra": "Drá.",  # "Dra." es la abreviatura de "Doctora": la voz leía "doctora"
}

AJUSTES_NEUTROS = {
    "stability": 0.80,
    "similarity_boost": 0.90,
    "style": 0.0,
    "use_speaker_boost": True,
    "speed": 1.0,
}
# Bloque 6 (preguntas/exclamaciones): extremo expresivo del rango pedido
AJUSTES_PROSODIA = {
    "stability": 0.75,
    "similarity_boost": 0.90,
    "style": 0.10,
    "use_speaker_boost": True,
    "speed": 1.0,
}


def _s(texto):
    """'Ba. Be. Bi.' -> ['Ba', 'Be', 'Bi']"""
    return [t.strip() for t in texto.split(".") if t.strip()]


def _familias(texto, nombres):
    unidades = _s(texto)
    assert len(unidades) == 5 * len(nombres), (len(unidades), nombres)
    return [(n, unidades[i * 5:(i + 1) * 5]) for i, n in enumerate(nombres)]


BLOQUES = [
    {
        "id": 1,
        "nombre": "Vocales y sílabas directas",
        "archivo": "bloque_1_vocales_y_silabas_directas",
        "previous_text": "Ahora vamos a practicar las sílabas en español.",
        "voice_settings": AJUSTES_NEUTROS,
        "por_tomas": True,
        "secciones": [
            {"id": "vocales", "carpeta": "01_vocales", "modo": "familias",
             "contexto": "Hola. Vamos a aprender las vocales en español.",
             "items": [("vocales", _s("A. E. I. O. U."))], "familia_en_raiz": True},
            {"id": "silabas_directas", "carpeta": "02_silabas_directas", "modo": "familias",
             "items": _familias(
                 "Ba. Be. Bi. Bo. Bu. Pa. Pe. Pi. Po. Pu. Ma. Me. Mi. Mo. Mu. Fa. Fe. Fi. Fo. Fu. "
                 "Va. Ve. Vi. Vo. Vu. Ta. Te. Ti. To. Tu. Da. De. Di. Do. Du. Na. Ne. Ni. No. Nu. "
                 "Ña. Ñe. Ñi. Ño. Ñu. La. Le. Li. Lo. Lu. Ra. Re. Ri. Ro. Ru. Sa. Se. Si. So. Su. "
                 "Ja. Je. Ji. Jo. Ju. Cha. Che. Chi. Cho. Chu. Ya. Ye. Yi. Yo. Yu. Ca. Que. Qui. Co. Cu. "
                 "Ga. Gue. Gui. Go. Gu. Za. Ce. Ci. Zo. Zu. Ka. Ke. Ki. Ko. Ku. Wa. We. Wi. Wo. Wu. "
                 "Lla. Lle. Lli. Llo. Llu. Rra. Rre. Rri. Rro. Rru.",
                 ["b", "p", "m", "f", "v", "t", "d", "n", "ny", "l", "r", "s", "j", "ch", "y",
                  "c", "g", "z", "k", "w", "ll", "rr"])},
        ],
    },
    {
        "id": 2,
        "nombre": "Sílabas inversas y grupos consonánticos",
        "archivo": "bloque_2_silabas_inversas_y_grupos_consonanticos",
        "previous_text": "Ahora vamos a practicar las sílabas inversas en español.",
        "voice_settings": AJUSTES_NEUTROS,
        "por_tomas": True,
        "secciones": [
            {"id": "silabas_inversas", "carpeta": "03_silabas_inversas", "modo": "familias",
             "items": _familias(
                 "Al. El. Il. Ol. Ul. Ar. Er. Ir. Or. Ur. As. Es. Is. Os. Us. An. En. In. On. Un. "
                 "Am. Em. Im. Om. Um. Ab. Eb. Ib. Ob. Ub. Ap. Ep. Ip. Op. Up. At. Et. It. Ot. Ut. "
                 "Ac. Ec. Ic. Oc. Uc. Ad. Ed. Id. Od. Ud. Af. Ef. If. Of. Uf. Ag. Eg. Ig. Og. Ug. "
                 "Az. Ez. Iz. Oz. Uz.",
                 ["l", "r", "s", "n", "m", "b", "p", "t", "c", "d", "f", "g", "z"])},
            {"id": "grupos_consonanticos", "carpeta": "04_grupos_consonanticos", "modo": "familias",
             "contexto": "Ahora vamos a practicar las sílabas con dos consonantes en español.",
             "items": _familias(
                 "Bra. Bre. Bri. Bro. Bru. Cra. Cre. Cri. Cro. Cru. Dra. Dre. Dri. Dro. Dru. "
                 "Fra. Fre. Fri. Fro. Fru. Gra. Gre. Gri. Gro. Gru. Pra. Pre. Pri. Pro. Pru. "
                 "Tra. Tre. Tri. Tro. Tru. Bla. Ble. Bli. Blo. Blu. Cla. Cle. Cli. Clo. Clu. "
                 "Fla. Fle. Fli. Flo. Flu. Gla. Gle. Gli. Glo. Glu. Pla. Ple. Pli. Plo. Plu.",
                 ["br", "cr", "dr", "fr", "gr", "pr", "tr", "bl", "cl", "fl", "gl", "pl"])},
        ],
    },
    {
        "id": 3,
        "nombre": "Combinaciones vocálicas y palabras cortas",
        "archivo": "bloque_3_combinaciones_vocalicas_y_palabras_cortas",
        "previous_text": "Ahora vamos a practicar palabras en español.",
        "voice_settings": AJUSTES_NEUTROS,
        "por_tomas": True,
        "secciones": [
            {"id": "combinaciones_vocalicas", "carpeta": "05_combinaciones_vocalicas", "modo": "plano",
             "contexto": "Ahora vamos a practicar las combinaciones de vocales en español.",
             "items": _s("Ai. Ei. Oi. Ui. Au. Eu. Ou. Ia. Ie. Io. Iu. Ua. Ue. Uo.")},
            {"id": "palabras_diptongos_hiatos", "carpeta": "06_palabras_diptongos_hiatos", "modo": "plano",
             "items": _s("Aéreo. Poeta. Teatro. País. Raíz. Baúl. Caída. Maíz. Río. Día. Frío. María. "
                         "Vehículo. Ruido. Ciudad. Cuidado. Causa. Peine. Cielo. Puerta. Fuego.")},
            {"id": "palabras_cortas", "carpeta": "07_palabras_cortas", "modo": "plano",
             "items": _s("Casa. Cama. Cara. Calle. Carro. Perro. Gato. Mesa. Silla. Puerta. Ventana. "
                         "Pato. Pelota. Pájaro. Mano. Dedo. Cabeza. Boca. Nariz. Ojo. Oreja. Sol. Luna. "
                         "Cielo. Tierra. Agua. Fuego. Aire. Mar. Río. Árbol. Flor. Pan. Sal. Miel. Leche. "
                         "Queso. Carne. Fruta. Azúcar. Café. Té. Libro. Hoja. Lápiz. Papel. Llave. Reloj.")},
        ],
    },
    {
        "id": 4,
        "nombre": "Palabras medianas, largas y contextos difíciles",
        "archivo": "bloque_4_palabras_medianas_largas_y_dificiles",
        "previous_text": "Ahora vamos a practicar palabras en español.",
        "voice_settings": AJUSTES_NEUTROS,
        "por_tomas": True,
        "secciones": [
            {"id": "palabras_largas", "carpeta": "08_palabras_medianas_y_largas", "modo": "plano",
             "items": _s("Computadora. Teléfono. Pantalla. Teclado. Música. Película. Persona. Palabra. "
                         "Sonido. Silencio. Mañana. Tarde. Noche. Temprano. Lentamente. Rápidamente. "
                         "Cuidadosamente. Probablemente. Completamente. Inteligencia. Pronunciación. "
                         "Comunicación. Tecnología. Conocimiento. Extraordinario. Responsabilidad. "
                         "Oportunidad. Imaginación. Ferrocarril. Ferretería. Circunstancia. "
                         "Infraestructura. Electricidad. Transparencia. Transformación. "
                         "Desafortunadamente. Incomprensible. Aproximadamente. Extraordinariamente. "
                         "Anticonstitucional.")},
            {"id": "palabras_r_rr", "carpeta": "09_palabras_r_y_rr", "modo": "plano",
             "items": _s("Rana. Rama. Rosa. Río. Rueda. Reloj. Ratón. Rápido. Realidad. Riqueza. Cara. "
                         "Pera. Loro. Arena. Corona. Mariposa. Amarillo. Ahora. Mirar. Barato. Carro. "
                         "Perro. Torre. Tierra. Guitarra. Barrera. Carrera. Carretera.")},
            {"id": "palabras_contraste", "carpeta": "10_palabras_contraste_bv_sz_gj", "modo": "plano",
             "items": _s("Baca. Vaca. Bello. Vello. Tubo. Tuvo. Votar. Botar. Bienes. Vienes. Casa. "
                         "Caza. Cocer. Coser. Cima. Sima. Tasa. Taza. Abrazar. Abrasar. Gente. Gigante. "
                         "General. Gimnasio. Girasol. Guitarra. Guerra. Guiso. Pingüino. Vergüenza. "
                         "Jamón. Jabón. Jardín. Jirafa. Joven. Jueves. Reloj. Trabajo. Ejercicio.")},
        ],
    },
    {
        "id": 5,
        "nombre": "Frases neutras y de continuidad",
        "archivo": "bloque_5_frases_neutras_y_de_continuidad",
        "previous_text": "Ahora vamos a leer frases en español.",
        "voice_settings": AJUSTES_NEUTROS,
        "secciones": [
            {"id": "frases_cortas", "carpeta": "11_frases_cortas", "modo": "frases",
             "items": [f + "." for f in _s(
                 "El sol sale por la mañana. La luna aparece por la noche. El agua está fría. "
                 "La casa tiene una puerta grande. El perro corre por el jardín. El gato duerme sobre "
                 "la silla. La niña juega con una pelota. El hombre abre la ventana. La música suena "
                 "suavemente. El teléfono está sobre la mesa. El libro tiene muchas páginas. "
                 "La computadora está encendida.")]},
            {"id": "parrafos", "carpeta": "12_parrafos", "modo": "parrafos",
             "items": [
                 ["Estoy leyendo este texto con una voz natural.",
                  "Cada palabra tiene un ritmo diferente.",
                  "Algunas frases son cortas.",
                  "Otras son mucho más largas y necesitan pequeñas pausas para que se entiendan correctamente."],
                 ["La inteligencia artificial permite desarrollar nuevas herramientas para comunicarnos.",
                  "Una voz sintética puede transformar un texto escrito en palabras habladas, utilizando "
                  "sonidos, pausas y diferentes patrones de entonación."],
                 ["Cuando una persona lee un libro, no pronuncia todas las palabras de la misma manera.",
                  "Cambia el ritmo, respira, hace pausas y adapta la entonación según el significado de "
                  "cada oración."],
                 ["La mañana comenzaba lentamente.",
                  "Los primeros rayos del sol iluminaban las calles, mientras el viento movía las hojas "
                  "de los árboles.",
                  "A lo lejos, se escuchaba el ruido de un automóvil que avanzaba por una carretera casi vacía."],
                 ["La tecnología ha cambiado la manera en que las personas acceden a la información.",
                  "Actualmente, los dispositivos electrónicos permiten almacenar miles de libros, consultar "
                  "documentos y escuchar contenidos en cualquier momento."],
             ]},
        ],
    },
    {
        "id": 6,
        "nombre": "Variante prosódica: preguntas y exclamaciones",
        "archivo": "bloque_6_preguntas_y_exclamaciones",
        "previous_text": "Ahora vamos a practicar preguntas y exclamaciones en español.",
        "voice_settings": AJUSTES_PROSODIA,
        "secciones": [
            {"id": "preguntas", "carpeta": "13_preguntas", "modo": "frases",
             "items": ["¿Dónde estás?", "¿Qué estás haciendo?", "¿Cuándo vas a volver?",
                       "¿Por qué pasó eso?", "¿Cómo podemos solucionarlo?", "¿Quién llamó por teléfono?",
                       "¿Cuánto tiempo tenemos?", "¿Cuál es la respuesta correcta?"]},
            {"id": "exclamaciones", "carpeta": "14_exclamaciones", "modo": "frases",
             "items": ["¡Qué alegría verte!", "¡No puedo creerlo!", "¡Eso es increíble!", "¡Cuidado!",
                       "¡Detente ahora!", "¡Qué hermoso día!"]},
        ],
    },
]


def texto_tts(u):
    """Texto que se envía para una unidad: sílabas/palabras llevan punto final."""
    if u in TEXTO_TTS:
        return TEXTO_TTS[u]
    return u if u[-1] in ".?!" else u + "."


def construir_texto(bloque):
    """Devuelve (texto_completo, unidades) donde cada unidad trae su rango de caracteres.

    Las unidades se separan con una línea en blanco (pausa natural, fácil de recortar).
    En los párrafos, las oraciones van seguidas (lectura continua) y los párrafos se separan
    con línea en blanco.
    """
    partes, unidades, pos = [], [], 0

    def agregar(fragmento, **meta):
        nonlocal pos
        if partes:
            partes.append("\n\n")
            pos += 2
        ini = pos
        partes.append(fragmento)
        pos += len(fragmento)
        unidades.append(dict(meta, texto=fragmento, ini=ini, fin=pos))

    for sec in bloque["secciones"]:
        if sec["modo"] == "familias":
            for grupo, us in sec["items"]:
                for u in us:
                    agregar(texto_tts(u), seccion=sec["id"], grupo=grupo, unidad=u)
        elif sec["modo"] in ("plano", "frases"):
            for i, u in enumerate(sec["items"], 1):
                agregar(texto_tts(u), seccion=sec["id"], indice=i, unidad=u)
        elif sec["modo"] == "parrafos":
            for p, oraciones in enumerate(sec["items"], 1):
                fragmento = " ".join(oraciones)
                agregar(fragmento, seccion=sec["id"], parrafo=p, unidad=fragmento, es_parrafo=True)
                base = unidades[-1]["ini"]
                off = 0
                for o_i, o in enumerate(oraciones, 1):
                    k = fragmento.index(o, off)
                    unidades.append(dict(seccion=sec["id"], parrafo=p, oracion=o_i, unidad=o, texto=o,
                                         ini=base + k, fin=base + k + len(o), dentro_de_parrafo=True))
                    off = k + len(o)
    return "".join(partes), unidades
