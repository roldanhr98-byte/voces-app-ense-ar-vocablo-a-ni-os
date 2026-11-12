/*
 * Lector encadenado — arma y reproduce sílabas, palabras y oraciones con los audios de esta carpeta.
 *
 *   import { Lector } from "./lector.js";
 *   const lector = await Lector.crear("lectura/");      // carga los 3 audios una sola vez (~1 s la primera vez)
 *   await lector.leerOracion("hoy me voy de vacaciones a la casa de mi tío");   // cualquier orden
 *   await lector.leerSilabas("vaca");                     // va - ca
 *   await lector.leerPalabra("vaca");                     // vaca
 *   await lector.leerSecuencia([["silabas", "vaca"], ["palabra", "vaca"],
 *                               ["silabas", "la vaca"], ["oracion", "la vaca come pasto"]]);
 *
 * Cómo arma la lectura:
 *  - Palabras del banco: versión "medio" (como suena dentro de una oración) y "final" para la última.
 *  - Palabras que no están grabadas o mal escritas: primero se busca una que suene igual (baca → vaca);
 *    si no hay, se arma con dífonos (transiciones entre sonidos) respetando la sílaba acentuada.
 *  - Empalmes según los sonidos que se tocan: antes de p/t/k/ch un silencio corto (el de esa consonante),
 *    vocal + vocal se funden, el resto con un solape corto y fundido de potencia constante.
 *  - Todo se arma en memoria, sin esperas: después de crear el lector cada lectura es instantánea.
 *
 * Mismas reglas que herramientas/fonetica.py y herramientas/lectura.py (los ejemplos se arman con esos).
 * En móviles el audio solo arranca después de un toque del usuario (regla del navegador).
 */

const VOCALES = "aeiouáéíóúü";
const FUERTES = "aeoáéíóú";
const INSEPARABLES = new Set(["pr", "br", "tr", "dr", "cr", "kr", "gr", "fr", "pl", "bl", "cl", "kl", "gl", "fl"]);
const TILDE = { "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ü": "u" };
const VOC = "aeiou";
const CORTE_EN_CIERRE = "ptkC";
const SUSTITUTOS = { R: "r", r: "R", N: "n", Y: "J", C: "t", Z: "s", J: "x", x: "J" };

const muestras = (seg, sr) => Math.floor(seg * sr + 0.5);
const clase = (s) => (VOC.includes(s[0]) ? "v" : CORTE_EN_CIERRE.includes(s[0]) ? "c" : "o");

/* ------------------------------------------------------------------ texto -> sonidos */
export function sinTildes(t) {
  return t.replace(/ñ/g, "\0").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\0/g, "ñ");
}

export function silabear(palabra) {
  const w = palabra.toLowerCase();
  const u = [];
  for (let i = 0; i < w.length;) {
    const dos = w.slice(i, i + 2);
    if (["ch", "ll", "rr"].includes(dos)) { u.push(dos); i += 2; }
    else if (dos === "qu" || ((dos === "gu" || dos === "gü") && i + 2 < w.length && "eiéí".includes(w[i + 2]))) {
      u.push(dos); i += 2;
    } else { u.push(w[i]); i += 1; }
  }
  const esVocal = (x) => x.length === 1 && VOCALES.includes(x);
  const sil = [];
  let actual = "";
  let k = 0;
  while (k < u.length) {
    const x = u[k];
    if (esVocal(x)) {
      actual += x;
      if (k + 1 < u.length && esVocal(u[k + 1])) {
        const y = u[k + 1];
        const hiato = (FUERTES.includes(x) && FUERTES.includes(y)) || "íú".includes(x) || "íú".includes(y);
        if (hiato) { sil.push(actual); actual = ""; }
      }
      k += 1;
      continue;
    }
    let j = k;
    while (j < u.length && !esVocal(u[j])) j += 1;
    const grupo = u.slice(k, j);
    if (j === u.length || !actual) {
      actual += grupo.join("");
    } else {
      let corte;
      if (grupo.length === 1) corte = 0;
      else if (grupo.length === 2) corte = INSEPARABLES.has(grupo.join("")) ? 0 : 1;
      else if (grupo.length === 3) corte = INSEPARABLES.has(grupo.slice(1).join("")) ? 1 : 2;
      else corte = 2;
      actual += grupo.slice(0, corte).join("");
      sil.push(actual);
      actual = grupo.slice(corte).join("");
    }
    k = j;
  }
  if (actual) sil.push(actual);
  const res = [];
  for (const s of sil) {
    if (res.length && ![...s].some((c) => VOCALES.includes(c))) res[res.length - 1] += s;
    else res.push(s);
  }
  return res;
}

