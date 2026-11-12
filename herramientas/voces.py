"""Voces del proyecto. Se elige con la variable VOZ (por defecto "martin"):

  VOZ=sara python3 herramientas/generar.py
  VOZ=sara python3 herramientas/empaquetar.py

Cada voz guarda sus audios en voces/<carpeta>/ (biblioteca/, lectura/, fuente/) y su caché en trabajo/<carpeta>/.
Las correcciones de tomas (semillas, tomas compuestas) son propias de cada voz: lo que falla con una voz no tiene
por qué fallar con otra, así que se revisan voz por voz con verificar.py y buscar_semillas.py.
"""
import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Notas de pronunciación para los README (según el acento de la voz)
NOTAS_DIALECTO = {
    "españa": {
        "acento": "español de España",
        "notas": (
            "## Notas de pronunciación (voz de España)\n\n"
            "- **Z y C ante e/i** (za, ce, ci, zo, zu, az, ez…): suenan /θ/, como en España, distinto de la S. Si la app "
            "es para Latinoamérica, conviene una voz con seseo (por ejemplo Lumina).\n"
            "- **LL e Y** suenan igual (yeísmo). **B y V** suenan igual, que es lo correcto en español.\n"
            "- **Ag, Eg, Ig, Og, Ug:** la G final sale suave [ɣ], como en \"i**g**norar\" o \"di**g**no\". Es la "
            "pronunciación natural, pero conviene escucharlas por si preferís una G más marcada."),
        "limitacion": "- **Voz de España:** la z y la c ante e/i suenan /θ/.",
    },
    "latinoamericano": {
        "acento": "español latinoamericano neutro",
        "notas": (
            "## Notas de pronunciación (voz latinoamericana)\n\n"
            "- **Seseo:** la Z y la C ante e/i suenan como la S (za = sa, ce = se), como en toda Latinoamérica. Por eso "
            "en `10_palabras_contraste_bv_sz_gj/` los pares casa/caza, coser/cocer, sima/cima, tasa/taza y "
            "abrasar/abrazar suenan igual: sirven para practicar cómo se escriben, no para distinguirlos de oído.\n"
            "- **LL e Y** suenan igual (yeísmo). **B y V** suenan igual, que es lo correcto en español.\n"
            "- **J:** suave, como se dice en Colombia y gran parte de Latinoamérica (más aspirada que la jota de España).\n"
            "- **Ag, Eg, Ig, Og, Ug:** la G final sale suave y aspirada, parecida a una J corta (Scribe la oye \"ach\"). "
            "Al final de sílaba la G del español es débil (como en \"i**g**norar\"), así que es esperable. Se probaron "
            "otras semillas y salían \"ak\", que se confunde con la C, así que se dejó esta. Conviene escucharlas."),
        "limitacion": ("- **Seseo:** la voz es latinoamericana, así que \"caza\" y \"casa\" suenan igual, que es lo "
                       "correcto en Latinoamérica."),
    },
}

