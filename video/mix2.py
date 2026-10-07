# -*- coding: utf-8 -*-
"""Звуковой микс для видео №2 (гайд по конфигу): музыка + SFX + озвучка с дакингом."""
import json, os, subprocess, wave, sys
import numpy as np
import imageio_ffmpeg
from audio_utils import load, place, envelope, fft_hp, rms_db, SR

HERE = os.path.dirname(os.path.abspath(__file__))
AUD = os.path.normpath(os.path.join(HERE, '..', 'assets', 'audio'))
PROC = os.path.join(AUD, 'proc2')
FF = imageio_ffmpeg.get_ffmpeg_exe()
VIDEO_IN = os.path.join(HERE, 'master2_mute.mp4')
VIDEO_OUT = os.path.join(HERE, '..', 'wardogs_otkluchenie_teney_konfig_1080x1920.mp4')
MIX_WAV = os.path.join(HERE, 'mix2.wav')


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode == 'hookA':
        global VIDEO_IN, VIDEO_OUT
        VIDEO_IN = os.path.join(HERE, '..', 'wardogs_otkluchenie_teney_konfig_hookA_mute.mp4')
        VIDEO_OUT = os.path.join(HERE, '..', 'wardogs_otkluchenie_teney_konfig_hookA.mp4')
    tl = json.load(open(os.path.join(HERE, 'timeline2.json')))
    total = tl['total']
    scenes = tl['scenes']
    tim = json.load(open(os.path.join(HERE, 'timings2.json')))
    n = int((total + 0.05) * SR)

    music = load(os.path.join(HERE, '..', 'assets', 'music', 'fonk_main2.wav'))
    vo = np.zeros(n, np.float32)
    for i, sc in enumerate(scenes):
        p = os.path.join(PROC, f'v2_{i+1}.wav')
        if os.path.exists(p):
            place(vo, load(p), sc['start'] + tim['scenes'][str(i)]['vo_start'], 1.0)

    sfx = {}
    def S(name):
        if name not in sfx:
            sfx[name] = load(os.path.join(AUD, name))
        return sfx[name]

    hits = []
    hits.append(('whoosh.wav', 0.06, 0.28))                      # мягкий старт (без удара)
    for k, sc in enumerate(scenes[1:], start=1):
        f = 'whoosh.wav' if k % 2 else 'whoosh_down.wav'
        hits.append((f, max(0.0, sc['start'] - 0.25), 0.42))     # переход между шагами

    for si, sc in enumerate(scenes):
        for it in sc['items']:
            kd, t0, du = it['kind'], it['t0'], it.get('dur', 0.3)
            if kd == 'fade_slide' and abs(du - 0.24) < 1e-6:
                hits.append(('tick.wav', t0, 0.11))              # строки списка
            if kd == 'pop':
                hits.append(('shimmer.wav', t0, 0.34))           # всплывающие окна/плашки
            if kd == 'boxdraw':
                hits.append(('whoosh_down.wav', t0 - 0.18, 0.36))
            if kd == 'crossfade':
                hits.append(('whoosh_down.wav', t0, 0.22))
            if it.get('sfx'):
                hits.append((it['sfx'], t0, it.get('sfxg') or 0.24))
            if kd == 'type':
                nsp = max(6, int(du / 0.05))                     # «клавиши» при печати
                for k in range(nsp):
                    hits.append(('tick.wav', t0 + du * (k / nsp), 0.055))
    if len(scenes) > 4:
        t5 = scenes[4]['start']
        hits.append(('riser.wav', t5 - 1.42, 0.46))              # райзер перед «РЕЗУЛЬТАТ»
    for it in scenes[-1]['items']:
        if it['kind'] == 'wipe' and 1.2 < it['t0'] - scenes[-1]['start'] < 1.5:
            hits.append(('shimmer.wav', it['t0'], 0.30))

    sfx_buf = np.zeros(n, np.float32)
    for name, t, g in hits:
        place(sfx_buf, S(name), t, g)
    print(f'SFX: {len(hits)}')

    duck = envelope(vo)
    bed = np.zeros(n, np.float32)
    k = min(n, len(music))
    bed[:k] = music[:k]
    bed = fft_hp(bed, 32)
    fo = int(1.2 * SR)
    bed[-fo:] *= np.linspace(1, 0, fo) ** 1.3
    music_g = 0.30 * (1 - 0.45 * duck)

    mix = vo * 1.0 + bed * music_g + sfx_buf
    mix = np.tanh(mix * 1.06) * 0.94
    mix *= 0.97 / max(1e-9, np.abs(mix).max())
    fo2 = int(0.35 * SR)
    mix[-fo2:] *= np.linspace(1, 0, fo2) ** 1.2
    print(f'  музыка rms {rms_db(bed):.1f} | голос {rms_db(vo):.1f} | sfx {rms_db(sfx_buf):.1f} | итог {rms_db(mix):.1f} дБ')

    with wave.open(MIX_WAV, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(mix, -1, 1) * 32767).astype('<i2').tobytes())

    r = subprocess.run([FF, '-i', MIX_WAV, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    print(' ', [l.strip() for l in r.splitlines() if l.strip().startswith('I:')][-1])

    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', VIDEO_IN, '-i', MIX_WAV,
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                    '-movflags', '+faststart', '-shortest', VIDEO_OUT], check=True)
    print('готово:', VIDEO_OUT)


if __name__ == '__main__':
    main()
