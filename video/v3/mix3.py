# -*- coding: utf-8 -*-
"""Финальный микс видео №3: оригинальная озвучка + музыка (с дакингом) + SFX."""
import json, os, subprocess, sys, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
AUD = os.path.join(ROOT, 'assets', 'audio')
MUS = os.path.join(ROOT, 'assets', 'music')
FF = None

sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..')))
from audio_utils import load, place, envelope, fft_hp, rms_db, SR  # noqa: E402

VIDEO_IN = os.path.join(HERE, 'master3_mute.mp4')
VIDEO_OUT = os.path.join(ROOT, 'wardogs_otkluchenie_teney_konfig_v3_1080x1920.mp4')
MIX_WAV = os.path.join(HERE, 'mix3.wav')

GAINS = {'pop.wav': 0.30, 'shimmer.wav': 0.26, 'whoosh.wav': 0.24,
         'whoosh_down.wav': 0.24, 'tick.wav': 0.10, 'success.wav': 0.30,
         'lock.wav': 0.28, 'punch.wav': 0.30, 'riser.wav': 0.40}


SFX_FILES = ['whoosh.wav', 'whoosh_down.wav', 'tick.wav', 'shimmer.wav', 'pop.wav',
             'success.wav', 'lock.wav', 'riser.wav', 'punch.wav']


def ensure_assets(ff):
    """Автогенерация производных ассетов (SFX, конвертация mp3->wav)."""
    if not all(os.path.exists(os.path.join(AUD, f)) for f in SFX_FILES):
        print('генерирую SFX...')
        import sfx3
        sfx3.main()
    vo_wav = os.path.join(AUD, 'vo3_full.wav')
    if not os.path.exists(vo_wav):
        subprocess.run([ff, '-y', '-loglevel', 'error', '-i', os.path.join(ROOT, 'wardogs2_audio.mp3'),
                        '-ar', '48000', '-ac', '1', vo_wav], check=True)
        print('конвертирована озвучка ->', vo_wav)
    mus_wav = os.path.join(MUS, 'fonk_main3.wav')
    if not os.path.exists(mus_wav):
        subprocess.run([ff, '-y', '-loglevel', 'error', '-i', os.path.join(ROOT, 'wardogs_music.mp3'),
                        '-ar', '48000', '-ac', '1', mus_wav], check=True)
        print('конвертирована музыка ->', mus_wav)


def main():
    import imageio_ffmpeg
    global FF
    FF = imageio_ffmpeg.get_ffmpeg_exe()
    ensure_assets(FF)

    tl = json.load(open(os.path.join(HERE, 'timeline3.json')))
    total = tl['total']
    scenes = tl['scenes']
    n = int((total + 0.05) * SR)

    vo = load(os.path.join(AUD, 'vo3_full.wav'))
    vbuf = np.zeros(n, np.float32)
    k = min(n, len(vo))
    vbuf[:k] = vo[:k]

    music = load(os.path.join(MUS, 'fonk_main3.wav'))
    bed = np.zeros(n, np.float32)
    k = min(n, len(music))
    bed[:k] = music[:k]
    bed = fft_hp(bed, 32)
    fo = int(1.2 * SR)
    bed[-fo:] *= np.linspace(1, 0, fo) ** 1.3

    sfx = {}
    def S(name):
        if name not in sfx:
            sfx[name] = load(os.path.join(AUD, name))
        return sfx[name]

    hits = []
    hits.append(('punch.wav', 0.02, 0.30))
    hits.append(('whoosh.wav', 0.06, 0.30))
    for k, sc in enumerate(scenes[1:], start=1):
        f = 'whoosh.wav' if k % 2 else 'whoosh_down.wav'
        hits.append((f, max(0.0, sc['start'] - 0.25), 0.42))
    # type -> серия tick
    for sc in scenes:
        for it in sc['items']:
            kd, t0, du = it['kind'], it['t0'], it.get('dur', 0.3)
            if kd == 'type':
                nsp = max(6, int(du / 0.05))
                for j in range(nsp):
                    hits.append(('tick.wav', t0 + du * (j / nsp), 0.05))
            if it.get('sfx'):
                hits.append((it['sfx'], t0, it.get('sfxg') or GAINS.get(it['sfx'], 0.24)))
    # riser перед «результатом» (сцена 5, индекс 4)
    if len(scenes) > 4:
        t5 = scenes[4]['start']
        hits.append(('riser.wav', t5 - 1.42, 0.46))

    sfx_buf = np.zeros(n, np.float32)
    for name, t, g in hits:
        place(sfx_buf, S(name), t, g)
    print(f'SFX: {len(hits)} событий, {len(sfx)} файлов')

    duck = envelope(vbuf)
    music_g = 0.30 * (1 - 0.45 * duck)

    mix = vbuf * 1.0 + bed * music_g + sfx_buf
    mix = np.tanh(mix * 1.06) * 0.94
    mix *= 0.97 / max(1e-9, np.abs(mix).max())
    fo2 = int(0.35 * SR)
    mix[-fo2:] *= np.linspace(1, 0, fo2) ** 1.2
    print(f'  музыка {rms_db(bed):.1f} | голос {rms_db(vbuf):.1f} | sfx {rms_db(sfx_buf):.1f} | итог {rms_db(mix):.1f} дБ')

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
