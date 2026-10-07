# -*- coding: utf-8 -*-
"""
Видео №2: «Отключение теней через конфиг» (гайд по Steam) — 1080x1920.
Формат как у первого ролика (рамка, пламя, прогресс-бар, шрифты), но с расширенной
визуализацией: мок-окна Windows (Выполнить / Блокнот), печатающийся путь,
поиск по параметру, анимация значения и сравнение «с тенями / без теней».
"""
import json, math, os, random, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import render as R
from render import (W, H, FPS, GOLD, GREEN, RED, LABEL, VALUE_W, DESC, COL, MARGIN_L, MARGIN_R,
                    TOP, BOTTOM, PROGRESS_Y, mask, colorize, gradient_fill, solid, paste, cl, eo, eb)
from common import blend, add_glow, make_rows, title_size

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'wardogs_otkluchenie_teney_konfig_1080x1920.mp4')
REFS = os.path.normpath(os.path.join(HERE, '..', 'assets', 'refs'))
CW = MARGIN_R - MARGIN_L
PATH = r'%LocalAppData%\Wardogs\Saved\Config\WindowsClient'

TIM = json.load(open(os.path.join(HERE, 'timings2.json'))) if os.path.exists(
    os.path.join(HERE, 'timings2.json')) else {'total': 44.26, 'scenes': {}}


def tsc(i, key, default):
    return TIM.get('scenes', {}).get(str(i), {}).get(key, default)


# --------------------------------------------------------------- утилиты рисования
def to_layer(im):
    a = np.asarray(im, np.float32)
    return a[..., :3].copy(), a[..., 3].copy() / 255.0


def rrect(w, h, radius, fill=None, outline=None, ow=2, S=2):
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=radius * S,
                                         fill=fill, outline=outline, width=ow * S)
    return to_layer(im.resize((w, h), Image.LANCZOS))


def line_layer(w, h, color, alpha=255):
    return solid(w, h, color, alpha)


def text_layer(txt, size, weight=600, color=(220, 226, 234), tracking=0.3, name='Montserrat'):
    return colorize(mask(txt, size, weight, tracking, name=name), color)