export function posicionAcento(palabra) {
  const w = palabra.toLowerCase();
  for (let i = 0; i < w.length; i++) if ("áéíóú".includes(w[i])) return i;
  const sil = silabear(w);
  if (!sil.length) return -1;
  const base = sinTildes(w);
  const llana = base ? "aeiouns".includes(base[base.length - 1]) : true;
  const k = llana && sil.length > 1 ? sil.length - 2 : sil.length - 1;
  let ini = 0;
  for (let i = 0; i < k; i++) ini += sil[i].length;
  const s = sil[k];
  const vocs = [];
  for (let j = 0; j < s.length; j++) {
    const c = s[j];
    const uMuda = c === "u" && j > 0 && "qg".includes(s[j - 1]) && j + 1 < s.length && "ei".includes(s[j + 1]);
    if ("aeiou".includes(c) && !uMuda) vocs.push(j);
  }
  if (!vocs.length) return -1;
  const fuertes = vocs.filter((j) => "aeo".includes(s[j]));
  return ini + (fuertes.length ? fuertes[0] : vocs[vocs.length - 1]);
}

/* Sonidos: a e i o u, p b t d k g f s m n l, Z (z/ce/ci), J (j/ge/gi), Y (y/ll), C (ch), N (ñ), r, R (rr) */
export function fonemas(palabra, acentuada = true) {
  const w = palabra.toLowerCase();
  const acento = acentuada ? posicionAcento(w) : -1;
  const res = [];
  let i = 0;
  while (i < w.length) {
    const c = w[i], sig = w[i + 1] || "", sig2 = w[i + 2] || "";
    if (w.startsWith("ch", i)) { res.push(["C", false]); i += 2; continue; }
    if (w.startsWith("ll", i)) { res.push(["Y", false]); i += 2; continue; }
    if (w.startsWith("rr", i)) { res.push(["R", false]); i += 2; continue; }
    if (c === "q") { res.push(["k", false]); i += sig === "u" ? 2 : 1; continue; }
    if (c === "g" && sig === "u" && sig2 && "eiéí".includes(sig2)) { res.push(["g", false]); i += 2; continue; }
    if (c === "g" && sig === "ü") { res.push(["g", false]); res.push(["u", false]); i += 2; continue; }
    if (VOCALES.includes(c)) { res.push([TILDE[c] || c, i === acento]); i += 1; continue; }
    if (c === "c") res.push([sig && "eiéí".includes(sig) ? "Z" : "k", false]);
    else if (c === "z") res.push(["Z", false]);
    else if (c === "g") res.push([sig && "eiéí".includes(sig) ? "J" : "g", false]);
    else if (c === "j") res.push(["J", false]);
    else if (c === "h") { /* muda */ }
    else if (c === "v") res.push(["b", false]);
    else if (c === "w") res.push(["u", false]);
    else if (c === "x") { if (i === 0) res.push(["s", false]); else { res.push(["k", false]); res.push(["s", false]); } }
    else if (c === "y") {
      if (i === w.length - 1 || !(sig && VOCALES.includes(sig))) res.push(["i", i === acento]);
      else res.push(["Y", false]);
    }
    else if (c === "ñ") res.push(["N", false]);
    else if (c === "r") res.push([i === 0 || "nls".includes(w[i - 1]) ? "R" : "r", false]);
    else if (c === "k") res.push(["k", false]);
    else if ("pbtdfsmnl".includes(c)) res.push([c, false]);
    i += 1;
  }
  return res;
}

