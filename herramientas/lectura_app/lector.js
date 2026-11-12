/*
 * Lector encadenado — arma y reproduce sílabas, palabras y oraciones con los audios de esta carpeta.
 *
 *   import { Lector } from "./lector.js";
 *   const lector = await Lector.crear("audios_lectura/");          // carpeta donde está manifest_lectura.json
 *   await lector.leerOracion("hoy me voy de vacaciones a la casa de mi tío");   // cualquier orden
 *   await lector.leerSilabas("vaca");                                // va - ca
 *   await lector.leerPalabra("vaca");                                // vaca
 *   await lector.leerSecuencia([["silabas", "vaca"], ["palabra", "vaca"],
 *                               ["silabas", "la vaca"], ["oracion", "la vaca come pasto"]]);
 *
 * - Las palabras del banco suenan con su versión "medio" y la última de la oración con su versión "final".
 * - Si una palabra no está grabada o viene mal escrita, se busca sin tildes y por sonido (b=v, h muda,
 *   ll=y...). Si igual no aparece, se arma con sílabas.
 * - En móviles el audio solo arranca después de un toque del usuario (regla del navegador).
 */

const VOCALES = "aeiouáéíóúü";
const FUERTES = "aeoáéíóú";
const INSEPARABLES = new Set(["pr", "br", "tr", "dr", "cr", "kr", "gr", "fr", "pl", "bl", "cl", "kl", "gl", "fl"]);

export function sinTildes(t) {
  return t.replace(/ñ/g, "\0").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/\0/g, "ñ");
}

