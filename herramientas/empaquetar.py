"""Copia el README, genera escuchar.html (página para probar los audios) y arma el zip.

  python3 herramientas/empaquetar.py [ruta_del_zip]
"""
import html
import json
import shutil
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
AUDIOS = RAIZ / "audios"
NOMBRE_CARPETA = "voces_abecedario_martin_osborne"

TITULOS = {
    "00_renders_bloques_completos": "Renders de los bloques completos",
    "01_vocales": "Vocales",
    "02_silabas_directas": "Sílabas directas",
    "03_silabas_inversas": "Sílabas inversas",
    "04_grupos_consonanticos": "Grupos consonánticos",
    "05_combinaciones_vocalicas": "Combinaciones vocálicas",
    "06_palabras_diptongos_hiatos": "Palabras con diptongos e hiatos",
    "07_palabras_cortas": "Palabras cortas",
    "08_palabras_medianas_y_largas": "Palabras medianas y largas",
    "09_palabras_r_y_rr": "Palabras con R y RR",
    "10_palabras_contraste_bv_sz_gj": "Contrastes B/V, S/Z, G/J",
    "11_frases_cortas": "Frases cortas",
    "12_parrafos": "Párrafos",
    "13_preguntas": "Preguntas",
    "14_exclamaciones": "Exclamaciones",
}


def pagina(manifiesto):
    secciones = {}
    for m in manifiesto:
        carpeta = m["archivo"].split("/")[0]
        if m["tipo"] == "familia":
            grupo = f"{carpeta}/{m['grupo']}"
        elif m["tipo"] == "unidad" and m.get("grupo"):
            grupo = f"{carpeta}/{m['grupo']}"
        else:
            grupo = carpeta
        secciones.setdefault(carpeta, {}).setdefault(grupo, []).append(m)

    def boton(m):
        etiqueta = m["texto"] if m["tipo"] != "familia" else "▶ " + m["texto"].replace(".", "")
        clase = "fam" if m["tipo"] == "familia" else ("largo" if len(m["texto"]) > 24 else "")
        return (f'<button class="{clase}" data-src="{html.escape(m["archivo"])}" '
                f'title="{html.escape(m["archivo"])}">{html.escape(etiqueta)}</button>')

    partes = []
    for carpeta in sorted(secciones):  # las carpetas llevan número; los grupos quedan en orden de aparición
        partes.append(f'<section><h2>{html.escape(TITULOS.get(carpeta, carpeta))}'
                      f' <small>{carpeta}/</small></h2>')
        for grupo, items in secciones[carpeta].items():
            items = sorted(items, key=lambda m: (m["tipo"] == "familia", m["orden"]))
            if grupo != carpeta:
                partes.append(f'<div class="grupo"><span class="letra">{html.escape(grupo.split("/")[1])}</span>')
            else:
                partes.append('<div class="grupo">')
            partes.append("".join(boton(m) for m in items) + "</div>")
        partes.append("</section>")

    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Escuchar voces</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#1d1b18; --muted:#6b665e; --card:#fff; --line:#e6e1d8; --acc:#2f6fdf; --acc-fg:#fff; --fam:#eef3fd; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#16181c; --fg:#ecebe8; --muted:#9a9790; --card:#20232a; --line:#30343c; --acc:#7aa7ff; --acc-fg:#0d1320; --fam:#1d2638; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:16px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; }}
header {{ position:sticky; top:0; background:var(--bg); border-bottom:1px solid var(--line); padding:14px 16px; z-index:2; }}
header h1 {{ margin:0; font-size:20px; }}
header p {{ margin:4px 0 0; color:var(--muted); font-size:14px; }}
#ahora {{ font-weight:600; color:var(--acc); }}
main {{ max-width:1100px; margin:0 auto; padding:8px 16px 48px; }}
h2 {{ font-size:18px; margin:28px 0 10px; }}
h2 small {{ color:var(--muted); font-weight:400; font-size:13px; }}
.grupo {{ display:flex; flex-wrap:wrap; gap:8px; align-items:center; padding:8px 0; border-top:1px solid var(--line); }}
.letra {{ min-width:38px; font-weight:700; text-transform:uppercase; color:var(--muted); }}
button {{ font:inherit; font-size:17px; padding:9px 14px; border-radius:10px; border:1px solid var(--line); background:var(--card); color:var(--fg); cursor:pointer; }}
button:hover {{ border-color:var(--acc); }}
button.fam {{ background:var(--fam); font-size:14px; }}
button.largo {{ font-size:14px; text-align:left; max-width:100%; }}
button.sonando {{ background:var(--acc); color:var(--acc-fg); border-color:var(--acc); }}
</style></head>
<body>
<header><h1>Voces: Martin Osborne (ElevenLabs)</h1>
<p>Tocá cualquier botón para escucharlo. Sonando: <span id="ahora">—</span></p></header>
<main>{''.join(partes)}</main>
<script>
const audio = new Audio(); let actual = null;
document.addEventListener("click", e => {{
  const b = e.target.closest("button[data-src]"); if (!b) return;
  if (actual) actual.classList.remove("sonando");
  actual = b; b.classList.add("sonando");
  document.getElementById("ahora").textContent = b.getAttribute("data-src");
  audio.src = b.getAttribute("data-src"); audio.currentTime = 0; audio.play();
}});
audio.addEventListener("ended", () => {{ if (actual) actual.classList.remove("sonando"); }});
</script>
</body></html>
"""


def main():
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "trabajo" / f"{NOMBRE_CARPETA}.zip"
    manifiesto = json.loads((AUDIOS / "manifest.json").read_text(encoding="utf-8"))
    shutil.copy(RAIZ / "herramientas" / "LEEME_audios.md", AUDIOS / "README.md")
    (AUDIOS / "escuchar.html").write_text(pagina(manifiesto), encoding="utf-8")
    destino.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(AUDIOS.rglob("*")):
            if f.is_file():
                z.write(f, f"{NOMBRE_CARPETA}/{f.relative_to(AUDIOS)}")
    print(f"zip: {destino} ({destino.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