def win_frame(w, h, title, radius=14, title_h=56, dots=True):
    """Окно в стиле Windows 11: заголовок, точки, разделитель."""
    S = 2
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=radius * S,
                        fill=(24, 26, 31, 255), outline=(58, 61, 69, 255), width=2 * S)
    d.rounded_rectangle([2 * S, 2 * S, (w - 2) * S - 1, title_h * S - 1], radius=(radius - 2) * S,
                        fill=(33, 36, 43, 255))
    d.rectangle([2 * S, (title_h - radius) * S, (w - 2) * S - 1, title_h * S - 1], fill=(33, 36, 43, 255))
    d.line([0, title_h * S, w * S, title_h * S], fill=(58, 61, 69, 255), width=S)
    if dots:
        for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
            cx = (24 + i * 24) * S
            d.ellipse([cx - 7 * S, (title_h // 2 - 7) * S, cx + 7 * S, (title_h // 2 + 7) * S],
                      fill=c + (255,))
    rgb, a = to_layer(im.resize((w, h), Image.LANCZOS))
    t_rgb, t_a = text_layer(title, 26, 600, (198, 205, 214), 0.3)
    paste(rgb, a, t_rgb, t_a, 108, (title_h - t_rgb.shape[0]) // 2)
    return rgb, a


# --------------------------------------------------------------- моки окон
def run_dialog(reveal_px=None, cursor=True):
    """Окно «Выполнить» с печатающимся путём. Возвращает слой и позицию курсора."""
    w, h = CW, 352
    rgb, a = win_frame(w, h, 'Выполнить')
    l_rgb, l_a = text_layer('Введите путь к папке конфигов:', 28, 600, (146, 154, 166), 0.2)
    paste(rgb, a, l_rgb, l_a, 44, 92)
    # поле ввода
    fx, fy, fw, fh = 44, 148, w - 88, 86
    fr, fa = rrect(fw, fh, 10, fill=(14, 15, 18, 255), outline=(70, 74, 83, 255), ow=2)
    paste(rgb, a, fr, fa, fx, fy)
    pm = mask(PATH, 24, 500, 0.0, name='JetBrainsMono')
    pr, pa = colorize(pm, (232, 237, 244))
    cell = pm.width / len(PATH)
    path_dx = fx + 20
    path_dy = fy + (fh - pm.height) // 2
    # кнопки
    bw, bh = 150, 56
    bx, by = w - 44 - bw, h - 34 - bh
    ok_rgb, ok_a = rrect(bw, bh, 9, fill=(58, 48, 22, 255), outline=GOLD + (215,), ow=2)
    paste(rgb, a, ok_rgb, ok_a, bx, by)
    t_rgb, t_a = text_layer('ОК', 30, 700, GOLD, 0.5)
    paste(rgb, a, t_rgb, t_a, bx + (bw - t_rgb.shape[1]) // 2, by + (bh - t_rgb.shape[0]) // 2)
    cbx = bx - 24 - bw
    c_rgb, c_a = rrect(bw, bh, 9, fill=(30, 32, 38, 255), outline=(72, 76, 85, 255), ow=2)
    paste(rgb, a, c_rgb, c_a, cbx, by)
    t2_rgb, t2_a = text_layer('Отмена', 30, 600, (150, 157, 168), 0.2)
    paste(rgb, a, t2_rgb, t2_a, cbx + (bw - t2_rgb.shape[1]) // 2, by + (bh - t2_rgb.shape[0]) // 2)
    return rgb, a, (pr, pa), (path_dx, path_dy), cell, (bx, by, bw, bh)


def notepad(search_reveal=None, highlight=0.0):
    """Окно Блокнота с поиском и найденным параметром."""
    w, h = CW, 486
    rgb, a = win_frame(w, h, 'GameUserSettings.ini — Блокнот')
    # меню: кегль подбирается так, чтобы пункты НЕ залезали на строку поиска
    labels = ('Файл', 'Правка', 'Поиск', 'Вид', 'Справка')
    sx, sy, sw, sh = w - 44 - 300, 62, 300, 48
    limit = sx - 22
    gap = 20
    msize = 24
    while True:
        ws = [mask(l, msize, 600, 0.2).width for l in labels]
        if msize <= 16 or 40 + sum(ws) + gap * (len(labels) - 1) <= limit:
            break
        msize -= 1
    mx = 40
    for lab, wd in zip(labels, ws):
        if mx + wd > limit:
            break
        l_rgb, l_a = text_layer(lab, msize, 600, (140, 147, 158), 0.2)
        paste(rgb, a, l_rgb, l_a, mx, sy + (sh - l_a.shape[0]) // 2)
        mx += wd + gap
    s_rgb, s_a = rrect(sw, sh, 8, fill=(16, 17, 20, 255), outline=(66, 70, 79, 255), ow=2)
    paste(rgb, a, s_rgb, s_a, sx, sy)
    # лупа
    d = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    mag = Image.new('RGBA', (40, 40), (0, 0, 0, 0))
    dm = ImageDraw.Draw(mag)
    dm.ellipse([4, 4, 24, 24], outline=(150, 157, 168, 255), width=3)
    dm.line([22, 22, 33, 33], fill=(150, 157, 168, 255), width=3)
    m_rgb, m_a = to_layer(mag)
    paste(rgb, a, m_rgb, m_a, sx + 10, sy + 5)
    stxt = 'sg.ShadowQuality'
    sm = mask(stxt, 22, 500, 0.0, name='JetBrainsMono')
    sr, sa = colorize(sm, (216, 222, 230))
    cell = sm.width / len(stxt)
    search_dx = sx + 50
    search_dy = sy + (sh - sm.height) // 2
    # тело
    bx, by = 30, 124
    bw, bh = w - 60, h - 124 - 22
    b_rgb, b_a = rrect(bw, bh, 8, fill=(17, 18, 21, 255), outline=(52, 55, 62, 255), ow=2)
    paste(rgb, a, b_rgb, b_a, bx, by)
    # «текст» контекста — приглушённые полосы
    dim_rgb, dim_a = solid(10, 10, (120, 126, 136), 255)
    for i, wd in enumerate((430, 620, 520, 700, 560)):
        seg = solid(min(wd, bw - 120), 13, (126, 133, 144), 108)
        paste(rgb, a, seg[0], seg[1], bx + 26, by + 26 + i * 40)
    # целевая строка
    ly = by + 26 + 5 * 40 + 10
    if highlight > 0.001:
        hl_rgb, hl_a = solid(bw - 40, 62, GOLD, 40 * highlight)
        paste(rgb, a, hl_rgb, hl_a, bx + 20, ly - 10)
        bar_rgb, bar_a = solid(6, 62, GOLD, int(255 * min(1.0, highlight)))
        paste(rgb, a, bar_rgb, bar_a, bx + 20, ly - 10)
    l1 = mask('sg.ShadowQuality', 32, 500, 0.0, name='JetBrainsMono')
    r1, a1 = colorize(l1, (226, 231, 238))
    paste(rgb, a, r1, a1, bx + 40, ly)
    x_off = bx + 40 + l1.width + 2
    eq = mask('=', 32, 500, 0.0, name='JetBrainsMono')
    eqr, eqa = colorize(eq, (150, 157, 168))
    paste(rgb, a, eqr, eqa, x_off, ly)
    val = mask('0', 32, 700, 0.0, name='JetBrainsMono')
    vr, va = colorize(val, GOLD)
    paste(rgb, a, vr, va, x_off + eq.width + 2, ly)
    return rgb, a, (sr, sa), (search_dx, search_dy), cell


def code_block(value='4', show_zero=True):
    """Крупная строка конфига: sg.ShadowQuality=0 / 4."""
    w, h = CW, 156
    rgb, a = rrect(w, h, 12, fill=(18, 19, 23, 255), outline=(66, 70, 79, 255), ow=2)
    pref = mask('sg.ShadowQuality=', 44, 500, 0.0, name='JetBrainsMono')
    pr, pa = colorize(pref, (214, 220, 228))
    px, py = 40, (h - pref.height) // 2
    paste(rgb, a, pr, pa, px, py)
    vx = px + pref.width + 4
    z_rgb, z_a = colorize(mask('0', 62, 700, 0.0, name='JetBrainsMono'), RED)
    f_rgb, f_a = colorize(mask('4', 62, 700, 0.0, name='JetBrainsMono'), GREEN)
    return rgb, a, (z_rgb, z_a), (f_rgb, f_a), (vx, py - 8), (px, py)


def toggle(state='off'):
    """Переключатель «ТЕНИ» + подпись."""
    w, h = 470, 96
    rgb, a = solid(w, h, (0, 0, 0), 0)
    pw, ph = 170, 76
    on = state == 'on'
    t_rgb, t_a = rrect(pw, ph, ph // 2,
                       fill=(58, 48, 22, 255) if on else (34, 36, 41, 255),
                       outline=(GOLD + (220,)) if on else ((78, 82, 91, 255)), ow=2)
    paste(rgb, a, t_rgb, t_a, 0, (h - ph) // 2)
    kn = 56
    kx = (pw - kn - 10) if on else 10
    k_rgb, k_a = solid(kn, kn, GOLD if on else (116, 122, 132), 255)
    km = Image.new('L', (kn, kn), 0)
    ImageDraw.Draw(km).ellipse([0, 0, kn - 1, kn - 1], fill=255)
    k_a = np.asarray(km, np.float32) / 255.0
    paste(rgb, a, k_rgb, k_a, kx, (h - kn) // 2)
    lab = 'ТЕНИ:  ВЫКЛ' if not on else 'ТЕНИ:  ВКЛ'
    color = (150, 157, 168) if not on else GOLD
    l_rgb, l_a = text_layer(lab, 36, 700, color, 0.5)
    paste(rgb, a, l_rgb, l_a, pw + 28, (h - l_rgb.shape[0]) // 2)
    return rgb, a


def check_mark(d=52, color=GREEN):
    """Кружок с галочкой."""
    S = 2
    im = Image.new('RGBA', (d * S, d * S), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    dd.ellipse([2, 2, d * S - 3, d * S - 3], outline=color + (235,), width=4 * S)
    dd.line([d * S * 0.28, d * S * 0.52, d * S * 0.44, d * S * 0.70], fill=color + (255,), width=5 * S)
    dd.line([d * S * 0.44, d * S * 0.70, d * S * 0.74, d * S * 0.30], fill=color + (255,), width=5 * S)
    return to_layer(im.resize((d, d), Image.LANCZOS))


def cross_mark(d=52, color=RED):
    S = 2
    im = Image.new('RGBA', (d * S, d * S), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    dd.ellipse([2, 2, d * S - 3, d * S - 3], outline=color + (235,), width=4 * S)
    dd.line([d * S * 0.32, d * S * 0.32, d * S * 0.68, d * S * 0.68], fill=color + (255,), width=5 * S)
    dd.line([d * S * 0.68, d * S * 0.32, d * S * 0.32, d * S * 0.68], fill=color + (255,), width=5 * S)
    return to_layer(im.resize((d, d), Image.LANCZOS))


def photo_panel(name, box, label, ok, w=CW, h=420):
    """Реальный скриншот из игры: кроп, скругление, затемнение снизу, метка."""
    im = Image.open(os.path.join(REFS, name)).convert('RGB').crop(box).resize((w, h), Image.LANCZOS)
    rgb = np.asarray(im, np.float32).copy()
    rm = Image.new('L', (w, h), 0)
    ImageDraw.Draw(rm).rounded_rectangle([0, 0, w - 1, h - 1], radius=14, fill=255)
    a = np.asarray(rm, np.float32) / 255.0
    grad = np.linspace(1.0, 0.42, 96)[:, None]
    rgb[h - 96:, :] *= grad[..., None]
    fr = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(fr).rounded_rectangle([1, 1, w - 2, h - 2], radius=14,
                                         outline=(74, 78, 87, 255), width=2)
    fa = np.asarray(fr, np.float32); al = fa[..., 3] / 255.0
    rgb = rgb * (1 - al[..., None]) + fa[..., :3] * al[..., None]
    a = np.maximum(a, al)
    col = GREEN if ok else RED
    lm = mask(label, 30, 800, 2.5)
    l_rgb, l_a = colorize(lm, col)
    pw, ph = lm.width + 44, lm.height + 26
    box_rgb, box_a = solid(pw, ph, (10, 10, 12), 205)
    paste(rgb, a, box_rgb, box_a, 18, h - ph - 18)
    bd_rgb, bd_a = rrect(pw, ph, 8, outline=col + (215,), ow=2)
    paste(rgb, a, bd_rgb, bd_a, 18, h - ph - 18)
    paste(rgb, a, l_rgb, l_a, 40, h - ph - 6)
    mk = (check_mark if ok else cross_mark)(46)
    paste(rgb, a, mk[0], mk[1], w - 66, h - 66)
    return rgb, a


def compare_panel(w=CW, h=412, crop=(240, 40, 1680, 900)):
    """Два реальных кадра из игры (та же точка, вид в оптику) для шторки-сравнения.
    Кроп плотнее по объекту: пример «с тенями / без теней» читается крупнее."""
    cwid, chgt = crop[2] - crop[0], crop[3] - crop[1]
    h = int(round(w * chgt / cwid))
    crop = (crop[0], crop[1], crop[2], crop[3])
    layers = []
    for name in ('ex3.jpg', 'ex4.jpg'):
        im = Image.open(os.path.join(REFS, name)).convert('RGB').crop(crop).resize((w, h), Image.LANCZOS)
        rgb = np.asarray(im, np.float32).copy()
        # нижняя вуаль: гасим штампы «SHADOW ON/OFF» с исходников, иначе при проходе
        # шторки два разных текста смешивались в кадре («SHADOW O·IN»)
        yy = np.arange(h, dtype=np.float32)[:, None]
        scrim = np.clip((yy - (h - 96)) / 26.0, 0, 1.0)
        scrim = np.where(yy >= (h - 70), 1.0, scrim)   # ниже — чистый чёрный: штампы не видны вообще
        rgb *= (1.0 - scrim[..., None])
        rm = Image.new('L', (w, h), 0)
        ImageDraw.Draw(rm).rounded_rectangle([0, 0, w - 1, h - 1], radius=14, fill=255)
        a = np.asarray(rm, np.float32) / 255.0
        fr = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ImageDraw.Draw(fr).rounded_rectangle([1, 1, w - 2, h - 2], radius=14,
                                             outline=(84, 88, 98, 255), width=2)
        fa = np.asarray(fr, np.float32); al = fa[..., 3] / 255.0
        rgb = rgb * (1 - al[..., None]) + fa[..., :3] * al[..., None]
        a = np.maximum(a, al)
        layers.append((rgb, a))
    return layers[0], layers[1]


def tag_chip(label, col):
    """Небольшая плашка-подпись для панели сравнения."""
    lm = mask(label, 30, 800, 2.5)
    l_rgb, l_a = colorize(lm, col)
    pw, ph = lm.width + 44, lm.height + 26
    rgb, a = solid(pw, ph, (10, 10, 12), 208)
    bd_rgb, bd_a = rrect(pw, ph, 8, outline=col + (215,), ow=2)
    paste(rgb, a, bd_rgb, bd_a, 0, 0)
    paste(rgb, a, l_rgb, l_a, 22, 12)
    return rgb, a


def scene_panel(kind='with', w=CW, h=260):
    """Стилизованная сцена: игрок на фоне ландшафта, с тенью или без."""
    S = 2
    im = Image.new('RGB', (w * S, h * S))
    d = ImageDraw.Draw(im)
    with_sh = kind.startswith('with')
    if with_sh:
        sky0, sky1 = (56, 30, 24), (162, 78, 40)
        ground0, ground1 = (50, 37, 24), (28, 21, 14)
        hill = (30, 22, 16)
        sun = (252, 168, 66)
    else:
        sky0, sky1 = (22, 40, 56), (48, 104, 118)
        ground0, ground1 = (66, 78, 46), (42, 52, 32)
        hill = (38, 50, 36)
        sun = (255, 240, 186)
    for y in range(h * S):
        p = y / (h * S)
        c = [sky0[i] + (sky1[i] - sky0[i]) * (p ** 1.1) for i in range(3)]
        d.line([0, y, w * S, y], fill=tuple(int(v) for v in c))
    horizon = int(h * 0.60) * S
    # солнце
    sr = 34
    d.ellipse([int(w * 0.74) * S - sr * S, horizon - 118 * S, int(w * 0.74) * S + sr * S, horizon - 50 * S],
              fill=sun)
    # холмы
    d.polygon([(0, horizon), (int(w * 0.22) * S, horizon - 54 * S), (int(w * 0.44) * S, horizon),
               (int(w * 0.66) * S, horizon - 30 * S), (w * S, horizon)], fill=hill)
    for y in range(horizon, h * S):
        p = (y - horizon) / (h * S - horizon)
        c = [ground0[i] + (ground1[i] - ground0[i]) * p for i in range(3)]
        d.line([0, y, w * S, y], fill=tuple(int(v) for v in c))

    def player(cx, base, sc=1.0, sil=(16, 12, 9), outline=None):
        bw, bh = int(26 * sc) * S, int(58 * sc) * S
        hr = int(13 * sc) * S
        d.rounded_rectangle([cx - bw // 2, base - bh, cx + bw // 2, base], radius=int(9 * sc) * S,
                            fill=sil, outline=outline, width=3 * S if outline else 0)
        d.ellipse([cx - hr, base - bh - 2 * hr, cx + hr, base - bh], fill=sil,
                  outline=outline, width=3 * S if outline else 0)

    p1x, p2x = int(w * 0.20) * S, int(w * 0.58) * S
    base = horizon + int(h * 0.30) * S
    if with_sh:
        player(p1x, base, 1.0, (24, 17, 12))
        player(p2x, base, 0.78, (22, 16, 12))
        # длинная тень, накрывающая вторую фигуру
        d.polygon([(p1x - 14 * S, base - 4 * S), (p1x + 16 * S, base - 4 * S),
                   (p2x + 120 * S, base + 26 * S), (p2x + 60 * S, base + 30 * S),
                   (p1x - 6 * S, base + 10 * S)], fill=(12, 9, 7))
    else:
        player(p1x, base, 1.0, (26, 24, 20), outline=(250, 190, 60, 255))
        player(p2x, base, 0.78, (26, 24, 20), outline=(250, 190, 60, 255))
    im = im.resize((w, h), Image.LANCZOS)
    # скругление
    maskim = Image.new('L', (w, h), 0)
    ImageDraw.Draw(maskim).rounded_rectangle([0, 0, w - 1, h - 1], radius=14, fill=255)
    arr = np.asarray(im, np.float32)
    ma = np.asarray(maskim, np.float32) / 255.0
    # рамка
    fr = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(fr).rounded_rectangle([1, 1, w - 2, h - 2], radius=14, outline=(70, 73, 82, 255), width=2)
    fa = np.asarray(fr, np.float32)
    al = (fa[..., 3] / 255.0)
    rgb = arr * (1 - al[..., None]) + fa[..., :3] * al[..., None]
    a = np.maximum(ma, al)
    # подпись и метка
    lab = 'С ТЕНЯМИ' if with_sh else 'БЕЗ ТЕНЕЙ'
    col = RED if with_sh else GREEN
    lm = mask(lab, 27, 800, 3.0)
    l_rgb, l_a = colorize(lm, col)
    box_rgb, box_a = solid(lm.width + 40, lm.height + 22, (12, 12, 14), 190)
    paste(rgb, a, box_rgb, box_a, 18, 16)
    bd_rgb, bd_a = rrect(lm.width + 40, lm.height + 22, 7, outline=col + (200,), ow=2)
    paste(rgb, a, bd_rgb, bd_a, 18, 16)
    paste(rgb, a, l_rgb, l_a, 38, 27)
    mk = (cross_mark if with_sh else check_mark)()
    paste(rgb, a, *mk, w - 74, 16)
    return rgb, a


# --------------------------------------------------------------- сцены
def fit_rows(rows, pitch, lsize, vsize, cw=CW):
    """Строки «лейбл + значение»: подгоняем кегль, чтобы не наезжали друг на друга."""
    k = 1.0
    for lab, val, _c in rows:
        lw = mask(lab, max(18, int(lsize)), 600, 0.6).width
        vw = mask(val, max(18, int(vsize)), 800, 0.2).width
        if lw + vw > cw - 40:
            k = min(k, (cw - 40) / (lw + vw))
    return make_rows(rows, pitch, max(18, int(lsize * k)), max(18, int(vsize * k)), cw)


def scene_hook(idx):
    items = []
    f_rgb, f_a = R.flame(215)
    items.append(dict(kind='pop', rgb=f_rgb, a=f_a, x=(W - f_rgb.shape[1]) // 2, y=300, t0=0.05, dur=0.5,
                      glow=((255, 140, 30), 190, 0.10)))
    y = 300 + f_rgb.shape[0] + 58
    c_rgb, c_a = R.build_chip('STEAM · WARDOGS', GOLD)
    items.append(dict(kind='fade_slide', rgb=c_rgb, a=c_a, x=(W - c_rgb.shape[1]) // 2, y=y, dy=18,
                      t0=0.30, dur=0.30))
    y += c_rgb.shape[0] + 54
    ts = min(title_size(t, W - 260) for t in ['ТЕНИ В НОЛЬ'])
    tp = int(ts * 1.06)
    t_rgb, t_a = R.build_title(['ТЕНИ В НОЛЬ'], ts, tp, 'center', W - 200)
    items.append(dict(kind='fade_slide', rgb=t_rgb, a=t_a, x=100, y=y, dy=26, t0=0.42, dur=0.42,
                      glow=(GOLD, 150, 0.05)))
    y += t_rgb.shape[0] + 52
    d_rgb, d_a = gradient_fill(R.mask_lines(['Видно всех — даже в тумане'], 44, 600, 0.2, 62,
                                            align='center', width=W - 200),
                               [(0, (146, 154, 165)), (1, (172, 180, 191))])
    items.append(dict(kind='fade_slide', rgb=d_rgb, a=d_a, x=100, y=y, dy=22, t0=0.82, dur=0.34))
    y += d_rgb.shape[0] + 54
    b_rgb, b_a = R.build_badge('2 МИНУТЫ → +КОНТРАСТ', GOLD)
    items.append(dict(kind='pop', rgb=b_rgb, a=b_a, x=(W - b_rgb.shape[1]) // 2, y=y, t0=1.28, dur=0.40))
    y += b_rgb.shape[0] + 40
    s_rgb, s_a = text_layer('ГАЙД ПО КОНФИГУ · ТЕНИ', 28, 700, (112, 119, 130), 6.0)
    items.append(dict(kind='fade_slide', rgb=s_rgb, a=s_a, x=(W - s_rgb.shape[1]) // 2, y=y + 26,
                      dy=18, t0=1.74, dur=0.34))
    return items


def scrim_layer(w, h, top_frac=0.0, amax=0.9, exp=0.75):
    """Мягкая затемняющая подложка (для наложения заголовка на кадр)."""
    yy = np.arange(h, dtype=np.float32)[:, None] / max(1.0, h - 1)
    a = np.clip((yy - top_frac) / (1 - top_frac), 0, 1.0) ** exp * amax
    rgb = np.zeros((h, w, 3), np.float32)
    return rgb, np.repeat(a, w, axis=1)


def scene_hook_payoff(idx):
    """Хук «результат сразу»: крупный реальный кадр игры до/после, а НАЗВАНИЕ
    наложено прямо на кадр. Первые секунды разгружены: сначала только сравнение
    и заголовок, остальные элементы появляются позже и по одному."""
    items = []
    PW = CW
    ph = int(round(PW * (900 - 40) / (1680 - 240)))      # ~503 px: пример крупнее
    PY = 300
    wl, wol = compare_panel(w=PW)
    sw = PW // 2
    panel = wl[0].copy(); pa = wl[1].copy()
    panel[:, sw:] = wol[0][:, sw:]; pa[:, sw:] = wol[1][:, sw:]
    items.append(dict(kind='pop', rgb=panel, a=pa, x=MARGIN_L, y=PY, dy=16, t0=0.04, dur=0.38))
    dv_rgb, dv_a = solid(4, ph - 40, (250, 200, 90), 235)
    items.append(dict(kind='grow', rgb=dv_rgb, a=dv_a, x=MARGIN_L + sw - 2, y=PY + 20, t0=0.24, dur=0.32))
    t1 = tag_chip('С ТЕНЯМИ', RED)
    t2 = tag_chip('БЕЗ ТЕНЕЙ', GREEN)
    items.append(dict(kind='fade_slide', rgb=t1[0], a=t1[1], x=MARGIN_L + 16, y=PY + 16, dy=-10,
                      t0=0.34, dur=0.25))
    items.append(dict(kind='fade_slide', rgb=t2[0], a=t2[1], x=MARGIN_L + PW - t2[0].shape[1] - 16,
                      y=PY + 16, dy=-10, t0=0.42, dur=0.25))
    # заголовок — НА КАДРЕ: мягкая подложка снизу кадра + название поверх
    sc_h = 205
    sc_rgb, sc_a = scrim_layer(PW, sc_h, top_frac=0.0, amax=0.92, exp=0.72)
    items.append(dict(kind='fade_slide', rgb=sc_rgb, a=sc_a, x=MARGIN_L, y=PY + ph - sc_h, dy=12,
                      t0=0.50, dur=0.28))
    ts = min(title_size(t, W - 300) for t in ['ТЕНИ В НОЛЬ'])
    tp = int(ts * 1.06)
    t_rgb, t_a = R.build_title(['ТЕНИ В НОЛЬ'], ts, tp, 'center', W - 300)
    items.append(dict(kind='fade_slide', rgb=t_rgb, a=t_a, x=(W - t_rgb.shape[1]) // 2,
                      y=PY + ph - t_rgb.shape[0] - 26, dy=18, t0=0.66, dur=0.38,
                      glow=(GOLD, 130, 0.04)))
    # ниже — по одному элементу, с паузами: первые секунды не перегружены
    y = PY + ph + 42
    d_rgb, d_a = gradient_fill(R.mask_lines(['Видно всех — даже в тумане'], 42, 600, 0.2, 60,
                                            align='center', width=W - 200),
                               [(0, (146, 154, 165)), (1, (172, 180, 191))])
    items.append(dict(kind='fade_slide', rgb=d_rgb, a=d_a, x=100, y=y, dy=22, t0=1.34, dur=0.34))
    y += d_rgb.shape[0] + 40
    b_rgb, b_a = R.build_badge('2 МИНУТЫ → +КОНТРАСТ', GOLD)
    items.append(dict(kind='pop', rgb=b_rgb, a=b_a, x=(W - b_rgb.shape[1]) // 2, y=y, t0=1.72, dur=0.40))
    y += b_rgb.shape[0] + 38
    c_rgb, c_a = R.build_chip('STEAM · WARDOGS', GOLD)
    items.append(dict(kind='fade_slide', rgb=c_rgb, a=c_a, x=(W - c_rgb.shape[1]) // 2, y=y,
                      dy=16, t0=2.06, dur=0.30))
    return items


def scene_step1(idx):
    items = []
    y = TOP
    c_rgb, c_a = R.build_chip('ШАГ 1', GOLD)
    items.append(dict(kind='fade_slide', rgb=c_rgb, a=c_a, x=MARGIN_L, y=y, dx=-40, t0=0.06, dur=0.24))
    y += c_rgb.shape[0] + 50
    ts = min(title_size(t, CW - 46) for t in ['ПУТЬ К КОНФИГУ'])
    tp = int(ts * 1.06)
    t_rgb, t_a = R.build_title(['ПУТЬ К КОНФИГУ'], ts, tp, 'left', None)
    items.append(dict(kind='wipe', rgb=t_rgb, a=t_a, x=MARGIN_L + 46, y=y, soft=110, t0=0.16, dur=0.44))
    b_rgb, b_a = solid(9, tp - 26, GOLD, 255)
    items.append(dict(kind='grow', rgb=b_rgb, a=b_a, x=MARGIN_L, y=y + 10, t0=0.21, dur=0.40))
    y += tp + 26
    rows = fit_rows([('ИГРА', 'ЗАКРЫТА ПОЛНОСТЬЮ', 'g'), ('WIN + R', 'ОТКРЫТЬ «ВЫПОЛНИТЬ»', 'g')],
                    116, 42, 44)
    ry = y
    for i, it in enumerate(rows):
        it['y'] = ry
        if it['kind'] == 'fade_slide':
            it['t0'] = 0.48 + (i // 2) * 0.22
            it['dur'] = 0.24
        else:
            it['t0'] = 0.58 + (i // 2) * 0.22
            it['dur'] = 0.20
        ry += it['h']
    items += rows
    y = ry + 40
    d_rgb, d_a, path_l, ppos, cell, okbox = run_dialog()
    items.append(dict(kind='pop', rgb=d_rgb, a=d_a, x=MARGIN_L, y=y, dy=16, t0=0.95, dur=0.42))
    p_rgb, p_a = solid(4, 42, GOLD, 255)
    items.append(dict(kind='type', rgb=path_l[0], a=path_l[1], x=MARGIN_L + ppos[0], y=y + ppos[1],
                      t0=1.30, dur=1.9, soft=14))
    items.append(dict(kind='cursor', rgb=p_rgb, a=p_a, x=0, y=0, t0=1.30, dur=1.9,
                      base_x=MARGIN_L + ppos[0], base_y=y + ppos[1] - 4, cell=cell))
    # вспышка на кнопке ОК
    ob = solid(okbox[2] + 8, okbox[3] + 8, GOLD, 90)
    items.append(dict(kind='blink', rgb=ob[0], a=ob[1], x=MARGIN_L + okbox[0] - 4, y=y + okbox[1] - 4,
                      t0=3.05, dur=0.9, period=0.42))
    y += d_rgb.shape[0] + 30
    n_rgb, n_a = R.build_chip('ENTER', GREEN)
    items.append(dict(kind='pop', rgb=n_rgb, a=n_a, x=MARGIN_L, y=y, t0=3.10, dur=0.34))
    cap_rgb, cap_a = text_layer('после вставки пути', 28, 600, (138, 146, 158), 0.4)
    items.append(dict(kind='fade_slide', rgb=cap_rgb, a=cap_a, x=MARGIN_L + n_rgb.shape[1] + 22,
                      y=y + 12, dx=-16, t0=3.22, dur=0.30))
    return items


def scene_step2(idx):
    items = []
    y = TOP
    c_rgb, c_a = R.build_chip('ШАГ 2', GOLD)
    items.append(dict(kind='fade_slide', rgb=c_rgb, a=c_a, x=MARGIN_L, y=y, dx=-40, t0=0.06, dur=0.24))
    y += c_rgb.shape[0] + 50
    ts = min(title_size(t, CW - 46) for t in ['НАЙДИ ПАРАМЕТР'])
    tp = int(ts * 1.06)
    t_rgb, t_a = R.build_title(['НАЙДИ ПАРАМЕТР'], ts, tp, 'left', None)
    items.append(dict(kind='wipe', rgb=t_rgb, a=t_a, x=MARGIN_L + 46, y=y, soft=110, t0=0.16, dur=0.44))
    b_rgb, b_a = solid(9, tp - 26, GOLD, 255)
    items.append(dict(kind='grow', rgb=b_rgb, a=b_a, x=MARGIN_L, y=y + 10, t0=0.21, dur=0.40))
    y += tp + 26
    rows = fit_rows([('ОТКРЫТЬ', 'БЛОКНОТОМ', 'o'), ('CTRL + F', 'ПОИСК ПО ФАЙЛУ', 'g')], 104, 40, 42)
    ry = y
    for i, it in enumerate(rows):
        it['y'] = ry
        if it['kind'] == 'fade_slide':
            it['t0'] = 0.48 + (i // 2) * 0.22
            it['dur'] = 0.24
        else:
            it['t0'] = 0.58 + (i // 2) * 0.22
            it['dur'] = 0.20
        ry += it['h']
    items += rows
    y = ry + 36
    np_rgb, np_a, search_l, spos, scell = notepad()
    np_hl = notepad(highlight=1.0)
    items.append(dict(kind='pop', rgb=np_rgb, a=np_a, x=MARGIN_L, y=y, dy=16, t0=0.95, dur=0.42))
    items.append(dict(kind='type', rgb=search_l[0], a=search_l[1], x=MARGIN_L + spos[0],
                      y=y + spos[1], t0=1.30, dur=1.15, soft=14))
    items.append(dict(kind='highlight', rgb=np_rgb, a=np_a, rgb2=np_hl[0], a2=np_hl[1],
                      x=MARGIN_L, y=y, t0=2.60, dur=0.5))
    return items


def scene_step3(idx):
    items = []
    y = TOP
    c_rgb, c_a = R.build_chip('ШАГ 3', GOLD)
    items.append(dict(kind='fade_slide', rgb=c_rgb, a=c_a, x=MARGIN_L, y=y, dx=-40, t0=0.06, dur=0.24))
    y += c_rgb.shape[0] + 50
    ts = min(title_size(t, CW - 46) for t in ['ПОСТАВЬ 4'])
    tp = int(ts * 1.06)
    t_rgb, t_a = R.build_title(['ПОСТАВЬ 4'], ts, tp, 'left', None)
    items.append(dict(kind='wipe', rgb=t_rgb, a=t_a, x=MARGIN_L + 46, y=y, soft=110, t0=0.16, dur=0.44))
    b_rgb, b_a = solid(9, tp - 26, GOLD, 255)
    items.append(dict(kind='grow', rgb=b_rgb, a=b_a, x=MARGIN_L, y=y + 10, t0=0.21, dur=0.40))
    y += tp + 22
    cb_rgb, cb_a, zero, four, vpos, ppos = code_block()
    items.append(dict(kind='wipe', rgb=cb_rgb, a=cb_a, x=MARGIN_L, y=y, soft=240, t0=0.55, dur=0.40))
    # «0» появляется и ПОЛНОСТЬЮ гаснет, и только потом на его месте проявляется «4»
    # (никакого наложения глифов: смена значения строго последовательная)
    items.append(dict(kind='fade_slide', rgb=zero[0], a=zero[1], x=MARGIN_L + vpos[0], y=y + vpos[1],
                      dy=0, t0=0.80, dur=0.25, fade_out=(1.38, 0.14)))
    items.append(dict(kind='fade_slide', rgb=four[0], a=four[1], x=MARGIN_L + vpos[0], y=y + vpos[1],
                      dy=-12, t0=1.56, dur=0.30, sfx='whoosh_down.wav'))
    ck = check_mark(58)
    items.append(dict(kind='pop', rgb=ck[0], a=ck[1], x=MARGIN_L + vpos[0] + 66, y=y + vpos[1] + 8,
                      t0=1.94, dur=0.40, glow=(GREEN, 90, 0.14)))
    y += cb_rgb.shape[0] + 34
    rows = fit_rows([('СОХРАНИТЬ', 'CTRL + S', 'o'),
                     ('ТОЛЬКО ДЛЯ ЧТЕНИЯ', 'ВКЛЮЧИТЬ', 'g'),
                     ('МЕНЮ НАСТРОЕК', 'НЕ ТРОГАТЬ', 'r')], 98, 39, 41)
    ry = y
    for i, it in enumerate(rows):
        it['y'] = ry
        if it['kind'] == 'fade_slide':
            it['t0'] = 2.30 + (i // 2) * 0.24
            it['dur'] = 0.24
        else:
            it['t0'] = 2.42 + (i // 2) * 0.24
            it['dur'] = 0.20
        ry += it['h']
    items += rows
    y = ry + 34
    n_rgb, n_a = R.build_note('ВАЖНО',
                              'Любое изменение в меню настроек сбросит тени — просто повтори шаг с конфигом.',
                              RED, CW)
    items.append(dict(kind='boxdraw', rgb=n_rgb, a=n_a, x=MARGIN_L, y=y, t0=3.55, dur=0.45))
    y += n_rgb.shape[0] + 36
    t_on = toggle('on')
    t_off = toggle('off')
    items.append(dict(kind='fade_slide', rgb=t_on[0], a=t_on[1], x=MARGIN_L, y=y, dy=16, t0=4.65,
                      dur=0.34, fade_out=(5.26, 0.14), sfx='shimmer.wav', sfxg=0.34))
    items.append(dict(kind='fade_slide', rgb=t_off[0], a=t_off[1], x=MARGIN_L, y=y, dy=-10, t0=5.42,
                      dur=0.30, sfx='whoosh_down.wav', sfxg=0.22))
    return items


def scene_result(idx):
    items = []
    y = TOP
    c_rgb, c_a = R.build_chip('РЕЗУЛЬТАТ', GREEN)
    items.append(dict(kind='fade_slide', rgb=c_rgb, a=c_a, x=MARGIN_L, y=y, dx=-40, t0=0.06, dur=0.24))
    y += c_rgb.shape[0] + 30
    ts = min(title_size(t, CW - 46) for t in ['ВИДНО ВСЕХ'])
    tp = int(ts * 1.06)
    t_rgb, t_a = R.build_title(['ВИДНО ВСЕХ'], ts, tp, 'left', None)
    items.append(dict(kind='wipe', rgb=t_rgb, a=t_a, x=MARGIN_L + 46, y=y, soft=110, t0=0.16, dur=0.44))
    b_rgb, b_a = solid(9, tp - 26, GREEN, 255)
    items.append(dict(kind='grow', rgb=b_rgb, a=b_a, x=MARGIN_L, y=y + 10, t0=0.21, dur=0.40))
    y += tp + 22
    # реальные кадры из игры: та же точка, шторка «с тенями → без теней».
    # Более плотный кроп -> объект сравнения крупнее (главный «пример» ролика).
    panel_w = CW
    ph = int(round(panel_w * (900 - 40) / (1680 - 240)))
    with_l, without_l = compare_panel(w=panel_w)
    items.append(dict(kind='pop', rgb=with_l[0], a=with_l[1], x=MARGIN_L, y=y, dy=16, t0=0.62, dur=0.42))
    items.append(dict(kind='compare', rgb=without_l[0], a=without_l[1], x=MARGIN_L, y=y,
                      t0=1.70, dur=1.35))
    items.append(dict(kind='compdivider', rgb=with_l[0][:1, :1], a=with_l[1][:1, :1], x=MARGIN_L, y=y,
                      t0=1.70, dur=1.35, h=ph, w=panel_w))
    tag_a = tag_chip('С ТЕНЯМИ', RED)
    tag_b = tag_chip('БЕЗ ТЕНЕЙ', GREEN)
    tx = MARGIN_L + panel_w - tag_a[0].shape[1] - 16
    items.append(dict(kind='fade_slide', rgb=tag_a[0], a=tag_a[1], x=tx, y=y + 16, dy=-12, t0=1.15, dur=0.3,
                      fade_out=(2.45, 0.45)))
    items.append(dict(kind='fade_slide', rgb=tag_b[0], a=tag_b[1], x=MARGIN_L + 16, y=y + 16, dy=-12,
                      t0=1.95, dur=0.3))
    # подпись: это настоящие кадры из игры
    lbm = mask('РЕАЛЬНЫЕ КАДРЫ ИЗ ИГРЫ', 24, 700, 3.0)
    lb_rgb, lb_a = solid(lbm.width + 36, lbm.height + 22, (10, 10, 12), 208)
    lb_bd = rrect(lbm.width + 36, lbm.height + 22, 8, outline=(96, 102, 112, 210), ow=2)
    paste(lb_rgb, lb_a, lb_bd[0], lb_bd[1], 0, 0)
    paste(lb_rgb, lb_a, *colorize(lbm, (168, 176, 186)), 18, 11)
    items.append(dict(kind='fade_slide', rgb=lb_rgb, a=lb_a, x=MARGIN_L + 18,
                      y=y + ph - lb_rgb.shape[0] - 18, dy=10, t0=1.15, dur=0.30))
    y += ph + 26
    rows = fit_rows([('ТУМАН / ЗАКАТ', 'МОДЕЛИ НЕ ПРЯЧУТСЯ', 'g'), ('КОНТРАСТ', 'ВЫШЕ', 'g')], 104, 41, 43)
    ry = y
    for i, it in enumerate(rows):
        it['y'] = ry
        if it['kind'] == 'fade_slide':
            it['t0'] = 3.20 + (i // 2) * 0.20
            it['dur'] = 0.24
        else:
            it['t0'] = 3.30 + (i // 2) * 0.20
            it['dur'] = 0.20
        ry += it['h']
    items += rows
    y = ry + 26
    bx_rgb, bx_a = R.build_box_result('БЕЗ ТЕНЕЙ', 'МОДЕЛИ ВИДНО СРАЗУ', GREEN, CW, bh=150)
    items.append(dict(kind='pop', rgb=bx_rgb, a=bx_a, x=MARGIN_L, y=y, t0=4.05, dur=0.42,
                      glow=(GREEN, 110, 0.08)))
    cr_rgb, cr_a = text_layer('Скриншоты: Bryce · гайд в Steam Community', 24, 600, (96, 103, 114), 0.4)
    items.append(dict(kind='fade_slide', rgb=cr_rgb, a=cr_a, x=MARGIN_L, y=y + bx_rgb.shape[0] + 16,
                      dy=14, t0=4.45, dur=0.34))
    return items


def scene_cta(idx):
    items = []
    f_rgb, f_a = R.flame(205)
    items.append(dict(kind='pop', rgb=f_rgb, a=f_a, x=(W - f_rgb.shape[1]) // 2, y=430, t0=0.05, dur=0.5,
                      glow=((255, 140, 30), 190, 0.10)))
    y = 430 + f_rgb.shape[0] + 44
    ts = min(title_size(t, W - 260) for t in ['СОХРАНИ', 'И ПОДПИШИСЬ'])
    tp = int(ts * 1.06)
    t_rgb, t_a = R.build_title(['СОХРАНИ', 'И ПОДПИШИСЬ'], ts, tp, 'center', W - 200)
    items.append(dict(kind='fade_slide', rgb=t_rgb, a=t_a, x=100, y=y, dy=26, t0=0.42, dur=0.42))
    y += t_rgb.shape[0] + 54
    d_rgb, d_a = gradient_fill(R.mask_lines(['Чтобы не потерять', 'настройки'], 45, 600, 0.2, 64,
                                            align='center', width=W - 200),
                               [(0, (146, 154, 165)), (1, (172, 180, 191))])
    items.append(dict(kind='fade_slide', rgb=d_rgb, a=d_a, x=100, y=y, dy=22, t0=0.82, dur=0.34))
    y += d_rgb.shape[0] + 56
    m = mask('WARDOGS', 50, 900, 8)
    br_rgb, br_a = colorize(m, GOLD)
    items.append(dict(kind='fade_slide', rgb=br_rgb, a=br_a, x=(W - m.width) // 2, y=y, dy=24,
                      t0=1.42, dur=0.34))
    ln_rgb, ln_a = solid(W - 380, 2, (52, 54, 58), 255)
    items.append(dict(kind='wipe', rgb=ln_rgb, a=ln_a, x=190, y=y - 40, soft=200, t0=1.34, dur=0.34))
    items.append(dict(kind='wipe', rgb=ln_rgb, a=ln_a, x=190, y=y + m.height + 30, soft=200,
                      t0=1.34, dur=0.34))
    y += m.height + 60
    s_rgb, s_a = text_layer('ЛУЧШИЕ НАСТРОЙКИ ГРАФИКИ', 29, 700, (110, 117, 128), 7.0)
    items.append(dict(kind='fade_slide', rgb=s_rgb, a=s_a, x=(W - s_rgb.shape[1]) // 2, y=y + 30,
                      dy=18, t0=1.74, dur=0.34))
    return items


SCENES = [scene_hook, scene_step1, scene_step2, scene_step3, scene_result, scene_cta]


# --------------------------------------------------------------- рендер кадра
def crossfade_layer(frame, rgb1, a1, rgb2, a2, x, y, wgt):
    """Смешение двух слоёв по премультиплицированной альфе.
    ВАЖНО: раньше брался max(a1, a2) — из-за этого два РАЗНЫХ текста
    (например «0» и «4») сливались в один глиф. Теперь каждый слой
    проявляется только со своей альфой: в конце виден ровно второй текст."""
    if wgt <= 0.001:
        blend(frame, rgb1, a1, x, y); return
    if wgt >= 0.999:
        blend(frame, rgb2, a2, x, y); return
    A = a1 * (1 - wgt) + a2 * wgt
    num = rgb1 * (a1 * (1 - wgt))[..., None] + rgb2 * (a2 * wgt)[..., None]
    rgb = num / np.maximum(A, 1e-6)[..., None]
    blend(frame, rgb, A, x, y)


def draw_item(frame, it, t, glow_cache):
    kd = it['kind']
    t0, du = it.get('t0', 0.0), it.get('dur', 0.3)
    p = cl((t - t0) / du)
    x, y = it['x'], it['y']
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
    elif kd == 'wipe':
        blend(frame, it['rgb'], it['a'], int(x), int(y), wipe=(eo(p), it.get('soft', 90)))
    elif kd == 'grow':
        blend(frame, it['rgb'], it['a'], int(x), int(y), grow=eo(p))
    elif kd == 'divider':
        blend(frame, it['rgb'], it['a'], int(x), int(y), alpha=p)
    elif kd == 'boxdraw':
        blend(frame, it['rgb'], it['a'], int(x), int(y), wipe=(eo(p), 300), alpha=min(1.0, p * 1.4))
    elif kd == 'crossfade':
        if t < t0:
            return
        w2 = eo(cl((t - t0) / du))
        crossfade_layer(frame, it['rgb'], it['a'], it['rgb2'], it['a2'], int(x), int(y), w2)
    elif kd == 'type':
        if p <= 0:
            return
        blend(frame, it['rgb'], it['a'], int(x), int(y), wipe=(p, it.get('soft', 10)))
    elif kd == 'cursor':
        cw, chh = it['rgb'].shape[1], it['rgb'].shape[0]
        px = it['base_x'] + it['cell'] * int(cl((t - t0) / du) * len(PATH))
        if t < t0:
            return
        al = 1.0 if (t - t0) < du else (0.5 if math.sin(t * 12) > -0.2 else 0.06)
        blend(frame, it['rgb'], it['a'], int(px), int(it['base_y']), alpha=al)
    elif kd == 'blink':
        if t < t0:
            return
        al = (math.sin((t - t0) / it.get('period', 0.4) * math.pi * 2) * 0.5 + 0.5) * 0.9 * \
             max(0.0, 1 - (t - t0) / (du * 1.6))
        if al > 0.02:
            blend(frame, it['rgb'], it['a'], int(x), int(y), alpha=al)
    elif kd == 'compare':
        if p <= 0:
            return
        blend(frame, it['rgb'], it['a'], int(x), int(y), wipe=(eo(p), 26))
    elif kd == 'compdivider':
        if p <= 0 or p >= 1:
            return
        k = eo(p)
        px = it['x'] + int(it['w'] * k)
        bar_rgb, bar_a = solid(4, it['h'] - 40, (250, 200, 90), 235)
        blend(frame, bar_rgb, bar_a, px - 2, int(it['y']) + 20)
        dot = glow_cache.get(('divider_dot', 0))
        if dot is None:
            dot = R.glow_sprite(64, (255, 214, 120), 2.2)
            glow_cache[('divider_dot', 0)] = dot
        add_glow(frame, dot[0], dot[1], px - 32, int(it['y']) + it['h'] // 2 - 32, 0.5)
    elif kd == 'highlight':
        if t < t0:
            return
        k = eo(cl((t - t0) / du))
        crossfade_layer(frame, it['rgb'], it['a'], it['rgb2'], it['a2'], int(x), int(y), k)
    # свечение
    if it.get('glow') and p > 0:
        col, r, k = it['glow']
        key = (r, tuple(col))
        if key not in glow_cache:
            glow_cache[key] = R.glow_sprite(r, col, 2.3)
        spr_rgb, spr_a = glow_cache[key]
        w = it['rgb'].shape[1]
        add_glow(frame, spr_rgb, spr_a, int(x + w * 0.5 - r), int(y + it['rgb'].shape[0] * 0.5 - r),
                 k * min(1.0, p * 1.5))


def main():
    random.seed(11); np.random.seed(11)
    base = R.radial_bg()
    fr_rgb, fr_a = R.corner_frame()
    ft_rgb, ft_a = R.footer_layer(text='WARDOGS · ГАЙД ПО КОНФИГУ')
    paste(base, np.zeros((H, W), np.float32), fr_rgb, fr_a, 0, 0)
    paste(base, np.zeros((H, W), np.float32), ft_rgb, ft_a, (W - ft_rgb.shape[1]) // 2, 1608)

    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    scenes = SCENES
    out_path = OUT
    if mode == 'hookA':
        scenes = [scene_hook_payoff] + SCENES[1:]
        out_path = os.path.join(HERE, '..', 'wardogs_otkluchenie_teney_konfig_hookA_mute.mp4')
    total = TIM.get('total', 44.26)
    dur_list = [tsc(i, 'dur', 7.0) for i in range(len(scenes))]
    scale = total / sum(dur_list)
    dur_list = [round(d * scale, 3) for d in dur_list]
    glow_cache = {}

    preview = len(sys.argv) > 1 and sys.argv[1] == 'preview'
    if preview:
        os.makedirs(os.path.join(HERE, 'preview2'), exist_ok=True)
        gt = 0.0
        for si, fn in enumerate(scenes):
            items = fn(si)
            for tag, tt in (('end', dur_list[si] - 0.1), ('mid', dur_list[si] * 0.55)):
                frame = base.copy()
                for it in items:
                    draw_item(frame, it, tt, glow_cache)
                gp = (gt + tt) / total
                tr_rgb, tr_a = solid(CW, 5, (44, 46, 50), 255)
                blend(frame, tr_rgb, tr_a, MARGIN_L, PROGRESS_Y, alpha=0.9)
                f_rgb, f_a = solid(max(2, int(CW * gp)), 5, GOLD, 255)
                blend(frame, f_rgb, f_a, MARGIN_L, PROGRESS_Y, alpha=0.95)
                Image.fromarray(np.clip(frame, 0, 255).astype(np.uint8)).save(
                    os.path.join(HERE, 'preview2', f'scene{si+1}_{tag}.png'))
            bot = max((it['y'] + it['rgb'].shape[0]) for it in items
                      if it.get('y', 0) > 0 and it['kind'] != 'cursor')
            over = [it['kind'] for it in items if it.get('y', 0) + it['rgb'].shape[0] > BOTTOM + 6
                    and it['kind'] not in ('cursor',)]
            print(f'  preview сцена {si+1} ({dur_list[si]:.2f}s) нижняя граница {bot}px' +
                  (f'  ПЕРЕПОЛНЕНИЕ: {over}' if over else ''))
            gt += dur_list[si]
        return

    # таймлайн для звукового микса
    tl = {'fps': FPS, 'total': round(sum(dur_list), 3), 'scenes': []}
    acc = 0.0
    for si, fn in enumerate(scenes):
        items = fn(si)
        bot = max((it['y'] + it['rgb'].shape[0]) for it in items if it.get('y', 0) > 0 and it['kind'] != 'cursor')
        flag = 'ок' if bot <= BOTTOM + 6 else f'ПЕРЕПОЛНЕНИЕ +{bot - BOTTOM:.0f}px'
        print(f'  сцена {si+1}: нижняя граница {bot}px ({flag})')
        tl['scenes'].append({'start': round(acc, 3), 'dur': dur_list[si],
                             'items': [{'kind': it['kind'], 't0': round(acc + it.get('t0', 0), 3),
                                        'dur': it.get('dur', 0.3), 'n': it.get('n'),
                                        'sfx': it.get('sfx'), 'sfxg': it.get('sfxg')} for it in items]})
        acc += dur_list[si]
    json.dump(tl, open(os.path.join(HERE, 'timeline2.json'), 'w'), ensure_ascii=False, indent=1)
    print('таймлайн: timeline2.json')

    ffmpeg = __import__('imageio_ffmpeg').get_ffmpeg_exe()
    cmd = [ffmpeg, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium',
           '-crf', '18', '-pix_fmt', 'yuv420p', '-profile:v', 'high', '-level', '4.2', '-g', '60',
           '-movflags', '+faststart', out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    noise = (np.random.rand(H + 60, W + 60).astype(np.float32) - 0.5) * 2.0
    parts = []
    for _ in range(14):
        parts.append(dict(x=random.uniform(60, W - 60), y0=random.uniform(1560, 1900),
                          sp=random.uniform(22, 52), ph=random.uniform(0, 6.3),
                          r=random.choice([70, 110, 150]), k=random.uniform(0.035, 0.07),
                          col=random.choice([GOLD, (255, 150, 40), (255, 210, 120)]),
                          amp=random.uniform(14, 42)))
    sprites = {(p['r'], tuple(p['col'])): R.glow_sprite(p['r'], p['col'], 2.6) for p in parts}
    glow_dot = R.glow_sprite(24, GOLD, 2.2)

    gt = 0.0
    print(f'сцен: {len(scenes)}, длительность: {sum(dur_list):.2f}s')
    for si, fn in enumerate(scenes):
        items = fn(si)
        nfr = int(round(dur_list[si] * FPS))
        for fi in range(nfr):
            t = fi / FPS
            frame = base.copy()
            fl = max(0.0, 1 - t / 0.16) ** 2
            if fl > 0.001:
                frame += fl * 13.0 * np.array([1.0, 0.72, 0.3], np.float32)
            for p in parts:
                sp_rgb, sp_a = sprites[(p['r'], tuple(p['col']))]
                life = (gt * p['sp'] + p['ph'] * 40) % 900
                y = p['y0'] - life
                x = p['x'] + p['amp'] * math.sin(gt * 0.7 + p['ph'])
                env = math.sin(math.pi * min(1.0, max(0.0, life / 900.0)))
                add_glow(frame, sp_rgb, sp_a, int(x), int(y), p['k'] * env * 0.9)
            for it in items:
                draw_item(frame, it, t, glow_cache)
            gp = (gt + t) / total
            tr_rgb, tr_a = solid(CW, 5, (44, 46, 50), 255)
            blend(frame, tr_rgb, tr_a, MARGIN_L, PROGRESS_Y, alpha=0.9)
            f_rgb, f_a = solid(max(2, int(CW * gp)), 5, GOLD, 255)
            blend(frame, f_rgb, f_a, MARGIN_L, PROGRESS_Y, alpha=0.95)
            add_glow(frame, *glow_dot, MARGIN_L + int(CW * gp) - 24, PROGRESS_Y - 22, 0.22)
            oy = (fi * 37) % 60; ox = (fi * 53) % 60
            frame += noise[oy:oy + H, ox:ox + W][..., None] * 1.9
            np.clip(frame, 0, 255, out=frame)
            proc.stdin.write(frame.astype(np.uint8).tobytes())
        gt += dur_list[si]
        print(f'  сцена {si+1}/{len(scenes)} готова ({gt:.1f}s)')
    proc.stdin.close(); proc.wait()
    print('готово:', out_path)


if __name__ == '__main__':
    main()