export function claveFonetica(w) {
  let t = sinTildes(w.toLowerCase().replace(/gü/g, "gw"));
  const reglas = [[/ch/g, "C"], [/ll/g, "y"], [/rr/g, "R"], [/qu/g, "k"], [/gu(?=[ei])/g, "G"],
    [/g(?=[ei])/g, "j"], [/G/g, "g"], [/c(?=[ei])/g, "z"], [/c/g, "k"], [/h/g, ""], [/v/g, "b"],
    [/w/g, "u"], [/x/g, "ks"], [/y$/, "i"], [/^r/, "R"]];
  for (const [a, b] of reglas) t = t.replace(a, b);
  return t;
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

export function normalizarSilaba(s) {
  let t = sinTildes(s.toLowerCase()).replace(/ch/g, "C").replace(/h/g, "").replace(/C/g, "ch");
  t = t.replace(/^g(?=[ei])/, "j").replace(/gü/g, "gu").replace(/ü/g, "u").replace(/^z(?=[ei])/, "c");
  if (t.length > 1 && t.endsWith("y")) t = t.slice(0, -1) + "i";
  return t;
}

export class Lector {
  static async crear(base = "./", ctx = null) {
    if (base && !base.endsWith("/")) base += "/";
    const r = await fetch(base + "manifest_lectura.json");
    if (!r.ok) throw new Error("No se encontró manifest_lectura.json en " + base);
    return new Lector(base, await r.json(), ctx || new (window.AudioContext || window.webkitAudioContext)());
  }

  constructor(base, manifest, ctx) {
    this.base = base;
    this.m = manifest;
    this.ctx = ctx;
    this.sr = ctx.sampleRate;
    this.p = manifest.parametros;
    this.cache = new Map();
    this.porTilde = new Map();
    this.porClave = new Map();
    for (const [w, d] of Object.entries(manifest.palabras)) {
      if (!this.porTilde.has(sinTildes(w))) this.porTilde.set(sinTildes(w), w);
      if (!this.porClave.has(d.clave)) this.porClave.set(d.clave, w);
    }
    this.fuente = null;
  }

  buscar(w) {
    w = w.toLowerCase();
    if (this.m.palabras[w]) return w;
    const a = this.porTilde.get(sinTildes(w));
    if (a) return a;
    return this.porClave.get(claveFonetica(w)) || null;
  }

  async _audio(rel) {
    if (!this.cache.has(rel)) {
      this.cache.set(rel, fetch(this.base + rel)
        .then((r) => r.arrayBuffer())
        .then((b) => this.ctx.decodeAudioData(b))
        .then((ab) => ab.getChannelData(0)));
    }
    return this.cache.get(rel);
  }

  async _silaba(s) {
    const inv = this.m.silabas;
    const t = normalizarSilaba(s);
    const solape = this.p.solape_coda_ms / 1000;
    if (inv[t]) return [[await this._audio(inv[t]), 0]];
    const m = t.match(/^([^aeiou]*)([aeiou]+)([^aeiou]*)$/);
    if (!m) return [];
    const [, ataque, nucleo, coda] = m;
    const piezas = [];
    if (inv[ataque + nucleo]) piezas.push([await this._audio(inv[ataque + nucleo]), 0]);
    else {
      if (inv[ataque + nucleo[0]]) piezas.push([await this._audio(inv[ataque + nucleo[0]]), 0]);
      const resto = nucleo.slice(1);
      if (resto) {
        const clave = inv[resto] ? resto : resto.slice(-1);
        if (inv[clave]) piezas.push([await this._audio(inv[clave]), solape]);
      }
    }
    if (coda) {
      const vc = nucleo.slice(-1) + coda[0];
      if (inv[vc]) piezas.push([await this._audio(inv[vc]), solape]);
    }
    return piezas;
  }

  async _palabra(w, final) {
    const pal = this.buscar(w);
    if (pal) {
      const d = this.m.palabras[pal];
      return [[await this._audio(final && d.final ? d.final : d.medio), 0]];
    }
    let piezas = [];
    for (const s of silabear(w)) piezas = piezas.concat(await this._silaba(s));
    return piezas;
  }

  _unir(piezas, pausa) {
    const f = Math.round(this.p.fundido_ms / 1000 * this.sr);
    let out = new Float32Array(0);
    let ultimo = 0;
    piezas.forEach(([y, solape], k) => {
      if (k === 0) { out = Float32Array.from(y); ultimo = y.length; return; }
      if (solape > 0) {
        // fusión: la vocal compartida suena una sola vez ("pa" + "an" -> "pan")
        const fr = this.p.fusion_recorte;
        out = out.subarray(0, out.length - Math.floor(fr * ultimo));
        y = y.subarray(Math.floor(fr * y.length));
        const n = Math.min(Math.round(solape * this.sr), out.length, y.length);
        const nuevo = new Float32Array(out.length + y.length - n);
        nuevo.set(out);
        const o = out.length - n;
        for (let i = 0; i < n; i++) nuevo[o + i] = out[o + i] * (1 - i / n) + y[i] * (i / n);
        nuevo.set(y.subarray(n), out.length);
        out = nuevo;
      } else {
        const z = Math.round(pausa * this.sr);
        const nuevo = new Float32Array(out.length + z + y.length);
        nuevo.set(out);
        nuevo.set(y, out.length + z);
        out = nuevo;
      }
      ultimo = y.length;
    });
    for (let i = 0; i < Math.min(f, out.length); i++) out[out.length - 1 - i] *= i / f;
    return out;
  }

  async oracion(texto) {
    const tokens = texto.match(/[\p{L}]+|[.,;:!?¡¿]/gu) || [];
    const total = tokens.filter((t) => /\p{L}/u.test(t)).length;
    const piezas = [];
    let vistas = 0;
    for (const t of tokens) {
      if (!/\p{L}/u.test(t)) {
        if (piezas.length && ",;:".includes(t)) piezas.push([new Float32Array(Math.round(this.p.pausa_coma_ms / 1000 * this.sr)), 0]);
        else if (piezas.length && ".!?".includes(t)) piezas.push([new Float32Array(Math.round(this.p.pausa_punto_ms / 1000 * this.sr)), 0]);
        continue;
      }
      vistas += 1;
      const pw = await this._palabra(t, vistas === total);
      if (pw.length) piezas.push([pw.length > 1 ? this._unir(pw, 0) : pw[0][0], 0]);
    }
    return this._unir(piezas, this.p.pausa_entre_palabras_ms / 1000);
  }

  async silabeo(texto) {
    const piezas = [];
    for (const w of texto.toLowerCase().match(/[\p{L}]+/gu) || []) {
      for (const s of silabear(w)) {
        const ps = await this._silaba(s);
        if (ps.length) piezas.push([this._unir(ps, 0), 0]);
      }
    }
    return this._unir(piezas, this.p.pausa_entre_silabas_ms / 1000);
  }

  async secuencia(pasos) {
    const audios = [];
    for (const [tipo, texto] of pasos) audios.push([tipo === "silabas" ? await this.silabeo(texto) : await this.oracion(texto), 0]);
    return this._unir(audios, this.p.pausa_entre_pasos_ms / 1000);
  }

  detener() {
    if (this.fuente) { try { this.fuente.stop(); } catch (e) { /* ya terminó */ } this.fuente = null; }
  }

  async reproducir(muestras) {
    this.detener();
    if (this.ctx.state === "suspended") await this.ctx.resume();
    const buf = this.ctx.createBuffer(1, Math.max(1, muestras.length), this.sr);
    buf.copyToChannel(muestras, 0);
    const src = this.ctx.createBufferSource();
    src.buffer = buf;
    src.connect(this.ctx.destination);
    this.fuente = src;
    return new Promise((ok) => { src.onended = ok; src.start(); });
  }

  async leerOracion(texto) { return this.reproducir(await this.oracion(texto)); }
  async leerPalabra(texto) { return this.reproducir(await this.oracion(texto)); }
  async leerSilabas(texto) { return this.reproducir(await this.silabeo(texto)); }
  async leerSecuencia(pasos) { return this.reproducir(await this.secuencia(pasos)); }
}

if (typeof window !== "undefined") window.Lector = Lector;
