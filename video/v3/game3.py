# -*- coding: utf-8 -*-
"""
Игровые кадры для видео №3: пара «С ТЕНЯМИ / БЕЗ ТЕНЕЙ» на AI-фоне.
Premade-сцена собирается один раз (с запасом под Ken Burns), в кадре — только
bilinear-вьюпорт. Солдат рисуется procédurally (SS=3), туман — фрактальный шум,
прицел — векторный (dim/bright/gold варианты, позиция анимируется в сцене).
"""
import os
import numpy as np
from PIL import Image, ImageDraw
import render3 as R

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.normpath(os.path.join(HERE, '..', '..', 'assets', 'refs'))

PW, PH = 842, 474          # панель на экране
KMAX = 1.14                # макс. приближение Ken Burns
PW2, PH2 = int(PW * KMAX), int(PH * KMAX)   # 959 x 540

GOLD_RIM = (255, 200, 90)
CX, GROUND = 700, 505      # позиция солдата в premade-координатах


# ---------------------------------------------------------------- helpers
def value_noise(w, h, cell, octaves, seed):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        c = max(2, cell // (2 ** o))
        gw, gh = w // c + 3, h // c + 3
        g = rng.random((gh, gw), dtype=np.float32)
        im = Image.fromarray((g * 255).astype(np.uint8), 'L').resize((w, h), Image.BILINEAR)
        out += amp * np.asarray(im, np.float32) / 255.0
        tot += amp
        amp *= 0.55
    return out / tot


def shift_x(a, dx):
    out = np.zeros_like(a)
    if dx > 0:
        out[:, dx:] = a[:, :-dx]
    elif dx < 0:
        out[:, :dx] = a[:, -dx:]
    else:
        out[:] = a
    return out


def shift_y(a, dy):
    out = np.zeros_like(a)
    if dy > 0:
        out[dy:, :] = a[:-dy, :]
    elif dy < 0:
        out[:dy, :] = a[-dy:, :]
    else:
        out[:] = a
    return out


# ---------------------------------------------------------------- soldier
def soldier_mask(ss=3):
    """Маска силуэта солдата (SS-холст -> premade). Коренастые пропорции à la WARDOGS."""
    W2, H2 = PW2 * ss, PH2 * ss
    im = Image.new('L', (W2, H2), 0)
    d = ImageDraw.Draw(im)
    S = ss
    cx, gr = CX, GROUND          # premade-координаты; P() домножает на SS

    def P(x):
        return x * S
    def ell(x0, y0, x1, y1):
        d.ellipse([P(x0), P(y0), P(x1), P(y1)], fill=255)
    def rr(x0, y0, x1, y1, r):
        d.rounded_rectangle([P(x0), P(y0), P(x1), P(y1)], radius=P(r), fill=255)
    def line(x0, y0, x1, y1, w):
        d.line([P(x0), P(y0), P(x1), P(y1)], fill=255, width=P(w), joint='curve')
    def poly(pts):
        d.polygon([(P(x), P(y)) for x, y in pts], fill=255)

    # --- голова: шлем + козырёк (смотрит влево) + лицо
    ell(cx - 17, 295, cx + 17, 331)
    poly([(cx - 15, 305), (cx - 29, 312), (cx - 15, 320)])
    ell(cx - 11, 321, cx + 11, 345)
    # --- шея
    rr(cx - 8, 340, cx + 8, 358, 3)
    # --- бронежилет (широкий верх, сужение к поясу)
    poly([(cx - 46, 358), (cx + 46, 358), (cx + 51, 392), (cx + 45, 428),
          (cx - 45, 428), (cx - 51, 392)])
    # передняя плита разгрузки + подсумки
    rr(cx - 22, 372, cx + 22, 424, 6)
    for (px0, py0) in [(-19, 392), (-3, 392), (-19, 408), (-3, 408)]:
        rr(cx + px0, py0, cx + px0 + 14, py0 + 12, 2)
    # --- оружие: автомат наизготовку, ствол влево-вверх
    line(cx - 10, 412, cx - 62, 398, 8)          # ствол
    line(cx - 62, 398, cx - 73, 395, 6)          # пламегаситель
    rr(cx - 14, 406, cx + 30, 424, 4)            # ствольная коробка
    poly([(cx - 6, 424), (cx + 8, 424), (cx + 2, 448), (cx - 6, 466),
          (cx - 14, 460), (cx - 5, 442), (cx - 11, 428)])   # изогнутый магазин
    rr(cx + 12, 424, cx + 21, 441, 3)            # рукоять
    rr(cx + 28, 408, cx + 55, 422, 4)            # приклад (в правое плечо)
    # --- руки
    line(cx - 42, 368, cx - 57, 406, 15)         # левая: плечо->локоть
    line(cx - 57, 406, cx - 41, 413, 12)         # локоть->кисть (на цевье)
    ell(cx - 49, 407, cx - 33, 421)              # левая кисть
    line(cx + 42, 368, cx + 55, 404, 15)         # правая: плечо->локоть
    line(cx + 55, 404, cx + 25, 433, 12)         # локоть->кисть (на рукояти)
    ell(cx + 18, 427, cx + 34, 441)              # правая кисть
    # --- таз (брюки)
    poly([(cx - 26, 424), (cx + 26, 424), (cx + 23, 458), (cx - 23, 458)])
    # --- ноги
    line(cx - 15, 452, cx - 19, 474, 22)         # левое бедро
    line(cx - 19, 474, cx - 15, 500, 17)         # левая голень
    ell(cx - 27, 465, cx - 11, 481)              # левый наколенник
    line(cx + 15, 452, cx + 21, 472, 22)         # правое бедро
    line(cx + 21, 472, cx + 19, 498, 17)         # правая голень
    ell(cx + 13, 463, cx + 29, 479)              # правый наколенник
    # --- ботинки (носки влево)
    rr(cx - 42, 497, cx + 2, 508, 4)
    rr(cx + 0, 495, cx + 42, 506, 4)

    im = im.resize((PW2, PH2), Image.LANCZOS)
    m = np.asarray(im, np.float32) / 255.0
    m = R.box_blur(m, 1)
    return np.clip(m, 0, 1)


def soldier_layer(with_shadows):
    """Слой солдата: тёмный силуэт или контрастная модель с золотым rim light."""
    a = soldier_mask(ss=3)
    h, w = a.shape
    ys = np.linspace(0, 1, h)[:, None].astype(np.float32)
    if with_shadows:
        top, bot = (26, 23, 20), (12, 10, 9)
        rgb = np.zeros((h, w, 3), np.float32)
        for ch in range(3):
            rgb[..., ch] = top[ch] + (bot[ch] - top[ch]) * ys
        return rgb, a
    # без теней: контрастная заливка
    top, bot = (64, 61, 56), (38, 36, 33)
    rgb = np.zeros((h, w, 3), np.float32)
    for ch in range(3):
        rgb[..., ch] = top[ch] + (bot[ch] - top[ch]) * ys
    # rim light: левый край (солнце слева) + слабый верхний
    edge_left = np.clip(a - shift_x(a, 5), 0, 1)
    edge_top = np.clip(a - shift_y(a, 4), 0, 1)
    rim_a = np.clip(edge_left * 1.0 + edge_top * 0.45, 0, 1) * 0.95
    rim_a = R.box_blur(rim_a, 1)
    rim_rgb = np.zeros((h, w, 3), np.float32)
    rim_rgb[..., 0], rim_rgb[..., 1], rim_rgb[..., 2] = GOLD_RIM
    R.paste(rgb, a, rim_rgb, rim_a, 0, 0)
    # тёплое свечение вокруг модели (контраст выделяет её на фоне)
    glow_rgb, glow_a = R.glow_sprite(150, (255, 190, 80), 2.6)
    R.paste(rgb, a, glow_rgb, glow_a * 0.10, CX - 150, int(GROUND - 200) - 150)
    return rgb, a


def ground_shadow_layer():
    """Длинная тень от фигуры вправо-вниз (солнце слева). Только «с тенями»."""
    rgb = np.zeros((PH2, PW2, 3), np.float32)
    rgb[..., 0], rgb[..., 1], rgb[..., 2] = (8, 7, 6)
    im = Image.new('L', (PW2 * 2, PH2 * 2), 0)
    d = ImageDraw.Draw(im)
    pts = [(CX - 34, GROUND - 2), (CX + 46, GROUND - 2), (CX + 260, GROUND + 72),
           (CX + 170, GROUND + 82), (CX - 6, GROUND + 16)]
    d.polygon([(x * 2, y * 2) for x, y in pts], fill=255)
    im = im.resize((PW2, PH2), Image.LANCZOS)
    a = np.asarray(im, np.float32) / 255.0
    a = R.box_blur(a, 7) * 0.62
    return rgb, a


def fog_layer(strength, seed=3):
    n = value_noise(PW2, PH2, cell=90, octaves=4, seed=seed)
    n2 = value_noise(PW2, PH2, cell=30, octaves=3, seed=seed + 50)
    n = np.clip(n * 0.65 + n2 * 0.35, 0, 1) ** 1.2
    yy = np.linspace(0, 1, PH2)[:, None].astype(np.float32)
    vert = np.clip(yy * 1.9, 0, 1) ** 1.4
    horiz = np.exp(-((yy - 0.52) / 0.16) ** 2) * 0.55
    band = np.clip(vert + horiz, 0, 1)
    a = np.clip(n * band * strength, 0, 1)
    a = R.box_blur(a, 5)
    rgb = np.zeros((PH2, PW2, 3), np.float32)
    rgb[..., 0], rgb[..., 1], rgb[..., 2] = (132, 122, 110)
    return rgb, a


def grade(rgb, with_shadows):
    out = rgb.copy()
    if with_shadows:
        out *= 0.80
        g = out.mean(-1, keepdims=True)
        out = g + (out - g) * 0.82
        out = (out - 128) * 0.97 + 128
    else:
        out = (out - 128) * 1.12 + 130
        g = out.mean(-1, keepdims=True)
        out = g + (out - g) * 1.08
        out += 3.0
    return np.clip(out, 0, 255)


def bloom(rgb, thr=205, strength=55, r=9):
    bright = np.clip(rgb - thr, 0, 60) / 60.0
    bl = R.box_blur(bright, r)
    return rgb + bl * strength


def vignette(rgb, power=0.62, k=0.30):
    yy, xx = np.mgrid[0:PH2, 0:PW2].astype(np.float32)
    r = np.sqrt(((xx - PW2 / 2) / (PW2 * power)) ** 2 + ((yy - PH2 / 2) / (PH2 * power)) ** 2)
    v = np.clip(1.05 - k * r ** 2, 0.55, 1.0)
    return rgb * v[..., None]


def make_scene(with_shadows):
    bg = Image.open(os.path.join(REFS, 'bg_industrial.jpg')).convert('RGB')
    crop = bg.crop((350, 240, 350 + PW2, 240 + PH2)).resize((PW2, PH2), Image.LANCZOS)
    rgb = np.asarray(crop, np.float32).copy()
    zero = np.zeros((PH2, PW2), np.float32)
    if with_shadows:
        R.paste(rgb, zero, *ground_shadow_layer(), 0, 0)
    sol_rgb, sol_a = soldier_layer(with_shadows)
    R.paste(rgb, zero, sol_rgb, sol_a, 0, 0)
    fog_rgb, fog_a = fog_layer(0.85 if with_shadows else 0.30)
    R.paste(rgb, zero, fog_rgb, fog_a, 0, 0)
    rgb = bloom(rgb)
    rgb = vignette(rgb)
    rgb = grade(rgb, with_shadows)
    return np.clip(rgb, 0, 255)


def panel_mask(radius=14):
    im = Image.new('L', (PW, PH), 0)
    ImageDraw.Draw(im).rounded_rectangle([0, 0, PW - 1, PH - 1], radius=radius, fill=255)
    return np.asarray(im, np.float32) / 255.0


def crosshair_layer(color=(245, 247, 250), alpha=150, gold_dot=False):
    """Прицел от первого лица, центр панели (SS=3). Позиция двигается в сцене."""
    S = 3
    im = Image.new('RGBA', (PW * S, PH * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx, cy = PW // 2 * S, PH // 2 * S
    col = color + (alpha,)
    r = 30 * S
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col, width=2 * S)
    gap, ln = 9 * S, 13 * S
    for (x0, y0, x1, y1) in [(cx, cy - r - gap - ln, cx, cy - r - gap),
                             (cx, cy + r + gap, cx, cy + r + gap + ln),
                             (cx - r - gap - ln, cy, cx - r - gap, cy),
                             (cx + r + gap, cy, cx + r + gap + ln, cy)]:
        d.line([x0, y0, x1, y1], fill=col, width=2 * S)
    if gold_dot:
        d.ellipse([cx - 3 * S, cy - 3 * S, cx + 3 * S, cy + 3 * S], fill=(255, 214, 120, 255))
    else:
        d.ellipse([cx - 2 * S, cy - 2 * S, cx + 2 * S, cy + 2 * S], fill=(255, 220, 140, 220))
    im = im.resize((PW, PH), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    return a[..., :3].copy(), a[..., 3].copy() / 255.0


def kb_view(premade, s, fx=0.5, fy=0.5, out_w=PW, out_h=PH):
    """Ken Burns: область premade размера (PW2/s, PH2/s) с центром (fx,fy) -> out_w x out_h."""
    wv, hv = PW2 / s, PH2 / s
    x0 = (PW2 - wv) * fx
    y0 = (PH2 - hv) * fy
    box = (x0, y0, x0 + wv, y0 + hv)
    im = Image.fromarray(np.clip(premade, 0, 255).astype(np.uint8), 'RGB').crop(box).resize(
        (out_w, out_h), Image.BILINEAR)
    return np.asarray(im, np.float32)


def build_all():
    with_rgb = make_scene(True)
    without_rgb = make_scene(False)
    pm = panel_mask()
    ch_dim = crosshair_layer((200, 205, 212), 130)
    ch_bright = crosshair_layer((248, 250, 252), 190)
    ch_gold = crosshair_layer((255, 214, 120), 235, gold_dot=True)
    return {'with': with_rgb, 'without': without_rgb, 'mask': pm,
            'cross_dim': ch_dim, 'cross_bright': ch_bright, 'cross_gold': ch_gold,
            'pw': PW, 'ph': PH, 'pw2': PW2, 'ph2': PH2, 'kmax': KMAX,
            'soldier_px': (int(CX * PW / PW2), int(410 * PH / PH2))}  # грудь в панель-координатах


if __name__ == '__main__':
    out = build_all()
    os.makedirs(os.path.join(HERE, 'preview3'), exist_ok=True)
    for k in ('with', 'without'):
        Image.fromarray(np.clip(kb_view(out[k], 1.0), 0, 255).astype(np.uint8)).save(
            os.path.join(HERE, 'preview3', f'game_{k}.png'))
    print('game panels ok; солдат(панель-px):', out['soldier_px'])
