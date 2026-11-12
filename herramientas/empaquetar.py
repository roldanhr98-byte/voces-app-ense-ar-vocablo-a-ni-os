"""Arma la entrega unificada:

  - probar_voces.html: página para importar el zip y probar letras, sílabas, palabras y textos
    (se genera desde herramientas/probador/plantilla.html con lector.js y los índices adentro).
  - voces_martin_osborne.zip con biblioteca/, lectura/, probar_voces.html y LEEME.md.

  python3 herramientas/empaquetar.py [ruta_del_zip]
"""
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from voces import BIBLIOTECA as BIB, LECTURA as LEC, NOMBRE_ZIP, NOTAS_DIALECTO, VOZ  # noqa: E402


DIALECTO = NOTAS_DIALECTO[VOZ.get("dialecto", "españa")]


def datos_lectura():
    """Cantidad de palabras, archivos de palabras y memoria (MB, enteros de 16 bits a 24 kHz) del paquete de lectura."""
    import json
    import wave
    man = LEC / "manifest_lectura.json"
    if not man.exists():
        return {}
    m = json.loads(man.read_text(encoding="utf-8"))
    seg = 0.0
    for ruta in m["audios"].values():
        with wave.open(str(LEC / ruta)) as w:
            seg += w.getnframes() / w.getframerate()
    n_arch = sum(1 for k in m["audios"] if k.startswith("palabras"))
    return {"{N_PALABRAS}": str(len(m["palabras"])), "{N_ARCHIVOS}": str(n_arch),
            "{MEMORIA}": str(int(round(seg * 24000 * 2 / 1e6 / 5) * 5))}


def plantilla(ruta):
    """Lee un README y completa los datos de la voz."""
    t = Path(ruta).read_text(encoding="utf-8")
    for k, v in datos_lectura().items():
        t = t.replace(k, v)
    for k, v in {"{VOZ_NOMBRE}": VOZ["nombre"], "{CARPETA}": NOMBRE_ZIP,
                 "{CORRECCIONES}": VOZ.get("correcciones") or "- Ninguna por ahora.",
                 "{ATENCION}": VOZ.get("atencion") or "las familias inversas.",
                 "{ACENTO}": DIALECTO["acento"], "{NOTAS_PRONUNCIACION}": DIALECTO["notas"],
                 "{LIMITACION_DIALECTO}": DIALECTO["limitacion"]}.items():
        t = t.replace(k, v)
    return t

PROBADOR = RAIZ / "herramientas" / "probador"
NOMBRE = NOMBRE_ZIP


def construir_pagina():
    """Devuelve (versión_web, versión_archivo). La web no lleva <html>/<head>/<body> (los agrega el visor)."""
    plantilla = (PROBADOR / "plantilla.html").read_text(encoding="utf-8")
    lector = (RAIZ / "herramientas" / "lectura_app" / "lector.js").read_text(encoding="utf-8")
    lector = re.sub(r"^export ", "", lector, flags=re.M)
    bib = json.loads((BIB / "manifest.json").read_text(encoding="utf-8"))
    bib = [[x["archivo"], x["texto"], x["tipo"], x.get("grupo")] for x in sorted(bib, key=lambda x: x["orden"])]
    lec = json.loads((LEC / "manifest_lectura.json").read_text(encoding="utf-8"))
    for k in ("difonos", "silabas", "marcas"):   # la página solo necesita las palabras para dibujar las fichas
        lec.pop(k, None)

    def js(o):
        return json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

    pagina = (plantilla.replace("/*@LECTOR@*/", lector)
              .replace("/*@BIB@*/null", js(bib))
              .replace("/*@LEC@*/null", js(lec)))
    cabeza, cuerpo = pagina.split("<!--@CUERPO@-->")
    web = cabeza + cuerpo
    archivo = ('<!doctype html>\n<html lang="es">\n<head>\n<meta charset="utf-8">\n'
               '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
               + cabeza + "</head>\n<body>\n" + cuerpo + "\n</body>\n</html>\n")
    return web, archivo


MP3_BIBLIOTECA = ["-ac", "1", "-ar", "48000", "-c:a", "libmp3lame", "-b:a", "64k"]   # clips sueltos
MP3_LECTURA = ["-ac", "1", "-ar", "24000", "-c:a", "libmp3lame", "-b:a", "48k"]      # voz para encadenar
CACHE_MP3 = RAIZ / "trabajo" / "mp3"


def a_mp3(origen, opciones):
    """Convierte un WAV a MP3 (con caché por contenido). Devuelve la ruta del MP3."""
    import hashlib
    import subprocess
    clave = hashlib.md5(origen.read_bytes() + " ".join(opciones).encode()).hexdigest()
    destino = CACHE_MP3 / f"{clave}.mp3"
    if not destino.exists():
        CACHE_MP3.mkdir(parents=True, exist_ok=True)
        tmp = destino.with_suffix(".tmp.mp3")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(origen), *opciones, str(tmp)], check=True)
        tmp.rename(destino)
    return destino


def main():
    from concurrent.futures import ThreadPoolExecutor
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "trabajo" / f"{NOMBRE}.zip"
    (BIB / "README.md").write_text(plantilla(RAIZ / "herramientas" / "LEEME_audios.md"), encoding="utf-8")
    (LEC / "README.md").write_text(plantilla(RAIZ / "herramientas" / "lectura_app" / "README.md"), encoding="utf-8")
    web, archivo = construir_pagina()
    (RAIZ / "probar_voces.html").write_text(archivo, encoding="utf-8")
    (RAIZ / "trabajo").mkdir(exist_ok=True)
    (RAIZ / "trabajo" / "probar_voces_web.html").write_text(web, encoding="utf-8")

    # lista de (ruta en el zip, archivo de origen o bytes)
    entradas, conversiones = [], []
    for carpeta, opciones in ((BIB, MP3_BIBLIOTECA), (LEC, MP3_LECTURA)):
        for f in sorted(carpeta.rglob("*")):
            if not f.is_file():
                continue
            rel = f"{NOMBRE}/{carpeta.name}/{f.relative_to(carpeta)}"
            if f.suffix == ".wav":
                conversiones.append((rel[:-4] + ".mp3", f, opciones))
            elif f.suffix in (".json", ".csv"):
                entradas.append((rel, f.read_text(encoding="utf-8").replace(".wav", ".mp3").encode("utf-8")))
            else:
                entradas.append((rel, f))
    with ThreadPoolExecutor(8) as ex:
        mp3 = list(ex.map(lambda c: (c[0], a_mp3(c[1], c[2])), conversiones))

    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(RAIZ / "probar_voces.html", f"{NOMBRE}/probar_voces.html")
        z.writestr(f"{NOMBRE}/LEEME.md", plantilla(PROBADOR / "LEEME.md").encode("utf-8"))
        for rel, origen in entradas:
            if isinstance(origen, bytes):
                z.writestr(rel, origen)
            else:
                z.write(origen, rel)
        for rel, origen in mp3:   # el MP3 ya está comprimido: se guarda tal cual
            z.write(origen, rel, compress_type=zipfile.ZIP_STORED)
    print(f"zip: {destino} ({destino.stat().st_size / 1e6:.1f} MB, {len(entradas) + len(mp3) + 2} archivos)")


if __name__ == "__main__":
    main()