VOCES = {
    # Voz principal: latinoamericana neutra (seseo: "casa" y "caza" suenan igual), tono muy parejo entre palabras
    # (empalma mejor) y audio limpio. Elegida entre 8 voces en una audición (ver VOCES.md).
    "lumina": {
        "id": "x5IDPSl4ZUbhosMmVFTk",
        "nombre": "Lumina - Neutral and Clear",
        "carpeta": "lumina",
        "rango_f0": (120, 400),
        "dialecto": "latinoamericano",
        "descripcion": "femenina, Latinoamérica (Colombia, acento neutro); clara, pareja y limpia",
        # habla algo rápido: palabras, frases y lectura se generan al 90 % (letras y sílabas al 100 %, más claras)
        "velocidad_bloques": {3: 0.9, 4: 0.9, 5: 0.9, 6: 0.9},
        "velocidad_lectura": 0.9,
        # versión final regrabada ("w."): con 1234 tenían un sonido de más al final ("buena a eso", "leo es…")
        "semilla_palabras": {"buena.": 7, "leo.": 7, "vaso.": 7, "fresa.": 7, "están.": 7},
        "semilla_por_toma": {
            "Za. Ce. Ci. Zo. Zu.": 7,      # con 1234 las cinco salían pegadas, sin pausa (se cortaba mal la S)
            "At. Et. It. Ot. Ut.": 7,      # con 1234 "At" sonaba "ate" (vocal agregada)
        },
        # Cada sílaba se toma de la mejor de varias tomas: (texto enviado, semilla, posición de la unidad en esa toma).
        "tomas_compuestas": {
            # Leía "Ca." como "Sa". Con K suena /ka/.
            "Ca. Que. Qui. Co. Cu.": [("Ka.\n\nQue.\n\nQui.\n\nCo.\n\nCu.", 1234, 0)]
                                     + [("Ca.\n\nQue.\n\nQui.\n\nCo.\n\nCu.", 1234, k) for k in range(1, 5)],
            # Sola, la J salía como la "ch" o la "j" del inglés (che, chi, cho, chu). Precedida por una palabra en
            # español ("Jefe. Je.") sale la jota: velar ante a, o, u y palatal suave ante e, i.
            "Ja. Je. Ji. Jo. Ju.": [("Jamón.\n\nJa.\n\nJefe.\n\nJe.\n\nJirafa.\n\nJi.\n\nJoya.\n\nJo.\n\nJugo.\n\nJu.", s, i)
                                    for s, i in [(1234, 1), (7, 3), (7, 5), (7, 7), (7, 9)]],
            # Agregaba una vocal ("ace", "ice", "o-se", "uce"). Con K o con tilde sale /ak/, /ek/, /ik/, /ok/, /uk/.
            "Ac. Ec. Ic. Oc. Uc.": [("Ak.\n\nEk.\n\nIk.\n\nOk.\n\nUk.", 1234, k) for k in range(3)]
                                   + [("Óc.\n\nÓc.\n\nÓc.", 1234, 1), ("Uc.\n\nUc.\n\nUc.", 1234, 1)],
            # Leía "Az." como "acento". Con seseo "az" suena igual que "as": se usa la toma de As.
            "Az. Ez. Iz. Oz. Uz.": [("As.\n\nEs.\n\nIs.\n\nOs.\n\nUs.", 1234, 0)]
                                   + [("Az.\n\nEz.\n\nIz.\n\nOz.\n\nUz.", 1234, k) for k in range(1, 5)],
        },
        "correcciones": (
            '- **Ca:** la voz la leía "sa". Se grabó como "Ka", que suena igual.\n'
            '- **Ja, Je, Ji, Jo, Ju:** sola, la J salía como "ch" (che, chi, cho, chu). Cada sílaba se grabó después '
            'de una palabra que la usa ("Jamón. Ja.", "Jefe. Je."…) y se recortó solo la sílaba.\n'
            '- **Za, Ce, Ci, Zo, Zu:** salían pegadas, sin pausa entre una y otra. Se regrabaron con otra semilla.\n'
            '- **Ac, Ic, Oc, Uc:** tenían una vocal agregada ("ace", "ice"…). Se tomaron de tomas escritas con K o con '
            'tilde, que suenan igual: /ak/, /ek/, /ik/, /ok/, /uk/.\n'
            '- **At:** sonaba "ate". Se regrabó con otra semilla.\n'
            '- **Az:** la voz leía "acento". Con seseo "az" suena igual que "as", así que se usa esa grabación.'),
        "atencion": ("la familia `02_silabas_directas/j/` (la J de esta voz es suave, como en Colombia) y la familia "
                     "inversa `03_silabas_inversas/g/` (la G final sale suave y aspirada)."),
    },
    "martin": {
        "id": "Vpv1YgvVd6CHIzOTiTt8",
        "nombre": "Martin Osborne - Deep and Passionate",
        "carpeta": "martin_osborne",
        "rango_f0": (55, 220),     # voz muy grave (~67 Hz), con tramos "rasposos"
        "descripcion": "masculina, España (castellano)",
        "correcciones": (
            '- **Af, Az:** tenían una vocal agregada ("afe", "a-ce…"). Se regrabaron con otra semilla.\n'
            '- **Dra, Dre…:** con la semilla original "Dra" y "Dre" quedaban pegadas. Se regrabó con otra semilla.\n'
            '- **Ac, Ec, Ic, Oc, Uc:** la voz decía "az" y "uke". Cada sílaba se tomó de la mejor de varias tomas (con K, '
            'que suena igual) y ahora suenan /ak/, /ek/, /ik/, /ok/, /uk/.\n'
            '- **Sima, Tasa, Taza, Abrazar, Abrasar:** se regrabaron con otra semilla porque "Abrasar" arrancaba con una '
            '"a" de más.'),
        "atencion": "las familias inversas `03_silabas_inversas/g/` y `c/`, y `03_silabas_inversas/z/`.",
        # Tomas que se regeneraron con otra semilla porque la original tenía un defecto. Clave: texto de la toma.
        "semilla_por_toma": {
            "Az. Ez. Iz. Oz. Uz.": 7,                    # con 1234 "Az" sonaba "a-ce-..." (vocal agregada)
            "Af. Ef. If. Of. Uf.": 7,                    # con 1234 "Af" sonaba "afe"
            "Drá. Dre. Dri. Dro. Dru.": 7,               # con 1234 "Dra/Dre" quedaban pegadas
            "Sima. Tasa. Taza. Abrazar. Abrasar.": 42,   # con 1234 "Abrasar" arrancaba con una "a" de más
        },
        # Tomas armadas eligiendo cada sílaba de la mejor toma candidata (texto_fuente, semilla, índice).
        # Familia inversa con C: esta voz dice "Ac" como [aθ] y agrega vocal en "Uc" ("uke"); se usan tomas
        # escritas con K (suena igual: /k/) y una toma de repetición para "Uc".
        "tomas_compuestas": {
            "Ac. Ec. Ic. Oc. Uc.": [
                ("Ak.\n\nEk.\n\nIk.\n\nOk.\n\nUk.", 2024, 0),  # Ac  -> [ak] con explosión final
                ("Ac.\n\nEc.\n\nIc.\n\nOc.\n\nUc.", 7, 1),     # Ec
                ("Ak.\n\nEk.\n\nIk.\n\nOk.\n\nUk.", 7, 2),     # Ic  -> [ik]
                ("Ac.\n\nEc.\n\nIc.\n\nOc.\n\nUc.", 7, 3),     # Oc
                ("Uc.\n\nUc.\n\nUc.", 7, 1),                   # Uc  -> [uk] sin vocal agregada
            ],
        },
    },
    "sara": {
        "id": "KHCvMklQZZo0O30ERnVn",
        "nombre": "Sara Martin - Gentle and Layered",
        "carpeta": "sara_martin",
        # Palabras de la lectura grabadas con otra semilla: con 1234, "a" salía "ia" (sonaba "voy a" al empezar).
        "semilla_palabras": {"a": 7},
        "rango_f0": (120, 400),
        "descripcion": "femenina, España (castellano); tono amable, recomendada para contenido educativo",
        "correcciones": (
            '- **Ac, Az:** salían con una vocal agregada ("ace", "aze"). Se tomaron de una toma donde la sílaba se '
            'repite ("Ac. Ac. Ac.") y sale limpia; el resto de cada familia quedó de la toma original.'),
        "atencion": ("la familia inversa `03_silabas_inversas/g/` (la G final sale suave) y las primeras sílabas de "
                     "`03_silabas_inversas/c/` y `z/`, que vienen de otra toma."),
        "semilla_por_toma": {},
        # "Ac" y "Az" salían con vocal agregada ("ace", "aze") en la toma de la familia: se toman de una toma
        # de repetición ("Ac. Ac. Ac.") donde salen limpias; el resto de cada familia queda de la toma original.
        "tomas_compuestas": {
            "Ac. Ec. Ic. Oc. Uc.": [("Ac.\n\nAc.\n\nAc.", 7, 1)]
            + [("Ac.\n\nEc.\n\nIc.\n\nOc.\n\nUc.", 1234, k) for k in range(1, 5)],
            "Az. Ez. Iz. Oz. Uz.": [("Az.\n\nAz.\n\nAz.", 7, 0)]
            + [("Az.\n\nEz.\n\nIz.\n\nOz.\n\nUz.", 1234, k) for k in range(1, 5)],
        },
    },
    # Pendientes (anotadas para más adelante, masculinas):
    "salva": {
        "id": "hyKxCTlAqtnW188CgltM",
        "nombre": "Salva - The Spanish Narrator",
        "carpeta": "salva",
        "rango_f0": (55, 250),
        "descripcion": "masculina, España (castellano); grave y cálida",
        "pendiente": True,
        "correcciones": "",
        "atencion": "",
        "semilla_por_toma": {},
        "tomas_compuestas": {},
    },
    "gabo": {
        "id": "o0SveC0zgHFuCsEO3vHR",
        "nombre": "Gabo - Deep, Evocative and Resonant",
        "carpeta": "gabo",
        "rango_f0": (55, 250),
        "descripcion": "masculina, España (castellano); grave. Alternativa latinoamericana: "
                       "4yMqddmQqI9aTy9ysF9H (Gabo - Thoughtful, Moving, and Powerful)",
        "pendiente": True,
        "correcciones": "",
        "atencion": "",
        "semilla_por_toma": {},
        "tomas_compuestas": {},
    },
}

CLAVE = os.environ.get("VOZ", "lumina")
if CLAVE not in VOCES:
    raise SystemExit(f"VOZ={CLAVE} no existe. Opciones: {', '.join(VOCES)}")
VOZ = VOCES[CLAVE]

DIR_VOZ = RAIZ / "voces" / VOZ["carpeta"]
BIBLIOTECA = DIR_VOZ / "biblioteca"
LECTURA = DIR_VOZ / "lectura"
FUENTE = DIR_VOZ / "fuente"
TRABAJO = RAIZ / "trabajo" / VOZ["carpeta"]
NOMBRE_ZIP = "voces_" + VOZ["carpeta"]
