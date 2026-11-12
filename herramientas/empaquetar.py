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
BIB = RAIZ / "biblioteca"
LEC = RAIZ / "lectura"
PROBADOR = RAIZ / "herramientas" / "probador"
NOMBRE = "voces_martin_osborne"


def construir_pagina():
    """Devuelve (versión_web, versión_archivo). La web no lleva <html>/<head>/<body> (los agrega el visor)."""
    plantilla = (PROBADOR / "plantilla.html").read_text(encoding="utf-8")
    lector = (RAIZ / "herramientas" / "lectura_app" / "lector.js").read_text(encoding="utf-8")
    lector = re.sub(r"^export ", "", lector, flags=re.M)
    bib = json.loads((BIB / "manifest.json").read_text(encoding="utf-8"))
    bib = [[x["archivo"], x["texto"], x["tipo"], x.get("grupo")] for x in sorted(bib, key=lambda x: x["orden"])]
    lec = json.loads((LEC / "manifest_lectura.json").read_text(encoding="utf-8"))
    for d in lec["palabras"].values():
        for k in [k for k in d if k.startswith("dur_")]:
            del d[k]

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


def main():
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "trabajo" / f"{NOMBRE}.zip"
    shutil.copy(RAIZ / "herramientas" / "LEEME_audios.md", BIB / "README.md")
    web, archivo = construir_pagina()
    (RAIZ / "probar_voces.html").write_text(archivo, encoding="utf-8")
    (RAIZ / "trabajo").mkdir(exist_ok=True)
    (RAIZ / "trabajo" / "probar_voces_web.html").write_text(web, encoding="utf-8")

    destino.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.write(RAIZ / "probar_voces.html", f"{NOMBRE}/probar_voces.html")
        z.write(PROBADOR / "LEEME.md", f"{NOMBRE}/LEEME.md")
        for carpeta in (BIB, LEC):
            for f in sorted(carpeta.rglob("*")):
                if f.is_file():
                    z.write(f, f"{NOMBRE}/{carpeta.name}/{f.relative_to(carpeta)}")
                    n += 1
    print(f"zip: {destino} ({destino.stat().st_size / 1e6:.1f} MB, {n + 2} archivos)")


if __name__ == "__main__":
    main()
