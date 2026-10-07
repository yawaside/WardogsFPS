# -*- coding: utf-8 -*-
"""
Сборка видео №3: рендер кадров 1080x1920@30 -> master3_mute.mp4 + timeline3.json.
Улучшения: zoomfade/wordpop кинетика, Ken Burns на игровых панелях, анимированный
прицел, кроссфейды между сценами, сегментированный прогресс-бар, частицы, grain.
"""
import json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image
import render3 as R
from render3 import (W, H, FPS, CW, MARGIN_L, MARGIN_R, TOP, BOTTOM, PROGRESS_Y,
                     GOLD, GREEN, RED, solid, paste, cl, eo, eb, eio, blend, add_glow,
                     scale_layer, glow_sprite)
import game3
import scenes3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
REFS = os.path.join(ROOT, 'assets', 'refs')
OUT_MUTE = os.path.join(HERE, 'master3_mute.mp4')

XFD = 0.28                      # длительность кроссфейда между сценами


# ---------------------------------------------------------------- premade assets
def make_bgphoto():
    """Размытая тёмная подложка (bg_city) для сцен с окнами."""
    im = Image.open(os.path.join(REFS, 'bg_city.jpg')).convert('RGB')
    # cover-crop под 1080x1920
    sc = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
    l = (im.width - W) // 2
    t = (im.height - H) // 2
    im = im.crop((l, t, l + W, t + H)).filter(__import__('PIL.ImageFilter', fromlist=['GaussianBlur']).GaussianBlur(18))
    a = np.asarray(im, np.float32)
    a *= 0.42
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rv = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    a *= np.clip(1.06 - 0.34 * rv ** 2, 0.45, 1.0)[..., None]
    return np.clip(a, 0, 255)


# ---------------------------------------------------------------- draw item
def crossfade_layer(frame, rgb1, a1, rgb2, a2, x, y, wgt):
    if wgt <= 0.001:
        blend(frame, rgb1, a1, x, y); return
    if wgt >= 0.999:
        blend(frame, rgb2, a2, x, y); return
    A = a1 * (1 - wgt) + a2 * wgt
    num = rgb1 * (a1 * (1 - wgt))[..., None] + rgb2 * (a2 * wgt)[..., None]
    rgb = num / np.maximum(A, 1e-6)[..., None]
    blend(frame, rgb, A, x, y)


