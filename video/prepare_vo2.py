# -*- coding: utf-8 -*-
"""Озвучка и тайминги для видео №2 (гайд по конфигу / тени)."""
import os, wave, json, subprocess
import numpy as np
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.normpath(os.path.join(HERE, '..', 'assets', 'audio'))
PROC = os.path.join(AUD, 'proc2')
os.makedirs(PROC, exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe()

ATEMPO = 1.06
# пауза перед голосом: элементы/текст успевают появиться первыми
VO_START = [1.28, 1.55, 1.55, 1.65, 1.40, 1.28]
TAILS =    [0.35, 0.35, 0.35, 0.35, 0.35, 1.30]


def load(f):
    with wave.open(f) as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), '<i2').astype(np.float32) / 32768.0
    return (x.reshape(-1, 2).mean(1) if ch == 2 else x), sr


def save(f, x, sr):
    with wave.open(f, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype('<i2').tobytes())


def tighten(x, sr, min_sil=0.17, keep=0.13, thr_db=-40.0):
    hop = int(0.005 * sr)
    m = len(x) // hop
    if not m:
        return x
    fr = x[:m * hop].reshape(m, hop)
    db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
    sil = db < thr_db
    keep_h = max(1, int(keep / 0.005))
    mask = np.ones(m, bool)
    i = 0
    while i < m:
        if sil[i]:
            j = i
            while j < m and sil[j]:
                j += 1
            if (j - i) * 0.005 > min_sil:
                mask[i + keep_h:j] = False
            i = j
        else:
            i += 1
    return fr[mask].reshape(-1)


def main():
    durs = []
    for i in range(1, 7):
        x, sr = load(os.path.join(AUD, f'v2_{i}.wav'))
        x = tighten(x, sr)
        tmp = os.path.join(PROC, f'_v2_{i}.wav')
        save(tmp, x, sr)
        out = os.path.join(PROC, f'v2_{i}.wav')
        subprocess.run([FF, '-y', '-loglevel', 'error', '-i', tmp, '-af',
                        f'atempo={ATEMPO},aresample=48000,'
                        'acompressor=threshold=-19dB:ratio=3:attack=6:release=140,'
                        'loudnorm=I=-16:TP=-1.5:LRA=9',
                        '-ac', '1', '-c:a', 'pcm_s16le', out], check=True)
        os.remove(tmp)
        y, sr2 = load(out)
        d = len(y) / sr2
        durs.append(d)
        print(f'  v2_{i}: {d:5.2f}s')

    scenes, total = {}, 0.0
    for i, d in enumerate(durs):
        dur = round(VO_START[i] + d + TAILS[i], 3)
        scenes[str(i)] = {'dur': dur, 'vo_start': VO_START[i], 'vo_len': round(d, 3)}
        total += dur
    with open(os.path.join(HERE, 'timings2.json'), 'w') as f:
        json.dump({'total': round(total, 3), 'scenes': scenes, 'atempo': ATEMPO}, f,
                  ensure_ascii=False, indent=1)
    acc = 0.0
    for k, v in scenes.items():
        print(f"  сцена {int(k)+1}: старт {acc:5.2f}s длина {v['dur']:5.2f}s | голос +{v['vo_start']}s ({v['vo_len']}s)")
        acc += v['dur']
    print(f'ИТОГО: {total:.2f}s')


if __name__ == '__main__':
    main()