export function claveFonetica(w) {
  let t = sinTildes(w.toLowerCase().replace(/gü/g, "gw"));
  const reglas = [[/ch/g, "C"], [/ll/g, "y"], [/rr/g, "R"], [/qu/g, "k"], [/gu(?=[ei])/g, "G"],
    [/g(?=[ei])/g, "j"], [/G/g, "g"], [/c(?=[ei])/g, "z"], [/c/g, "k"], [/h/g, ""], [/v/g, "b"],
    [/w/g, "u"], [/x/g, "ks"], [/y$/, "i"], [/^r/, "R"]];
  for (const [a, b] of reglas) t = t.replace(a, b);
  return t;
}

export function normalizarSilaba(s) {
  let t = sinTildes(s.toLowerCase()).replace(/ch/g, "C").replace(/h/g, "").replace(/C/g, "ch");
  t = t.replace(/^g(?=[ei])/, "j").replace(/gü/g, "gu").replace(/ü/g, "u").replace(/^z(?=[ei])/, "c");
  if (t.length > 1 && t.endsWith("y")) t = t.slice(0, -1) + "i";
  return t;
}

export function claveDifono(a, b) {
  const k = ([s, ac]) => s + (ac && VOC.includes(s) ? "1" : "");
  return `${k(a)}-${k(b)}`;
}

/* ------------------------------------------------------------------ mezcla */
// piezas: [[audio, junta]]; junta > 0 = muestras de silencio antes; < 0 = muestras de solape con fundido
export function mezclar(piezas) {
  let pos = 0;
  const inicios = [];
  piezas.forEach(([y, junta], k) => {
    let ini;
    if (k === 0) ini = 0;
    else if (junta >= 0) ini = pos + junta;
    else ini = pos - Math.min(-junta, piezas[k - 1][0].length, y.length);
    inicios.push(ini);
    pos = ini + y.length;
  });
  const out = new Float32Array(Math.max(pos, 0));
  piezas.forEach(([y, junta], k) => {
    const ini = inicios[k];
    let n = 0;
    if (k > 0 && junta < 0) n = Math.min(-junta, piezas[k - 1][0].length, y.length);
    for (let i = 0; i < n; i++) {
      const ang = (i + 0.5) / n * (Math.PI / 2);
      out[ini + i] = out[ini + i] * Math.cos(ang) + y[i] * Math.sin(ang);
    }
    for (let i = n; i < y.length; i++) out[ini + i] += y[i];
  });
  return out;
}

/* ------------------------------------------------------------------ lector */
export class Lector {
  static async crear(base = "./", opciones = {}) {
    if (base && !base.endsWith("/")) base += "/";
    const leer = (rel) => fetch(base + rel).then((r) => {
      if (!r.ok) throw new Error("No se encontró " + base + rel);
      return r.arrayBuffer();
    });
    return Lector.desdeArchivos(leer, opciones);
  }

  // leer(ruta) -> Promise<ArrayBuffer>. Sirve para leer desde un zip u otra fuente.
  static async desdeArchivos(leer, opciones = {}) {
    const m = JSON.parse(new TextDecoder().decode(await leer("manifest_lectura.json")));
    const ctx = opciones.ctx || new (window.AudioContext || window.webkitAudioContext)({ sampleRate: opciones.sampleRate || 24000 });
    const lector = new Lector(m, ctx);
    await lector.cargar(leer);
    return lector;
  }

