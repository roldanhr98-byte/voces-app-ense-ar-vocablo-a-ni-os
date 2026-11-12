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

VOCES = {
    "martin": {
        "id": "Vpv1YgvVd6CHIzOTiTt8",
        "nombre": "Martin Osborne - Deep and Passionate",
        "carpeta": "martin_osborne",
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
        "descripcion": "masculina, España (castellano); grave. Alternativa latinoamericana: "
                       "4yMqddmQqI9aTy9ysF9H (Gabo - Thoughtful, Moving, and Powerful)",
        "pendiente": True,
        "correcciones": "",
        "atencion": "",
        "semilla_por_toma": {},
        "tomas_compuestas": {},
    },
}

CLAVE = os.environ.get("VOZ", "martin")
if CLAVE not in VOCES:
    raise SystemExit(f"VOZ={CLAVE} no existe. Opciones: {', '.join(VOCES)}")
VOZ = VOCES[CLAVE]

DIR_VOZ = RAIZ / "voces" / VOZ["carpeta"]
BIBLIOTECA = DIR_VOZ / "biblioteca"
LECTURA = DIR_VOZ / "lectura"
FUENTE = DIR_VOZ / "fuente"
TRABAJO = RAIZ / "trabajo" / VOZ["carpeta"]
NOMBRE_ZIP = "voces_" + VOZ["carpeta"]
