# -*- coding: utf-8 -*-
"""Аудио-помощники (видео №2): загрузка, размещение, дакинг, фильтры."""
import wave
import numpy as np

SR = 48000


def load(f):
    with wave.open(f) as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), '<i2').astype(np.float32) / 32768.0
        if w.getsampwidth() != 2:
            raise RuntimeError(w.getsampwidth())
    if ch == 2:
        x = x.reshape(-1, 2).mean(1)
    if sr != SR:
        idx = np.arange(int(len(x) * SR / sr)) * (sr / SR)
        x = np.interp(idx, np.arange(len(x)), x).astype(np.float32)
    return x



def place(buf, sig, t, gain=1.0):
    i = max(0, int(round(t * SR)))
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[:j - i] * gain



def envelope(x, atk=0.025, rel=0.30, hop=0.005, norm=0.055):
    h = int(hop * SR)
    m = len(x) // h
    r = np.sqrt((x[:m * h].reshape(m, h) ** 2).mean(1) + 1e-12)
    e = np.zeros(m, np.float32)
    prev = 0.0
    for i in range(m):
        v = r[i]
        c = 1 - np.exp(-hop / (atk if v > prev else rel))
        prev += (v - prev) * c
        e[i] = prev
    e = np.clip(e / norm, 0, 1) ** 1.2
    rep = np.repeat(e, h)
    if len(rep) < len(x):
        rep = np.pad(rep, (0, len(x) - len(rep)), mode='edge')
    return rep[:len(x)]



def fft_hp(x, f0):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    H = (f / f0) ** 2 / (1.0 + (f / f0) ** 2)
    return np.fft.irfft(X * H, len(x)).astype(np.float32)



def rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)