def draw_item(frame, it, t, ctx):
    kd = it['kind']
    t0, du = it.get('t0', 0.0), it.get('dur', 0.3)
    p = cl((t - t0) / du)
    x, y = it.get('x', 0), it.get('y', 0)
    G = ctx['game']

    if kd == 'fade_slide':
        e = eo(p)
        x += it.get('dx', 0) * (1 - e); y += it.get('dy', 0) * (1 - e)
        al = p
        if it.get('fade_out'):
            fo_t, fo_d = it['fade_out']
            al = min(al, 1 - cl((t - fo_t) / fo_d))
        blend(frame, it['rgb'], it['a'], int(x), int(y), alpha=max(0.0, al))

    elif kd == 'pop':
        e = eb(p, 1.45)
        y += it.get('dy', 0) * (1 - e)
        blend(frame, it['rgb'], it['a'], int(x), int(y), alpha=min(1.0, p * 1.2))

    elif kd == 'zoomfade':
        e = eb(p, 1.35)
        s = it.get('z0', 0.55) + (1 - it.get('z0', 0.55)) * e
        dx = it.get('dx', 0) * (1 - eo(p)); dy = it.get('dy', 0) * (1 - eo(p))
        rgb, a = scale_layer(it['rgb'], it['a'], s)
        h, w = it['a'].shape
        cx = x + dx + (w - rgb.shape[1]) // 2
        cy = y + dy + (h - rgb.shape[0]) // 2
        al = p
        if it.get('fade_out'):
            fo_t, fo_d = it['fade_out']
            al = min(al, 1 - cl((t - fo_t) / fo_d))
        blend(frame, rgb, a, int(cx), int(cy), alpha=max(0.0, al))

    elif kd == 'wipe':
        blend(frame, it['rgb'], it['a'], int(x), int(y), wipe=(eo(p), it.get('soft', 90)))

    elif kd == 'grow':
        blend(frame, it['rgb'], it['a'], int(x), int(y), grow=eo(p))

    elif kd == 'divider':
        blend(frame, it['rgb'], it['a'], int(x), int(y), alpha=p)

    elif kd == 'boxdraw':
        blend(frame, it['rgb'], it['a'], int(x), int(y), wipe=(eo(p), 300), alpha=min(1.0, p * 1.4))

    elif kd == 'type':
        if p <= 0:
            return
        blend(frame, it['rgb'], it['a'], int(x), int(y), wipe=(p, it.get('soft', 10)))

    elif kd == 'cursor':
        if t < t0:
            return
        nch = it.get('nchars', 1)
        nsh = int(cl((t - t0) / du) * nch)
        px = it['base_x'] + it['cell'] * nsh
        if t < t0 + du:
            al = 1.0
        else:
            al = 0.9 if math.sin(t * 12) > -0.2 else 0.12
        blend(frame, it['rgb'], it['a'], int(px), int(it['base_y']), alpha=al)

    elif kd == 'blink':
        if t < t0:
            return
        al = (math.sin((t - t0) / it.get('period', 0.4) * math.pi * 2) * 0.5 + 0.5) * 0.9 * \
             max(0.0, 1 - (t - t0) / (du * 1.6))
        if al > 0.02:
            blend(frame, it['rgb'], it['a'], int(x), int(y), alpha=al)

    elif kd == 'highlight':
        if t < t0:
            return
        k = eo(cl((t - t0) / du))
        crossfade_layer(frame, it['rgb'], it['a'], it['rgb2'], it['a2'], int(x), int(y), k)

    elif kd == 'game':
        kb = it.get('kb')
        if kb:
            pk = cl((t - kb.get('t0', t0)) / kb['dur'])
            e = eio(pk)
            s = kb['s0'] + (kb['s1'] - kb['s0']) * e
            fx = kb['fx0'] + (kb['fx1'] - kb['fx0']) * e
            fy = kb['fy0'] + (kb['fy1'] - kb['fy0']) * e
        else:
            s, fx, fy = G['kmax'], 0.5, 0.5
        view = game3.kb_view(G[it['which']], s, fx, fy)
        a_view = G['mask'] * p
        if it.get('wipe_in'):
            soft = 60
            ramp = np.clip((eo(p) * (G['pw'] + soft) - np.arange(G['pw'])) / soft, 0, 1).astype(np.float32)
            a_view = a_view * ramp[None, :]
        blend(frame, view, a_view, int(x), int(y))
        # рамка панели
        fr_rgb, fr_a = ctx['panel_frame']
        blend(frame, fr_rgb, fr_a, int(x), int(y), alpha=p)

    elif kd == 'crosshair':
        if p <= 0:
            return
        mv0, mvd = it.get('mv_t0', 99), it.get('mv_dur', 0.1)
        mp = cl((t - mv0) / mvd)
        me = eio(mp)
        dx = it.get('dx0', 0) + (it.get('dx1', 0) - it.get('dx0', 0)) * me
        dy = it.get('dy0', 0) + (it.get('dy1', 0) - it.get('dy0', 0)) * me
        rgb, a = G[it.get('layer', 'cross_bright')]
        al = min(1.0, p * 1.5)
        if it.get('pulse') and t > t0:
            al *= 0.8 + 0.2 * math.sin((t - t0) * 10)
        blend(frame, rgb, a, int(x + dx), int(y + dy), alpha=al)

    elif kd == 'compdivider':
        if p <= 0 or p >= 1:
            return
        k = eo(p)
        px = int(x + it['w'] * k)
        bar_rgb, bar_a = solid(4, it['h'] - 40, (250, 200, 90), 235)
        edge = min(p * 4, 1.0, (1 - p) * 4)
        blend(frame, bar_rgb, bar_a, px - 2, int(y) + 20, alpha=edge)
        key = ('divider_dot',)
        if key not in ctx['glow_cache']:
            ctx['glow_cache'][key] = glow_sprite(64, (255, 214, 120), 2.2)
        dot = ctx['glow_cache'][key]
        add_glow(frame, dot[0], dot[1], px - 32, int(y) + it['h'] // 2 - 32, 0.5 * edge)

    elif kd == 'knob':
        ts, te = it.get('tstart', t0), it.get('tend', t0 + du)
        e = eio(cl((t - ts) / max(1e-6, te - ts)))
        px = int(it['x0'] + (it['x1'] - it['x0']) * e)
        blend(frame, it['rgb'], it['a'], px, int(y), alpha=1 - e)
        if it.get('rgb2') is not None:
            blend(frame, it['rgb2'], it['a2'], px, int(y), alpha=e)

    elif kd == 'pulse':
        if t < t0:
            return
        col, r, k = it.get('glow', ((255, 255, 255), 90, 0.12))
        key = (r, tuple(col))
        if key not in ctx['glow_cache']:
            ctx['glow_cache'][key] = glow_sprite(r, col, 2.3)
        spr = ctx['glow_cache'][key]
        h, w = it['a'].shape
        kk = k * (0.6 + 0.4 * math.sin((t - t0) * 6))
        add_glow(frame, spr[0], spr[1], int(x + w / 2 - r), int(y + h / 2 - r), kk)

    elif kd == 'bgphoto':
        blend(frame, ctx['bgphoto'], np.full((H, W), it.get('alpha', 0.2), np.float32), 0, 0,
              alpha=p)

    # свечение на элементе
    if it.get('glow') and p > 0 and kd not in ('pulse',):
        col, r, k = it['glow']
        key = (r, tuple(col))
        if key not in ctx['glow_cache']:
            ctx['glow_cache'][key] = glow_sprite(r, col, 2.3)
        spr_rgb, spr_a = ctx['glow_cache'][key]
        h, w = it['a'].shape
        add_glow(frame, spr_rgb, spr_a, int(x + w * 0.5 - r), int(y + h * 0.5 - r),
                 k * min(1.0, p * 1.5))


# ---------------------------------------------------------------- глобальные эффекты
def apply_global_fx(frame, items, t, fi):
    for it in items:
        kd = it['kind']
        t0, du = it.get('t0', 0.0), it.get('dur', 0.3)
        p = cl((t - t0) / du)
        if kd == 'flash' and p > 0:
            al = it.get('peak', 0.5) * (p * 2 if p < 0.5 else (1 - p) * 2)
            col = np.array(it.get('color', (255, 255, 255)), np.float32)
            reg = it.get('region')
            if reg:
                x, y, w, h = reg
                frame[y:y + h, x:x + w] += col[None, None, :] * (al * 0.85)
            else:
                frame += col[None, None, :] * al
        elif kd == 'shake' and 0 < p < 1:
            amp = it.get('amp', 3.0) * (1 - p)
            off = int(round(amp * math.sin((t - t0) * 48)))
            if off:
                frame[:] = np.roll(np.roll(frame, off, axis=0), off // 2, axis=1)
        elif kd == 'fadeout' and p > 0:
            frame *= (1 - 0.45 * eo(p))


# ---------------------------------------------------------------- прогресс-бар
def draw_progress(frame, gp, seg_ends, t):
    x = MARGIN_L
    n = len(seg_ends)
    for i in range(n):
        x0 = MARGIN_L + int(CW * seg_ends[i][0])
        x1 = MARGIN_L + int(CW * seg_ends[i][1])
        wseg = max(2, x1 - x0 - 6)
        done = gp > seg_ends[i][1] - 1e-6
        cur = (not done) and gp >= seg_ends[i][0] - 1e-6
        if done:
            col, al = GOLD, 0.95
        elif cur:
            al = 0.65 + 0.3 * (0.5 + 0.5 * math.sin(t * 5))
            col, al = GOLD, al
        else:
            col, al = (44, 46, 50), 0.9
        trgb, ta = solid(wseg, 5, col, 255)
        blend(frame, trgb, ta, x0, PROGRESS_Y, alpha=al)
    # glow-dot на границе
    gx = MARGIN_L + int(CW * gp)
    dot = glow_sprite(24, GOLD, 2.2)
    add_glow(frame, dot[0], dot[1], gx - 24, PROGRESS_Y - 22, 0.22)


# ---------------------------------------------------------------- main
def main():
    preview = 'preview' in sys.argv
    random.seed(11); np.random.seed(11)
    base = R.radial_bg()
    fr_rgb, fr_a = R.corner_frame()
    ft_rgb, ft_a = R.footer_layer(text='WARDOGS · ГАЙД ПО КОНФИГУ')
    zero_a = np.zeros((H, W), np.float32)
    paste(base, zero_a, fr_rgb, fr_a, 0, 0)
    paste(base, zero_a, ft_rgb, ft_a, (W - ft_rgb.shape[1]) // 2, 1608)
    bgphoto = make_bgphoto()
    G = game3.build_all()
    # рамка панели
    pfr = Image.new('RGBA', (G['pw'], G['ph']), (0, 0, 0, 0))
    from PIL import ImageDraw
    ImageDraw.Draw(pfr).rounded_rectangle([1, 1, G['pw'] - 2, G['ph'] - 2], radius=14,
                                          outline=(84, 88, 98, 255), width=2)
    fa = np.asarray(pfr, np.float32)
    panel_frame = (fa[..., :3].copy(), fa[..., 3].copy() / 255.0)

    ctx = {'game': G, 'glow_cache': {}, 'bgphoto': bgphoto, 'panel_frame': panel_frame}

    scenes = scenes3.SCENE_FNS
    durs = scenes3.SCENE_DURS
    total = scenes3.TOTAL
    seg_ends = []
    acc = 0.0
    for d in durs:
        seg_ends.append((acc / total, (acc + d) / total))
        acc += d

    scene_items = [fn(G) for fn in scenes]

    # превью-режим: mid/end кадры + проверка переполнения
    if preview:
        os.makedirs(os.path.join(HERE, 'preview3'), exist_ok=True)
        noise = R.film_grain_tile(0, 1.7)
        noise = (np.random.default_rng(7).random((H + 160, W + 160), dtype=np.float32) - 0.5) * 2.0 * 1.7
        gt = 0.0
        for si, items in enumerate(scene_items):
            for tag, tt in (('end', durs[si] - 0.12), ('mid', durs[si] * 0.55)):
                frame = base.copy()
                for it in items:
                    draw_item(frame, it, tt, ctx)
                apply_global_fx(frame, items, tt, 0)
                gp = (gt + tt) / total
                draw_progress(frame, gp, seg_ends, gt + tt)
                oy, ox = (int(gt * 7) * 37) % 160, (int(gt * 5) * 53) % 160
                frame += noise[oy:oy + H, ox:ox + W][..., None] * 1.7
                np.clip(frame, 0, 255, out=frame)
                Image.fromarray(frame.astype(np.uint8)).save(
                    os.path.join(HERE, 'preview3', f'scene{si+1}_{tag}.png'))
            def _bot(it):
                a = it.get('a')
                if a is None:
                    return 0
                return it.get('y', 0) + a.shape[0]
            bot = max((_bot(it) for it in items), default=0)
            over = [it['kind'] for it in items if _bot(it) > BOTTOM + 6]
            print(f'  preview сцена {si+1} ({durs[si]:.2f}s) нижняя граница {bot}px' +
                  (f'  ПЕРЕПОЛНЕНИЕ: {over}' if over else ''))
            gt += durs[si]
        return

    # таймлайн для звукового микса
    tl = {'fps': FPS, 'total': round(total, 3), 'scenes': []}
    acc = 0.0
    for si, items in enumerate(scene_items):
        def _bot(it):
            a = it.get('a')
            if a is None:
                return 0
            return it.get('y', 0) + a.shape[0]
        bot = max((_bot(it) for it in items), default=0)
        flag = 'ок' if bot <= BOTTOM + 6 else f'ПЕРЕПОЛНЕНИЕ +{bot - BOTTOM:.0f}px'
        print(f'  сцена {si+1}: нижняя граница {bot}px ({flag})')
        tl['scenes'].append({'start': round(acc, 3), 'dur': durs[si],
                             'items': [{'kind': it['kind'], 't0': round(acc + it.get('t0', 0), 3),
                                        'dur': it.get('dur', 0.3), 'sfx': it.get('sfx'),
                                        'sfxg': it.get('sfxg')} for it in items]})
        acc += durs[si]
    json.dump(tl, open(os.path.join(HERE, 'timeline3.json'), 'w'), ensure_ascii=False, indent=1)
    print('таймлайн: timeline3.json')

    # частицы пыли/искр
    parts = []
    for _ in range(16):
        parts.append(dict(x=random.uniform(60, W - 60), y0=random.uniform(1560, 1900),
                          sp=random.uniform(22, 52), ph=random.uniform(0, 6.3),
                          r=random.choice([70, 110, 150]), k=random.uniform(0.035, 0.07),
                          col=random.choice([GOLD, (255, 150, 40), (255, 210, 120)]),
                          amp=random.uniform(14, 42)))
    sprites = {(p['r'], tuple(p['col'])): glow_sprite(p['r'], p['col'], 2.6) for p in parts}
    noise = (np.random.default_rng(7).random((H + 160, W + 160), dtype=np.float32) - 0.5) * 2.0 * 1.7

    import imageio_ffmpeg
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium',
           '-crf', '17', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.2', '-g', '60',
           '-movflags', '+faststart', OUT_MUTE]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    xf_frames = int(XFD * FPS)
    gt = 0.0
    print(f'сцен: {len(scenes)}, длительность: {total:.2f}s')
    prev_last = None
    for si, items in enumerate(scene_items):
        # последний кадр предыдущей сцены (для кроссфейда)
        if prev_last is None:
            prev_last = np.zeros((H, W, 3), np.float32)   # старт с чёрного
        nfr = int(round(durs[si] * FPS))
        for fi in range(nfr):
            t = fi / FPS
            frame = base.copy()
            # flash-in первой сцены
            if si == 0:
                fl = max(0.0, 1 - t / 0.14) ** 2
                if fl > 0.001:
                    frame += fl * 60.0 * np.array([1.0, 0.9, 0.75], np.float32)
            # частицы
            for p in parts:
                sp_rgb, sp_a = sprites[(p['r'], tuple(p['col']))]
                life = (gt * p['sp'] + p['ph'] * 40) % 900
                py = p['y0'] - life
                px = p['x'] + p['amp'] * math.sin(gt * 0.7 + p['ph'])
                env = math.sin(math.pi * min(1.0, max(0.0, life / 900.0)))
                add_glow(frame, sp_rgb, sp_a, int(px), int(py), p['k'] * env * 0.9)
            for it in items:
                draw_item(frame, it, t, ctx)
            apply_global_fx(frame, items, t, fi)
            gp = (gt + t) / total
            draw_progress(frame, gp, seg_ends, gt + t)
            # дыхание фона
            frame += math.sin((gt + t) * 0.5) * 0.6
            # кроссфейд с предыдущей сценой
            if si > 0 and fi < xf_frames:
                wgt = 1 - eo(fi / xf_frames)
                frame *= wgt
                frame += prev_last * (1 - wgt)
            # grain
            oy, ox = (fi * 37) % 160, (fi * 53) % 160
            frame += noise[oy:oy + H, ox:ox + W][..., None] * 1.7
            np.clip(frame, 0, 255, out=frame)
            proc.stdin.write(frame.astype(np.uint8).tobytes())
        prev_last = frame.copy()
        gt += durs[si]
        print(f'  сцена {si+1}/{len(scenes)} готова ({gt:.1f}s)')
    proc.stdin.close(); proc.wait()
    print('готово:', OUT_MUTE)


if __name__ == '__main__':
    main()
