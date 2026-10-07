# -*- coding: utf-8 -*-
"""Синтез SFX для видео №3 (48kHz mono). Все звуки процедурные."""
import os
import numpy as np
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.normpath(os.path.join(HERE, '..', '..', 'assets', 'audio'))
SR = 48000


def save(name, x, gain=1.0):
    x = np.clip(x * gain, -1, 1)
    with wave.open(os.path.join(AUD, name), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())
    print(f'  {name}: {len(x)/SR:.2f}s')


def env(n, a, d):
    t = np.arange(n) / SR
    e = np.minimum(t / max(1e-6, a), 1.0) * np.exp(-t / max(1e-6, d))
    return (e / max(1e-9, e.max())).astype(np.float32)


def sine(dur, f0, f1=None, decay=0.25):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f0 if f1 is None else f0 + (f1 - f0) * (t / dur)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) * env(n, 0.004, decay)).astype(np.float32)


def noise(dur):
    return np.random.default_rng(42).standard_normal(int(dur * SR)).astype(np.float32)


def bandpass_win(x_win, f0, bw=0.7):
    X = np.fft.rfft(x_win)
    f = np.fft.rfftfreq(len(x_win), 1 / SR)
    H = np.exp(-((np.log(np.maximum(f, 1) / f0)) ** 2) / (2 * bw ** 2))
    return np.fft.irfft(X * H, len(x_win)).astype(np.float32)


def whoosh(dur, f_hi, f_lo, name):
    """Noise whoosh: bandpass центр падает от f_hi до f_lo по окнам."""
    n = int(dur * SR)
    x = noise(dur)
    win = int(0.02 * SR)
    out = np.zeros(n, np.float32)
    pos = 0
    i = 0
    while pos + win <= n:
        p = pos / n
        fc = f_hi * (f_lo / f_hi) ** (p ** 0.8)
        seg = bandpass_win(x[pos:pos + win], fc)
        e = env(win, 0.006, dur * 0.5)
        out[pos:pos + win] = seg * e
        pos += win
        i += 1
    e = env(n, 0.03, dur * 0.55)
    save(name, out * e, 0.9)


def main():
    os.makedirs(AUD, exist_ok=True)
    whoosh(0.30, 2200, 180, 'whoosh.wav')
    whoosh(0.38, 1500, 70, 'whoosh_down.wav')
    save('tick.wav', sine(0.05, 1900, decay=0.018), 0.55)
    # shimmer: два тона + лёгкий шумовой «искрящийся» хвост
    a1 = sine(0.35, 2600, decay=0.16)
    a2 = sine(0.30, 3900, decay=0.12)
    sh = np.zeros(max(len(a1), len(a2)), np.float32)
    sh[:len(a1)] += a1
    sh[:len(a2)] += 0.6 * a2
    nz = noise(0.25) * env(int(0.25 * SR), 0.002, 0.09) * 0.05
    sh[:len(nz)] += nz
    save('shimmer.wav', sh, 0.8)
    # pop: короткий «пух» с понижением тона
    save('pop.wav', sine(0.09, 520, 170, decay=0.035), 0.85)
    # success: арпеджо вверх
    su = np.zeros(int(0.5 * SR), np.float32)
    for i, f in enumerate((880, 1318, 1758)):
        seg = sine(0.22, f, decay=0.14)
        st = int(i * 0.09 * SR)
        su[st:st + len(seg)] += seg
    save('success.wav', su, 0.75)
    # lock: короткий восходящий «дзинь» (фиксация прицела)
    save('lock.wav', sine(0.16, 2200, 2637, decay=0.07), 0.8)
    # riser: нарастающий шум перед «результатом»
    ri = noise(0.55)
    ri = np.convolve(ri, np.ones(64) / 64, mode='same').astype(np.float32)
    n = len(ri)
    cresc = (np.arange(n) / n) ** 2.2
    save('riser.wav', ri * cresc * env(n, 0.02, 0.28), 0.8)
    # punch: низкий удар на старте
    pu = sine(0.28, 62, 40, decay=0.12)
    nb = noise(0.06) * env(int(0.06 * SR), 0.001, 0.03) * 0.4
    pu[:len(nb)] += nb
    save('punch.wav', pu, 0.9)


if __name__ == '__main__':
    main()
