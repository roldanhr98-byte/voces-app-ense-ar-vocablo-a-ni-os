"""Medidas acústicas simples para control de calidad de sílabas."""
import numpy as np

SR = 48000


def frames(x, win=0.030, hop=0.005):
    w, h = int(win * SR), int(hop * SR)
    n = max(1, (len(x) - w) // h + 1)
    idx = np.arange(w)[None, :] + h * np.arange(n)[:, None]
    return x[idx] * np.hanning(w)[None, :]


def perfil(x):
    """Por frame de 5 ms: energía dB, sonoridad (autocorrelación normalizada), tasa de cruces por cero."""
    F = frames(x)
    e = 10 * np.log10((F ** 2).mean(1) + 1e-12)
    zcr = (np.abs(np.diff(np.sign(F), axis=1)) > 0).mean(1)
    lo, hi = int(SR / 400), int(SR / 70)
    sp = np.fft.rfft(F, 2048, axis=1)
    ac = np.fft.irfft(np.abs(sp) ** 2, axis=1)[:, :hi + 1]
    w = np.hanning(F.shape[1])
    acw = np.correlate(w, w, "full")[len(w) - 1:len(w) + hi]
    acw = acw / acw[0]
    voz = (ac[:, lo:hi + 1] / (ac[:, :1] + 1e-12) / acw[None, lo:hi + 1]).max(1)
    return e, voz, zcr


def segmentos_sonoros(x, umbral_voz=0.45, rel_db=30):
    """Lista de (inicio_s, fin_s) de tramos sonoros con energía relevante."""
    e, voz, _ = perfil(x)
    activo = (voz > umbral_voz) & (e > e.max() - rel_db)
    segs, i = [], 0
    while i < len(activo):
        if activo[i]:
            j = i
            while j < len(activo) and activo[j]:
                j += 1
            segs.append([i, j])
            i = j
        else:
            i += 1
    # unir tramos separados por < 25 ms
    unidos = []
    for s in segs:
        if unidos and s[0] - unidos[-1][1] <= 5:
            unidos[-1][1] = s[1]
        else:
            unidos.append(s)
    return [(a * 0.005, b * 0.005) for a, b in unidos if b - a >= 4]


def ruido_inicial_ms(x, rel_db=45):
    """ms de sonido sordo (fricación/explosión) antes del primer tramo sonoro."""
    e, voz, zcr = perfil(x)
    act = np.where(e > e.max() - rel_db)[0]
    if not len(act):
        return 0.0
    ini = act[0]
    son = np.where((voz > 0.45) & (e > e.max() - 30))[0]
    if not len(son):
        return 0.0
    k = son[son >= ini]
    k = k[0] if len(k) else ini
    sordo = (voz[ini:k] < 0.45).sum()
    return float(sordo * 5)


def formantes(x, t0, t1):
    """F1, F2 medios (Hz) por LPC entre t0 y t1."""
    from numpy.linalg import solve
    y = x[int(t0 * SR):int(t1 * SR)]
    y = y[::4]  # 12 kHz
    sr = SR / 4
    res = []
    w = int(0.025 * sr)
    for k in range(0, max(1, len(y) - w), int(0.01 * sr)):
        s = y[k:k + w]
        if len(s) < w:
            break
        s = np.append(s[0], s[1:] - 0.97 * s[:-1]) * np.hamming(w)
        p = 14
        r = np.correlate(s, s, "full")[w - 1:w + p]
        if r[0] <= 0:
            continue
        R = np.array([[r[abs(i - j)] for j in range(p)] for i in range(p)]) + np.eye(p) * r[0] * 1e-6
        a = solve(R, r[1:p + 1])
        raices = np.roots(np.concatenate([[1], -a]))
        raices = raices[np.imag(raices) > 0]
        f = np.angle(raices) * sr / (2 * np.pi)
        bw = -np.log(np.abs(raices)) * sr / np.pi
        f = np.sort(f[(f > 200) & (bw < 400)])
        if len(f) >= 2:
            res.append(f[:2])
    if not res:
        return None
    return np.median(np.array(res), axis=0)


def jorobas_graves(x, caida_db=18, min_ms=40, union_ms=30):
    """Cuenta los núcleos vocálicos (jorobas de energía en 100-900 Hz).
    Una sílaba sola debe tener 1; 2 indica una vocal agregada (ej. "Af" -> "afe")."""
    F = frames(x, win=0.025, hop=0.005)
    sp = np.abs(np.fft.rfft(F, 2048, axis=1)) ** 2
    fr = np.fft.rfftfreq(2048, 1 / SR)
    e = 10 * np.log10(sp[:, (fr >= 100) & (fr <= 900)].sum(1) + 1e-12)
    arriba = e > e.max() - caida_db
    runs, i = [], 0
    while i < len(arriba):
        if arriba[i]:
            j = i
            while j < len(arriba) and arriba[j]:
                j += 1
            runs.append([i, j])
            i = j
        else:
            i += 1
    unidos = []
    for r in runs:
        if unidos and (r[0] - unidos[-1][1]) * 5 < union_ms:
            unidos[-1][1] = r[1]
        else:
            unidos.append(r)
    return len([r for r in unidos if (r[1] - r[0]) * 5 >= min_ms])



def sonoridad_inicial(x, ms=25):
    """Sonoridad media (0-1) de los primeros `ms` de voz. En palabras con p/t/k inicial
    debe ser baja (explosión sorda); alta indica una vocal agregada antes ("(e)pera")."""
    e, voz, _ = perfil(x)
    act = np.where(e > e.max() - 35)[0]
    if not len(act):
        return 0.0
    i = act[0]
    return float(np.mean(voz[i:i + max(1, ms // 5)]))


def ruido_previo_ms(x, debil=45, fuerte=20):
    """ms entre el primer sonido débil (-45 dB del máximo) y el arranque fuerte (-20 dB).
    Valores altos = respiración u otro ruido antes de la palabra."""
    e, _, _ = perfil(x)
    m = e.max()
    a = np.where(e > m - debil)[0]
    b = np.where(e > m - fuerte)[0]
    if not len(a) or not len(b):
        return 0.0
    return float((b[0] - a[0]) * 5)