  constructor(manifest, ctx = null) {
    this.m = manifest;
    this.p = manifest.parametros;
    this.ctx = ctx;
    this.sr = ctx ? ctx.sampleRate : manifest.sr;
    this.audios = {};
    this.desfase = {};
    this.porTilde = new Map();
    this.porClave = new Map();
    for (const [w, d] of Object.entries(manifest.palabras)) {
      if (!this.porTilde.has(sinTildes(w))) this.porTilde.set(sinTildes(w), w);
      if (!this.porClave.has(d.clave)) this.porClave.set(d.clave, w);
    }
    this.fuente = null;
  }

  // Carga y decodifica los 3 audios en paralelo. Corrige el pequeño desfase que agregan algunos formatos (MP3).
  async cargar(leer) {
    await Promise.all(Object.entries(this.m.audios).map(async ([nombre, ruta]) => {
      const buf = await this.ctx.decodeAudioData(await leer(ruta));
      const x = buf.getChannelData(0);
      const deltas = [];
      for (const marca of this.m.marcas[nombre] || []) {
        // el MP3 solo puede atrasar el audio (retardo del codificador), nunca adelantarlo
        const a = Math.max(0, muestras(marca - 0.02, this.sr)), b = Math.min(x.length, muestras(marca + 0.12, this.sr));
        for (let i = a; i < b; i++) if (Math.abs(x[i]) > 0.05) { deltas.push(i / this.sr - marca); break; }
      }
      deltas.sort((p, q) => p - q);
      this.desfase[nombre] = deltas.length ? deltas[Math.floor(deltas.length / 2)] : 0;
      this.audios[nombre] = x;
    }));
    return this;
  }

  _corte(archivo, [ini, dur]) {
    const a = muestras(ini + (this.desfase[archivo] || 0), this.sr);
    return this.audios[archivo].subarray(Math.max(0, a), Math.max(0, a) + muestras(dur, this.sr));
  }

  buscar(w) {
    w = w.toLowerCase();
    if (this.m.palabras[w]) return w;
    return this.porTilde.get(sinTildes(w)) || this.porClave.get(claveFonetica(w)) || null;
  }

  _buscarDifono(s1, a1, s2, a2) {
    const inv = this.m.difonos;
    for (const [x1, x2] of [[a1, a2], [!a1, a2], [a1, !a2], [!a1, !a2]]) {
      const k = claveDifono([s1, x1], [s2, x2]);
      if (inv[k]) return inv[k];
    }
    for (const [t1, t2] of [[SUSTITUTOS[s1] || s1, s2], [s1, SUSTITUTOS[s2] || s2]]) {
      for (const [x1, x2] of [[a1, a2], [!a1, a2], [a1, !a2]]) {
        const k = claveDifono([t1, x1], [t2, x2]);
        if (inv[k]) return inv[k];
      }
    }
    return null;
  }

  difonos(fon) {
    const seq = [["_", false], ...fon, ["_", false]];
    const piezas = [];
    for (let i = 0; i + 1 < seq.length; i++) {
      const d = this._buscarDifono(seq[i][0], seq[i][1], seq[i + 1][0], seq[i + 1][1]);
      if (!d) continue;
      const y = this._corte("difonos", d);
      piezas.push([y, piezas.length ? -muestras(this.p.fundido_difono_ms[clase(d[2])] / 1000, this.sr) : 0]);
    }
    return piezas.length ? mezclar(piezas) : new Float32Array(0);
  }

  palabra(w, final) {
    const pal = this.buscar(w);
    let fon, y;
    if (pal) {
      const d = this.m.palabras[pal];
      fon = fonemas(pal);
      y = this._corte("palabras", final && d.final ? d.final : d.medio);
    } else {
      fon = fonemas(w);
      y = this.difonos(fon);
    }
    if (!fon.length) return null;
    return [y, fon[0][0], fon[fon.length - 1][0]];
  }

  _junta(prevFin, sigIni) {
    if (CORTE_EN_CIERRE.includes(sigIni)) return muestras(this.p.hueco_oclusiva_ms / 1000, this.sr);
    if (VOC.includes(sigIni)) return -muestras((VOC.includes(prevFin) ? this.p.solape_vocales_ms : this.p.solape_vocal_ms) / 1000, this.sr);
    return -muestras(this.p.solape_ms / 1000, this.sr);
  }

