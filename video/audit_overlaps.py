# -*- coding: utf-8 -*-
"""Аудит наложений: ловим пересечения ЛЮБЫХ текстовых слоёв по всем кадрам.
Патчим mask/colorize/paste, чтобы понять, какие слои содержат текст,
затем гоняем ту же покадровую логику, что и main(), и ищем пересечения bbox."""
import json, math, os, sys
import numpy as np
import render as R
import common as C
import build2 as B

PIN = []            # держим ссылки, чтобы id() не переиспользовались
MASK2TXT = {}       # id(PIL mask) -> текст
TXT_LAYERS = {}     # id(rgb ndarray) -> текст
INK_BBOX = {}       # id(a ndarray) -> (x0,y0,x1,y1) по альфе

o_mask, o_mask_lines, o_colorize = R.mask, R.mask_lines, R.colorize
o_paste = R.paste
o_grad = R.gradient_fill


def mask_w(text, size, weight=700, tracking=0.0, name='Montserrat'):
    m = o_mask(text, size, weight, tracking, name=name)
    MASK2TXT[id(m)] = str(text)
    PIN.append(m)
    return m


def mask_lines_w(lines, size, weight=700, tracking=0.0, pitch=None, align='left', width=None):
    m = o_mask_lines(lines, size, weight, tracking, pitch, align, width)
    MASK2TXT[id(m)] = ' | '.join(lines)
    PIN.append(m)
    return m


def colorize_w(m, color):
    rgb, a = o_colorize(m, color)
    if id(m) in MASK2TXT:
        TXT_LAYERS[id(rgb)] = MASK2TXT[id(m)]
        PIN.append(rgb)
    return rgb, a


def gradient_fill_w(m, stops):
    rgb, a = o_grad(m, stops)
    if id(m) in MASK2TXT:
        TXT_LAYERS[id(rgb)] = MASK2TXT[id(m)]
        PIN.append(rgb)
    return rgb, a


def paste_w(cr, ca, rgb, a, x, y):
    if id(rgb) in TXT_LAYERS:
        TXT_LAYERS[id(cr)] = TXT_LAYERS[id(rgb)]
        PIN.append(cr)
    elif id(rgb) in MASK2TXT:            # склейка маски напрямую
        TXT_LAYERS[id(cr)] = MASK2TXT[id(rgb)]
        PIN.append(cr)
    return o_paste(cr, ca, rgb, a, x, y)


for mod in (R, C, B):
    for nm, fn in (('mask', mask_w), ('mask_lines', mask_lines_w), ('colorize', colorize_w),
                   ('gradient_fill', gradient_fill_w), ('paste', paste_w)):
        if hasattr(mod, nm):
            setattr(mod, nm, fn)

DRAWLOG = []
CUR = {'sc': 0, 'fr': 0, 't': 0.0, 'o_blend': None}


def blend_w(frame, rgb, a, x, y, alpha=1.0, wipe=None, grow=None):
    txt = TXT_LAYERS.get(id(rgb))
    if txt is not None and alpha > 0.03:
        key = id(a)
        bb = INK_BBOX.get(key)
        if bb is None:
            aa = np.asarray(a)
            ys, xs = np.where(aa > 0.03)
            if len(xs) == 0:
                bb = (0, 0, 0, 0)
            else:
                bb = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
            INK_BBOX[key] = bb
            PIN.append(a)
        DRAWLOG.append((CUR['sc'], CUR['fr'], CUR['t'], txt, int(x) + bb[0], int(y) + bb[1],
                        int(x) + bb[2], int(y) + bb[3], float(alpha)))
    return CUR['o_blend'](frame, rgb, a, x, y, alpha=alpha, wipe=wipe, grow=grow)


CUR['o_blend'] = B.blend
B.blend = blend_w


def inter(a, b):
    x0 = max(a[4], b[4]); y0 = max(a[5], b[5]); x1 = min(a[6], b[6]); y1 = min(a[7], b[7])
    if x1 <= x0 or y1 <= y0:
        return 0, None
    return (x1 - x0) * (y1 - y0), (x0, y0, x1, y1)


def main():
    tim = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'timings2.json')))
    total = tim['total']
    scenes = B.SCENES
    dur = [tim['scenes'][str(i)]['dur'] for i in range(len(scenes))]
    scale = total / sum(dur)
    dur = [round(d * scale, 3) for d in dur]
    B.random.seed(11); np.random.seed(11)
    glow_cache = {}
    dummy = np.zeros((R.H, R.W, 3), np.float32)
    global DRAWLOG
    step = int(sys.argv[2]) if len(sys.argv) > 2 else 2
    for si, fn in enumerate(scenes):
        items = fn(si)
        nfr = int(round(dur[si] * R.FPS))
        for fi in range(0, nfr, step):
            t = fi / R.FPS
            CUR.update(sc=si + 1, fr=fi, t=t)
            for it in items:
                B.draw_item(dummy, it, t, glow_cache)
        print(f'сцена {si+1} просчитана', flush=True)

    print(f'\nвсего отрисовок текста: {len(DRAWLOG)}')
    # группируем по (сцена, кадр) и ищем пересечения
    from collections import defaultdict
    per = defaultdict(list)
    for ev in DRAWLOG:
        per[(ev[0], ev[1])].append(ev)
    pairs = defaultdict(lambda: {'n': 0, 'area': 0, 'rect': None, 't': [], 'a1': 0, 'a2': 0})
    for (sc, fr), evs in per.items():
        for i in range(len(evs)):
            for j in range(i + 1, len(evs)):
                A, Bv = evs[i], evs[j]
                if A[8] < 0.35 or Bv[8] < 0.35:
                    continue
                ar, rect = inter(A, Bv)
                if ar >= 1400:
                    key = (sc, A[3][:48], Bv[3][:48])
                    p = pairs[key]
                    p['n'] += 1
                    p['t'].append(A[2])
                    if ar > p['area']:
                        p['area'] = ar; p['rect'] = rect
                        p['a1'], p['a2'] = A[8], Bv[8]
    if not pairs:
        print('\nПЕРЕСЕЧЕНИЙ ТЕКСТА С ТЕКСТОМ НЕ НАЙДЕНО')
        return
    rows = sorted(pairs.items(), key=lambda kv: -kv[1]['area'])
    print(f'\nнайдено пар с пересечением: {len(rows)}')
    for (sc, s1, s2), p in rows[:40]:
        t0, t1 = min(p['t']), max(p['t'])
        print(f'сц{sc}  t={t0:.2f}..{t1:.2f}s  ({p["n"]} кадр.)  площадь {p["area"]}px  '
              f'[{s1}] X [{s2}]  rect={p["rect"]}  alpha {p["a1"]:.2f}/{p["a2"]:.2f}')
    json.dump([[k[0], k[1], k[2], v] for k, v in rows[:80]],
              open('overlap_report.json', 'w'), ensure_ascii=False, indent=1, default=str)


if __name__ == '__main__':
    main()
