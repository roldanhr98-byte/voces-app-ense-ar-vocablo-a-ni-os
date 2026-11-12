"""Tono (F0), marcas de período y TD-PSOLA para suavizar empalmes.

  f0(x, sr, fmin, fmax)        -> F0 por frame de 5 ms (0 = sin voz)
  marcas(x, sr, f0s)           -> posiciones (muestras) de cada período glótico en los tramos con voz
  psola(x, sr, marcas, factor) -> x con el tono multiplicado por factor[i] (por muestra), misma duración
"""
import numpy as np

HOP = 0.005


def f0(x, sr, fmin=60, fmax=400, umbral=0.15):
    """F0 con YIN (de Cheveigné y Kawahara), por frame de 5 ms. Más robusto que la autocorrelación simple
    frente a errores de octava en voces graves o rasposas."""
    x = np.asarray(x, dtype=np.float64)
    n_orig = len(x)
    sr2 = sr
    if sr % 16000 == 0 and sr > 16000 and len(x) > 64:      # el tono no necesita 48 kHz
        q = sr // 16000
        X = np.fft.rfft(x)
        X[np.fft.rfftfreq(len(x), 1 / sr) > 7000] = 0
        x = np.fft.irfft(X, len(x))[::q]
        sr2 = sr // q
    W = int(0.04 * sr2)
    h = int(HOP * sr2)
    tmin, tmax = max(2, int(sr2 / fmax)), min(W - 1, int(sr2 / fmin) + 1)
    n = max(1, (n_orig // (sr // sr2) - W) // h + 1)
    if len(x) < W + 2:
        return np.zeros(n)
    idx = np.minimum(np.arange(W)[None, :] + h * np.arange(n)[:, None], len(x) - 1)
    F = x[idx]
    en = (F ** 2).mean(1)
    ac = np.fft.irfft(np.abs(np.fft.rfft(F, 2 * W, axis=1)) ** 2, axis=1)[:, :tmax + 1]
    cs = np.cumsum(F ** 2, axis=1)
    taus = np.arange(tmax + 1)
    e1 = np.where(taus[None, :] < W, cs[:, np.clip(W - 1 - taus, 0, W - 1)], 0)
    e2 = cs[:, -1:] - np.where(taus[None, :] > 0, cs[:, np.clip(taus - 1, 0, W - 1)], 0)
    d = np.maximum(e1 + e2 - 2 * ac, 0)
    d[:, 0] = 0
    cm = np.cumsum(d[:, 1:], axis=1)
    dp = np.ones_like(d)
    dp[:, 1:] = d[:, 1:] * taus[None, 1:] / np.maximum(cm, 1e-12)
    res = np.zeros(n)
    piso = en.max() * 10 ** (-40 / 10)
    for i in range(n):
        if en[i] < piso:
            continue
        fila = dp[i, tmin:tmax + 1]
        bajo = np.where(fila < umbral)[0]
        if len(bajo):
            k = bajo[0]
            while k + 1 < len(fila) and fila[k + 1] < fila[k]:
                k += 1
        else:
            k = int(np.argmin(fila))
            if fila[k] > 0.35:
                continue
        tau = tmin + k
        if 0 < k < len(fila) - 1:   # interpolación parabólica
            a, b, c = fila[k - 1], fila[k], fila[k + 1]
            den = a - 2 * b + c
            if den > 0:
                tau = tau + 0.5 * (a - c) / den
        res[i] = sr2 / tau
    out = res.copy()
    for i in range(n):
        if res[i] > 0:
            vec = res[max(0, i - 2):i + 3]
            out[i] = np.median(vec[vec > 0])
    return out


def marcas(x, sr, f0s):
    """Marcas de período (picos del período) en los tramos con voz."""
    from numpy.fft import rfft, irfft
    # señal suavizada (< 900 Hz) para ubicar los picos
    n = len(x)
    X = rfft(x)
    fr = np.fft.rfftfreq(n, 1 / sr)
    X[fr > 900] = 0
    xl = irfft(X, n)
    res = []
    t = 0
    h = int(HOP * sr)
    while t < n:
        i = min(len(f0s) - 1, t // h)
        if f0s[i] <= 0:
            t += h
            continue
        T = int(sr / f0s[i])
        a, b = t, min(n, t + T)
        if b - a < 4:
            break
        p = a + int(np.argmax(xl[a:b]))
        res.append(p)
        # siguiente: alrededor de p + T
        while True:
            i = min(len(f0s) - 1, p // h)
            if f0s[i] <= 0:
                t = p + T
                break
            T = int(sr / f0s[i])
            a, b = p + int(0.8 * T), min(n, p + int(1.2 * T))
            if b - a < 2:
                t = n
                break
            q = a + int(np.argmax(xl[a:b]))
            res.append(q)
            p = q
    return np.array(sorted(set(res)), dtype=int)


def psola(x, sr, mk, factor):
    """TD-PSOLA: cambia el tono por factor (array por muestra), conserva la duración.
    Fuera de los tramos con marcas (consonantes sordas, silencio) copia la señal tal cual."""
    if len(mk) < 3:
        return x.copy()
    out = np.zeros(len(x) + sr // 10)
    peso = np.zeros_like(out)
    # períodos de análisis
    periodos = np.diff(mk)
    # tramos con voz: marcas consecutivas a menos de 1/50 s
    tramos, ini = [], 0
    for k in range(1, len(mk)):
        if mk[k] - mk[k - 1] > sr // 50:
            tramos.append((ini, k - 1))
            ini = k
    tramos.append((ini, len(mk) - 1))
    voz = np.zeros(len(x), dtype=bool)
    for a, b in tramos:
        if b - a < 2:
            continue
        ta = mk[a]
        tb = mk[b]
        voz[ta:tb] = True
        # marcas de síntesis
        t = float(ta)
        while t < tb:
            # marca de análisis más cercana
            k = a + int(np.argmin(np.abs(mk[a:b + 1] - t)))
            T0 = periodos[min(k, len(periodos) - 1)] if k < len(mk) - 1 else periodos[k - 1]
            c = mk[k]
            L = int(T0)
            g0, g1 = max(0, c - L), min(len(x), c + L)
            grano = x[g0:g1] * np.hanning(g1 - g0)
            s = int(round(t)) - (c - g0)
            if s >= 0 and s + len(grano) <= len(out):
                out[s:s + len(grano)] += grano
                peso[s:s + len(grano)] += np.hanning(g1 - g0)
            f = factor[min(len(factor) - 1, int(t))]
            t += T0 / max(0.5, min(2.0, f))
    # normalizar donde hay voz y copiar el resto
    y = x.copy()
    m = voz & (peso[:len(x)] > 0.1)
    y[m] = out[:len(x)][m] / np.maximum(peso[:len(x)][m], 0.5)
    # bordes de cada tramo: fundido de 5 ms entre original y procesado
    f = int(0.005 * sr)
    for a, b in tramos:
        if b - a < 2:
            continue
        for borde, sentido in ((mk[a], 1), (mk[b], -1)):
            for j in range(f):
                p = borde + sentido * j
                if 0 <= p < len(x) and m[p]:
                    al = j / f
                    y[p] = al * y[p] + (1 - al) * x[p]
    return y


# ----------------------------------------------------------------------------- ajustes para empalmar
def a_st(hz):
    return 12 * np.log2(np.maximum(hz, 1e-6) / 100.0)


def de_st(st):
    return 100.0 * 2 ** (st / 12)


def _tono_por_muestra(x, sr, rango):
    f = f0(x, sr, *rango)
    centros = (np.arange(len(f)) * HOP + 0.02) * sr
    v = f > 0
    return f, centros, v


def ajustar_tono(x, sr, rango, puntos=None, bordes=None, max_st=8.0):
    """Cambia el tono con TD-PSOLA (misma duración).
    puntos: [(muestra, semitonos_objetivo)] -> sigue ese contorno (semitonos respecto de 100 Hz).
    bordes: (st_inicio, st_fin) -> solo corrige el principio y el final con una rampa (None = no tocar ese borde);
            la melodía de adentro se conserva."""
    f, centros, v = _tono_por_muestra(x, sr, rango)
    if v.sum() < 3:
        return x.copy()
    t = np.arange(len(x))
    st_act = np.interp(t, centros[v], a_st(f[v]))
    if puntos:
        pos = [p for p, _ in puntos]
        obj = np.interp(t, pos, [s for _, s in puntos])
        corr = obj - st_act
    else:
        st_v = a_st(f[v])
        c_ini = (bordes[0] - np.median(st_v[:3])) if bordes[0] is not None else 0.0
        c_fin = (bordes[1] - np.median(st_v[-3:])) if bordes[1] is not None else 0.0
        corr = np.interp(t, [centros[v][0], centros[v][-1]], [c_ini, c_fin])
    corr = np.clip(corr, -max_st, max_st)
    return psola(x, sr, marcas(x, sr, f), 2 ** (corr / 12))


def nivel_db(x, sr, centro, ancho=0.010):
    a, b = max(0, int(centro - ancho * sr)), min(len(x), int(centro + ancho * sr))
    if b - a < 8:
        return None
    return 20 * np.log10(np.sqrt(np.mean(x[a:b] ** 2)) + 1e-9)


def rampa_ganancia(x, puntos_db, max_db=10.0):
    """Ganancia en dB que pasa por [(muestra, dB)] (lineal entre puntos, constante en los extremos)."""
    if not puntos_db:
        return x.copy()
    pos = [p for p, _ in puntos_db]
    g = np.clip(np.interp(np.arange(len(x)), pos, [d for _, d in puntos_db]), -max_db, max_db)
    return x * 10 ** (g / 20)


def tono_en(x, sr, rango, muestras):
    """Tono (semitonos respecto de 100 Hz) en esas muestras, interpolando entre los frames con voz."""
    f, centros, v = _tono_por_muestra(x, sr, rango)
    if v.sum() < 3:
        return None, None
    st = a_st(f[v])
    return np.interp(muestras, centros[v], st), float(np.median(st))