  oracion(texto) {
    const tokens = texto.match(/\p{L}+|[.,;:!?¡¿]/gu) || [];
    const total = tokens.filter((t) => /\p{L}/u.test(t)).length;
    const piezas = [];
    let vistas = 0, ultimo = null, pausa = 0;
    for (const t of tokens) {
      if (!/\p{L}/u.test(t)) {
        if (piezas.length && ",;:".includes(t)) pausa = Math.max(pausa, muestras(this.p.pausa_coma_ms / 1000, this.sr));
        else if (piezas.length && ".!?".includes(t)) pausa = Math.max(pausa, muestras(this.p.pausa_punto_ms / 1000, this.sr));
        continue;
      }
      vistas += 1;
      const r = this.palabra(t, vistas === total);
      if (!r || !r[0].length) continue;
      const [y, ini, fin] = r;
      const junta = !piezas.length ? 0 : (pausa || this._junta(ultimo, ini));
      piezas.push([y, junta]);
      ultimo = fin; pausa = 0;
    }
    return piezas.length ? mezclar(piezas) : new Float32Array(0);
  }

  silaba(s) {
    const t = normalizarSilaba(s);
    if (this.m.silabas[t]) return this._corte("silabas", this.m.silabas[t]);
    return this.difonos(fonemas(s));   // sílaba que no está grabada: con dífonos
  }

  silabeo(texto) {
    const piezas = [];
    for (const w of texto.toLowerCase().match(/\p{L}+/gu) || []) {
      for (const s of silabear(w)) {
        const y = this.silaba(s);
        if (y.length) piezas.push([y, piezas.length ? muestras(this.p.pausa_entre_silabas_ms / 1000, this.sr) : 0]);
      }
    }
    return piezas.length ? mezclar(piezas) : new Float32Array(0);
  }

  secuencia(pasos) {
    const piezas = [];
    for (const [tipo, texto] of pasos) {
      const y = tipo === "silabas" ? this.silabeo(texto) : this.oracion(texto);
      if (y.length) piezas.push([y, piezas.length ? muestras(this.p.pausa_entre_pasos_ms / 1000, this.sr) : 0]);
    }
    return piezas.length ? mezclar(piezas) : new Float32Array(0);
  }

  // Cómo se va a leer cada palabra: [{palabra, como: "grabada"|"suena_igual"|"difonos", usa}]
  diagnostico(texto) {
    return (texto.match(/\p{L}+/gu) || []).map((w) => {
      const pal = this.buscar(w);
      if (pal && sinTildes(pal) === sinTildes(w.toLowerCase())) return { palabra: w, como: "grabada", usa: pal };
      if (pal) return { palabra: w, como: "suena_igual", usa: pal };
      return { palabra: w, como: "difonos", usa: silabear(w).join("-") };
    });
  }

  /* ---- reproducción ---- */
  detener() {
    if (this.fuente) { try { this.fuente.stop(); } catch (e) { /* ya terminó */ } this.fuente = null; }
  }

  async reproducir(m) {
    this.detener();
    if (!m.length) return;
    if (this.ctx.state === "suspended") await this.ctx.resume();
    const buf = this.ctx.createBuffer(1, m.length, this.sr);
    buf.copyToChannel(m, 0);
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.ctx.destination);
    this.fuente = src;
    return new Promise((ok) => { src.onended = ok; src.start(); });
  }

  leerOracion(texto) { return this.reproducir(this.oracion(texto)); }
  leerPalabra(texto) { return this.reproducir(this.oracion(texto)); }
  leerSilabas(texto) { return this.reproducir(this.silabeo(texto)); }
  leerSecuencia(pasos) { return this.reproducir(this.secuencia(pasos)); }
}

if (typeof window !== "undefined") window.Lector = Lector;
