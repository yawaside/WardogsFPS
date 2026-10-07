# -*- coding: utf-8 -*-
"""
Сцены видео №3. Тайминги под оригинальную озвучку (wardogs2_audio.mp3):
  сцена 1 «хук»      0.000–7.125   (VO 1.28–6.78)
  сцена 2 «шаг 1»    7.125–15.479  (VO 8.68–15.13)
  сцена 3 «шаг 2»    15.479–22.197 (VO 17.03–21.85)
  сцена 4 «шаг 3»    22.197–31.342 (VO 23.85–30.99)
  сцена 5 «результат» 31.342–38.091 (VO 32.74–37.74)
  сцена 6 «CTA»      38.091–44.922 (VO 39.37–43.62)
Хук усилен: сначала «боль» (убийство из тени), через ~1.3с — вспышка и «решение»
(видно всех), прицел «находит» цель. Первые секунды — без голоса, чистый визуал.
"""
import os
import numpy as np
from PIL import Image, ImageDraw
import render3 as R
from render3 import (W, H, CW, MARGIN_L, MARGIN_R, TOP, BOTTOM, GOLD, GREEN, RED, LABEL,
                     VALUE_W, DESC, COL, mask, mask_lines, colorize, gradient_fill, solid, paste,
                     wrap, title_size, cl, eo, eb, eio)

HERE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.normpath(os.path.join(HERE, '..', '..', 'assets', 'refs'))
PATH = r'%LocalAppData%\Wardogs\Saved\Config\WindowsClient'


# ---------------------------------------------------------------- утилиты слоёв
def to_layer(im):
    a = np.asarray(im, np.float32)
    return a[..., :3].copy(), a[..., 3].copy() / 255.0


def rrect(w, h, radius, fill=None, outline=None, ow=2, S=2):
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=radius * S,
                                         fill=fill, outline=outline, width=ow * S)
    return to_layer(im.resize((w, h), Image.LANCZOS))


def text_layer(txt, size, weight=600, color=(220, 226, 234), tracking=0.3, name='Montserrat'):
    return colorize(mask(txt, size, weight, tracking, name=name), color)


def word_layers(words, size, weight, color, pitch, tracking=-2.0, gap=0.32):
    """Слова -> отдельные слои + ширины (для кинетического появления по слову)."""
    out = []
    for w in words:
        rgb, a = text_layer(w, size, weight, color, tracking)
        out.append((rgb, a))
    return out


def row_items(rows, pitch, lsize, vsize, y0, t0, stagger=0.22, cw=CW):
    """Строки «лейбл -> значение» + разделители (кегль автоподгоняется)."""
    k = 1.0
    for (lab, val, _cc) in rows:
        lw = mask(lab, max(18, int(lsize)), 600, 0.6).width
        vw = mask(val, max(18, int(vsize)), 800, 0.2).width
        if lw + vw > cw - 40:
            k = min(k, (cw - 40) / (lw + vw))
    lsize = max(18, int(lsize * k))
    vsize = max(18, int(vsize * k))
    items = []
    ry = y0
    for i, (lab, val, cc) in enumerate(rows):
        rgb = np.zeros((pitch, cw, 3), np.float32)
        a = np.zeros((pitch, cw), np.float32)
        lm = mask(lab, lsize, 600, 0.6)
        lrgb, la = colorize(lm, LABEL)
        vm = mask(val, vsize, 800, 0.2)
        vrgb, va = colorize(vm, COL[cc])
        y = max(0, (pitch - lm.height) // 2 - 4)
        paste(rgb, a, lrgb, la, 0, y)
        paste(rgb, a, vrgb, va, cw - vm.width, y)
        items.append(dict(kind='fade_slide', rgb=rgb, a=a, x=MARGIN_L, y=ry, dx=-38,
                          t0=t0 + i * stagger, dur=0.24, sfx='tick.wav'))
        drgb, da = solid(cw, 2, (34, 35, 38), 255)
        items.append(dict(kind='divider', rgb=drgb, a=da, x=MARGIN_L, y=ry + pitch - 2,
                          t0=t0 + i * stagger + 0.10, dur=0.20))
        ry += pitch
    return items, ry


def chip_item(text, color, x, y, t0, dur=0.30, kind='zoomfade', dx=0, dy=18, sfx='pop.wav'):
    rgb, a = R.build_chip(text, color)
    return dict(kind=kind, rgb=rgb, a=a, x=x, y=y, dx=dx, dy=dy, t0=t0, dur=dur, sfx=sfx)


def header_items(klabel, kcolor, title, t0=0.06, title_color_bar=GOLD):
    """Чип шага + заголовок (wipe) + акцентная черта (grow)."""
    items = []
    c_rgb, c_a = R.build_chip(klabel, kcolor)
    items.append(dict(kind='zoomfade', rgb=c_rgb, a=c_a, x=MARGIN_L, y=TOP, dx=-40, dy=0,
                      t0=t0, dur=0.30, sfx='pop.wav'))
    y = TOP + c_rgb.shape[0] + 46
    ts = title_size(title, CW - 46)
    tp = int(ts * 1.06)
    t_rgb, t_a = R.build_title([title], ts, tp, 'left', None)
    items.append(dict(kind='wipe', rgb=t_rgb, a=t_a, x=MARGIN_L + 46, y=y, soft=110,
                      t0=t0 + 0.10, dur=0.44, sfx='whoosh.wav'))
    b_rgb, b_a = solid(9, tp - 26, title_color_bar, 255)
    items.append(dict(kind='grow', rgb=b_rgb, a=b_a, x=MARGIN_L, y=y + 10,
                      t0=t0 + 0.15, dur=0.40))
    return items, y + tp + 26


# ---------------------------------------------------------------- моки окон
def win_frame(w, h, title, radius=14, title_h=56, dots=True):
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


def window_shadow(w, h, off=14, blur=16, alpha=0.55):
    rgb = np.zeros((h + off * 2, w + off * 2, 3), np.float32)
    a = np.zeros((h + off * 2, w + off * 2), np.float32)
    sr, sa = solid(w, h, (0, 0, 0), 255)
    paste(rgb, a, sr, sa, off, off + 6)
    a = R.box_blur(a, blur) * alpha
    return rgb, a


def run_dialog():
    """Окно «Выполнить» с печатающимся путём. Возвращает слой, слой-тиень и позиции."""
    w, h = CW, 352
    rgb, a = win_frame(w, h, 'Выполнить')
    sh_rgb, sh_a = window_shadow(w, h)
    l_rgb, l_a = text_layer('Введите путь к папке конфигов:', 28, 600, (146, 154, 166), 0.2)
    paste(rgb, a, l_rgb, l_a, 44, 92)
    fx, fy, fw, fh = 44, 148, w - 88, 86
    fr, fa = rrect(fw, fh, 10, fill=(14, 15, 18, 255), outline=(70, 74, 83, 255), ow=2)
    paste(rgb, a, fr, fa, fx, fy)
    # фокус-рамка (Win11-акцент, золотая)
    foc, foc_a = rrect(fw + 6, fh + 6, 12, outline=GOLD + (140,), ow=2)
    paste(rgb, a, foc, foc_a, fx - 3, fy - 3)
    pm = mask(PATH, 24, 500, 0.0, name='JetBrainsMono')
    pr, pa = colorize(pm, (232, 237, 244))
    cell = pm.width / len(PATH)
    path_dx, path_dy = fx + 20, fy + (fh - pm.height) // 2
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
    return (rgb, a), (sh_rgb, sh_a), (pr, pa), (path_dx, path_dy), cell, (bx, by, bw, bh)


def notepad(highlight=0.0):
    w, h = CW, 486
    rgb, a = win_frame(w, h, 'GameUserSettings.ini — Блокнот')
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
    search_dx, search_dy = sx + 50, sy + (sh - sm.height) // 2
    # тело редактора
    bx, by = 30, 124
    bw, bh = w - 60, h - 124 - 22
    b_rgb, b_a = rrect(bw, bh, 8, fill=(17, 18, 21, 255), outline=(52, 55, 62, 255), ow=2)
    paste(rgb, a, b_rgb, b_a, bx, by)
    # «текст» полосами (синтаксис: параметры серые, значения золотистые)
    rows_txt = [('sg.AntiAliasingQuality', '3', 430), ('sg.ViewDistanceQuality', '3', 620),
                ('sg.TextureQuality', '3', 520), ('sg.EffectsQuality', '2', 560),
                ('sg.PostProcessQuality', '2', 470)]
    for i, (wd, _v, _w) in enumerate(rows_txt):
        seg = solid(min(_w, bw - 140), 13, (110, 116, 126), 105)
        paste(rgb, a, seg[0], seg[1], bx + 26, by + 26 + i * 40)
    # целевая строка (крупнее, с «=0»)
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
    # счётчик совпадений в строке поиска (справа)
    cnt = mask('1/1', 20, 600, 0.5, name='JetBrainsMono')
    cr, ca = colorize(cnt, (120, 200, 140))
    paste(rgb, a, cr, ca, sx + sw - cnt.width - 16, sy + (sh - cnt.height) // 2)
    return (rgb, a), (sr, sa), (search_dx, search_dy), cell


def code_block():
    w, h = CW, 156
    rgb, a = rrect(w, h, 12, fill=(18, 19, 23, 255), outline=(66, 70, 79, 255), ow=2)
    pref = mask('sg.ShadowQuality=', 44, 500, 0.0, name='JetBrainsMono')
    pr, pa = colorize(pref, (214, 220, 228))
    px, py = 40, (h - pref.height) // 2
    paste(rgb, a, pr, pa, px, py)
    vx = px + pref.width + 4
    z_rgb, z_a = colorize(mask('0', 62, 700, 0.0, name='JetBrainsMono'), RED)
    f_rgb, f_a = colorize(mask('4', 62, 700, 0.0, name='JetBrainsMono'), GREEN)
    return (rgb, a), (z_rgb, z_a), (f_rgb, f_a), (vx, py - 8), (px, py)


def toggle_pair():
    """Два состояния переключателя «ТЕНИ» + позиция ползунка."""
    def one(state):
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
        k_rgb, _ = solid(kn, kn, GOLD if on else (116, 122, 132), 255)
        km = Image.new('L', (kn, kn), 0)
        ImageDraw.Draw(km).ellipse([0, 0, kn - 1, kn - 1], fill=255)
        k_a = np.asarray(km, np.float32) / 255.0
        paste(rgb, a, k_rgb, k_a, kx, (h - kn) // 2)
        lab = 'ТЕНИ:  ВКЛ' if on else 'ТЕНИ:  ВЫКЛ'
        color = GOLD if on else (150, 157, 168)
        l_rgb, l_a = text_layer(lab, 36, 700, color, 0.5)
        paste(rgb, a, l_rgb, l_a, pw + 28, (h - l_rgb.shape[0]) // 2)
        return (rgb, a), kx
    on_l, kx_on = one('on')
    off_l, kx_off = one('off')
    # слой ползунка отдельно (едет при анимации)
    kn = 56
    k_gray_rgb, _ = solid(kn, kn, (150, 157, 168), 255)
    km = Image.new('L', (kn, kn), 0)
    ImageDraw.Draw(km).ellipse([0, 0, kn - 1, kn - 1], fill=255)
    k_a = np.asarray(km, np.float32) / 255.0
    k_gold_rgb, _ = solid(kn, kn, GOLD, 255)
    return on_l, off_l, (k_gold_rgb, k_a), (k_gray_rgb, k_a), kx_on, kx_off, kn


# ---------------------------------------------------------------- игровые панели
def scrim_layer(w, h, top_frac=0.0, amax=0.9, exp=0.75):
    yy = np.arange(h, dtype=np.float32)[:, None] / max(1.0, h - 1)
    a = np.clip((yy - top_frac) / (1 - top_frac), 0, 1.0) ** exp * amax
    rgb = np.zeros((h, w, 3), np.float32)
    return rgb, np.repeat(a, w, axis=1)


def tag_chip(label, col):
    lm = mask(label, 30, 800, 2.5)
    l_rgb, l_a = colorize(lm, col)
    pw, ph = lm.width + 44, lm.height + 26
    rgb, a = solid(pw, ph, (10, 10, 12), 208)
    bd_rgb, bd_a = rrect(pw, ph, 8, outline=col + (215,), ow=2)
    paste(rgb, a, bd_rgb, bd_a, 0, 0)
    paste(rgb, a, l_rgb, l_a, 22, 12)
    return rgb, a


# ---------------------------------------------------------------- СЦЕНА 1: ХУК
def scene_hook(G):
    """Хук: «ТЕБЯ УБИЛИ?» (с тенями) -> вспышка -> «ВИДНО ВСЕХ» (без теней) -> «ТЕНИ В НОЛЬ"."""
    items = []
    PW, PH = G['pw'], G['ph']
    PY = 268
    kb = dict(s0=1.0, s1=1.10, dur=7.1, fx0=0.5, fx1=0.485, fy0=0.5, fy1=0.49)

    # --- панель «с тенями» + прицел dim по центру (пусто — цели нет)
    items.append(dict(kind='game', which='with', x=MARGIN_L, y=PY, t0=0.05, dur=0.42,
                      kb=kb, sfx='whoosh.wav'))
    items.append(dict(kind='crosshair', layer='cross_dim', x=MARGIN_L, y=PY,
                      dx0=0, dy0=0, dx1=0, dy1=0, mv_t0=99, mv_dur=0.1, t0=0.2, dur=0.3))
    # чип «С ТЕНЯМИ»
    t1 = tag_chip('С ТЕНЯМИ', RED)
    items.append(dict(kind='fade_slide', rgb=t1[0], a=t1[1], x=MARGIN_L + 16, y=PY + 16,
                      dy=-10, t0=0.30, dur=0.25, sfx='tick.wav'))
    # затемнение низа панели + надпись «ТЕБЯ УБИЛИ?» (красная, по слову)
    sc_rgb, sc_a = scrim_layer(PW, 200, amax=0.92, exp=0.72)
    items.append(dict(kind='fade_slide', rgb=sc_rgb, a=sc_a, x=MARGIN_L, y=PY + PH - 200,
                      dy=12, t0=0.34, dur=0.28))
    q1 = mask('ТЕБЯ УБИЛИ?', 64, 900, -1.5)
    q1_rgb, q1_a = colorize(q1, (248, 235, 235))
    items.append(dict(kind='zoomfade', rgb=q1_rgb, a=q1_a, x=(W - q1.width) // 2,
                      y=PY + PH - q1.height - 30, dy=16, t0=0.44, dur=0.40,
                      glow=(RED, 120, 0.10), sfx='pop.wav'))

    # --- вспышка и смена на «без теней» (t=1.30)
    items.append(dict(kind='flash', color=(255, 214, 120), t0=1.30, dur=0.14, peak=0.55))
    items.append(dict(kind='shake', t0=1.30, dur=0.18, amp=3.0))
    items.append(dict(kind='game', which='without', x=MARGIN_L, y=PY, t0=1.32, dur=0.30,
                      wipe_in=True, kb=kb, sfx='shimmer.wav'))
    # прицел едет к фигуре и фиксируется (золотой)
    sxp, syp = G['soldier_px']
    items.append(dict(kind='crosshair', layer='cross_bright', x=MARGIN_L, y=PY,
                      dx0=0, dy0=0, dx1=sxp - PW // 2, dy1=syp - PH // 2,
                      mv_t0=1.36, mv_dur=0.55, t0=1.34, dur=0.3))
    items.append(dict(kind='crosshair', layer='cross_gold', x=MARGIN_L, y=PY,
                      dx0=sxp - PW // 2, dy0=syp - PH // 2, dx1=sxp - PW // 2, dy1=syp - PH // 2,
                      mv_t0=99, mv_dur=0.1, t0=1.94, dur=0.22, pulse=True, sfx='lock.wav'))
    t2 = tag_chip('БЕЗ ТЕНЕЙ', GREEN)
    items.append(dict(kind='fade_slide', rgb=t2[0], a=t2[1], x=MARGIN_L + 16, y=PY + 16,
                      dy=-10, t0=1.44, dur=0.25, sfx='tick.wav'))
    # надпись меняется на «ВИДНО ВСЕХ»
    q2 = mask('ВИДНО ВСЕХ', 64, 900, -1.5)
    q2_rgb, q2_a = colorize(q2, (225, 255, 228))
    items.append(dict(kind='fade_slide', rgb=q2_rgb, a=q2_a, x=(W - q2.width) // 2,
                      y=PY + PH - q2.height - 30, dy=0, t0=1.72, dur=0.30,
                      fade_out=None, sfx='shimmer.wav', glow=(GREEN, 130, 0.12)))
    items.append(dict(kind='fade_slide', rgb=q1_rgb, a=q1_a, x=(W - q1.width) // 2,
                      y=PY + PH - q1.height - 30, dy=0, t0=0.44, dur=0.01,
                      fade_out=(1.70, 0.16)))

    # --- заголовок и оффер под панелью
    y = PY + PH + 46
    ts = title_size('ТЕНИ В НОЛЬ', W - 260)
    tp = int(ts * 1.06)
    t_rgb, t_a = R.build_title(['ТЕНИ В НОЛЬ'], ts, tp, 'center', W - 200)
    items.append(dict(kind='wipe', rgb=t_rgb, a=t_a, x=100, y=y, soft=200, t0=2.24, dur=0.46,
                      glow=(GOLD, 150, 0.06), sfx='whoosh.wav'))
    y += t_rgb.shape[0] + 40
    d_rgb, d_a = gradient_fill(mask_lines_wrap(['Одна цифра в конфиге — видно всех, даже в тумане'],
                                              42, 600, W - 260),
                               [(0, (146, 154, 165)), (1, (172, 180, 191))])
    items.append(dict(kind='fade_slide', rgb=d_rgb, a=d_a, x=(W - d_rgb.shape[1]) // 2, y=y,
                      dy=18, t0=2.66, dur=0.34))
    y += d_rgb.shape[0] + 40
    b_rgb, b_a = R.build_badge('2 МИНУТЫ → +КОНТРАСТ', GOLD)
    items.append(dict(kind='zoomfade', rgb=b_rgb, a=b_a, x=(W - b_rgb.shape[1]) // 2, y=y,
                      dy=20, t0=3.06, dur=0.42, sfx='pop.wav'))
    y += b_rgb.shape[0] + 34
    c_rgb, c_a = R.build_chip('STEAM · WARDOGS', GOLD)
    items.append(dict(kind='fade_slide', rgb=c_rgb, a=c_a, x=(W - c_rgb.shape[1]) // 2, y=y,
                      dy=14, t0=3.44, dur=0.30))
    return items


def mask_lines_wrap(lines, size, weight, width, pitch=None):
    out = []
    for t in lines:
        out += wrap(t, size, weight, width)
    lines = out
    ms = [mask(t, size, weight, 0.2) for t in lines]
    ascent, descent = R.fnt(size, weight).getmetrics()
    pitch = pitch or int((ascent + descent) * 1.06)
    img = Image.new('L', (width, pitch * len(ms) + 4), 0)
    for i, m in enumerate(ms):
        img.paste(m, ((width - m.width) // 2, i * pitch), m)
    return img


# ---------------------------------------------------------------- СЦЕНА 2: ШАГ 1
def scene_step1(G):
    items = []
    items.append(dict(kind='bgphoto', t0=0.0, dur=0.4, alpha=0.24))
    its, y = header_items('ШАГ 1', GOLD, 'ПУТЬ К КОНФИГУ')
    items += its
    rows, ry = row_items([('ИГРА', 'ЗАКРЫТА ПОЛНОСТЬЮ', 'g'),
                          ('WIN + R', 'ОТКРЫТЬ «ВЫПОЛНИТЬ»', 'g')], 116, 42, 44, y, 0.48)
    items += rows
    y = ry + 40
    (d_rgb, d_a), (sh_rgb, sh_a), path_l, ppos, cell, okbox = run_dialog()
    items.append(dict(kind='pop', rgb=sh_rgb, a=sh_a, x=MARGIN_L - 14, y=y - 8 + 6, dy=16,
                      t0=0.90, dur=0.42))
    items.append(dict(kind='pop', rgb=d_rgb, a=d_a, x=MARGIN_L, y=y, dy=16, t0=0.95, dur=0.42,
                      sfx='pop.wav'))
    items.append(dict(kind='type', rgb=path_l[0], a=path_l[1], x=MARGIN_L + ppos[0],
                      y=y + ppos[1], t0=1.30, dur=1.9, soft=14))
    items.append(dict(kind='cursor', rgb=solid(4, 42, GOLD, 255)[0],
                      a=solid(4, 42, GOLD, 255)[1], x=0, y=0, t0=1.30, dur=1.9,
                      base_x=MARGIN_L + ppos[0], base_y=y + ppos[1] - 4, cell=cell, nchars=len(PATH)))
    ob = solid(okbox[2] + 8, okbox[3] + 8, GOLD, 90)
    items.append(dict(kind='blink', rgb=ob[0], a=ob[1], x=MARGIN_L + okbox[0] - 4,
                      y=y + okbox[1] - 4, t0=3.05, dur=0.9, period=0.42))
    y += d_rgb.shape[0] + 30
    n_rgb, n_a = R.build_chip('ENTER', GREEN)
    items.append(dict(kind='zoomfade', rgb=n_rgb, a=n_a, x=MARGIN_L, y=y, dy=14, t0=3.10,
                      dur=0.34, sfx='pop.wav'))
    cap_rgb, cap_a = text_layer('после вставки пути — открыть папку', 28, 600, (138, 146, 158), 0.4)
    items.append(dict(kind='fade_slide', rgb=cap_rgb, a=cap_a, x=MARGIN_L + n_rgb.shape[1] + 22,
                      y=y + 12, dx=-16, t0=3.22, dur=0.30))
    return items


# ---------------------------------------------------------------- СЦЕНА 3: ШАГ 2
def scene_step2(G):
    items = []
    items.append(dict(kind='bgphoto', t0=0.0, dur=0.4, alpha=0.22))
    its, y = header_items('ШАГ 2', GOLD, 'НАЙДИ ПАРАМЕТР')
    items += its
    rows, ry = row_items([('ОТКРЫТЬ', 'БЛОКНОТОМ', 'o'),
                          ('CTRL + F', 'ПОИСК ПО ФАЙЛУ', 'g')], 104, 40, 42, y, 0.48)
    items += rows
    f_rgb, f_a = R.build_chip('НАЙДЕНО: 1', GREEN)
    items.append(dict(kind='zoomfade', rgb=f_rgb, a=f_a, x=MARGIN_L + CW - f_rgb.shape[1],
                      y=ry + 30, dy=12, t0=2.78, dur=0.36, sfx='pop.wav'))
    y = ry + 100
    (np_rgb, np_a), search_l, spos, scell = notepad()
    np_hl = notepad(highlight=1.0)
    sh_rgb, sh_a = window_shadow(CW, 486)
    items.append(dict(kind='pop', rgb=sh_rgb, a=sh_a, x=MARGIN_L - 14, y=y - 8 + 6, dy=16,
                      t0=0.90, dur=0.42))
    items.append(dict(kind='pop', rgb=np_rgb, a=np_a, x=MARGIN_L, y=y, dy=16, t0=0.95, dur=0.42,
                      sfx='pop.wav'))
    items.append(dict(kind='type', rgb=search_l[0], a=search_l[1], x=MARGIN_L + spos[0],
                      y=y + spos[1], t0=1.30, dur=1.15, soft=14))
    items.append(dict(kind='cursor', rgb=solid(4, 36, GOLD, 255)[0],
                      a=solid(4, 36, GOLD, 255)[1], x=0, y=0, t0=1.30, dur=1.15,
                      base_x=MARGIN_L + spos[0], base_y=y + spos[1] - 4, cell=scell,
                      nchars=len('sg.ShadowQuality')))
    # подсветка найденной строки
    items.append(dict(kind='highlight', rgb=np_rgb, a=np_a, rgb2=np_hl[0][0], a2=np_hl[0][1],
                      x=MARGIN_L, y=y, t0=2.60, dur=0.5, sfx='shimmer.wav'))
    return items


# ---------------------------------------------------------------- СЦЕНА 4: ШАГ 3
def scene_step3(G):
    items = []
    items.append(dict(kind='bgphoto', t0=0.0, dur=0.4, alpha=0.22))
    its, y = header_items('ШАГ 3', GOLD, 'ПОСТАВЬ 4')
    items += its
    (cb_rgb, cb_a), zero, four, vpos, ppos = code_block()
    items.append(dict(kind='wipe', rgb=cb_rgb, a=cb_a, x=MARGIN_L, y=y, soft=240, t0=0.55,
                      dur=0.40, sfx='whoosh.wav'))
    items.append(dict(kind='fade_slide', rgb=zero[0], a=zero[1], x=MARGIN_L + vpos[0],
                      y=y + vpos[1], dy=0, t0=0.80, dur=0.25, fade_out=(1.38, 0.14)))
    # смена 0 -> 4: вспышка + зелёный «4» + галочка
    items.append(dict(kind='flash', color=(120, 255, 160), t0=1.56, dur=0.16, peak=0.35,
                      region=(MARGIN_L + vpos[0] - 30, y + vpos[1] - 20, 160, 110)))
    items.append(dict(kind='zoomfade', rgb=four[0], a=four[1], x=MARGIN_L + vpos[0],
                      y=y + vpos[1], dy=-12, t0=1.56, dur=0.34, sfx='success.wav',
                      glow=(GREEN, 150, 0.16)))
    ck = R.check_mark(58)
    items.append(dict(kind='zoomfade', rgb=ck[0], a=ck[1], x=MARGIN_L + vpos[0] + 66,
                      y=y + vpos[1] + 8, dy=-8, t0=1.94, dur=0.40, sfx='pop.wav',
                      glow=(GREEN, 90, 0.14)))
    y += cb_rgb.shape[0] + 34
    rows, ry = row_items([('СОХРАНИТЬ', 'CTRL + S', 'o'),
                          ('ТОЛЬКО ДЛЯ ЧТЕНИЯ', 'ВКЛЮЧИТЬ', 'g'),
                          ('МЕНЮ НАСТРОЕК', 'НЕ ТРОГАТЬ', 'r')], 98, 39, 41, y, 2.30)
    items += rows
    y = ry + 34
    n_rgb, n_a = R.build_note('ВАЖНО',
                              'Любое изменение в меню настроек сбросит тени — просто повтори шаг с конфигом.',
                              RED, CW)
    items.append(dict(kind='boxdraw', rgb=n_rgb, a=n_a, x=MARGIN_L, y=y, t0=3.55, dur=0.45,
                      sfx='whoosh_down.wav'))
    y += n_rgb.shape[0] + 36
    on_l, off_l, knob_g, knob_s, kx_on, kx_off, kn = toggle_pair()
    items.append(dict(kind='fade_slide', rgb=on_l[0], a=on_l[1], x=MARGIN_L, y=y, dy=16,
                      t0=4.65, dur=0.30, fade_out=(5.26, 0.14), sfx='shimmer.wav'))
    items.append(dict(kind='fade_slide', rgb=off_l[0], a=off_l[1], x=MARGIN_L, y=y, dy=-10,
                      t0=5.42, dur=0.30, sfx='whoosh_down.wav'))
    # ползунок едет справа налево, цвет меняется gold -> gray
    items.append(dict(kind='knob', rgb=knob_g[0], a=knob_g[1], rgb2=knob_s[0], a2=knob_s[1],
                      x=MARGIN_L + kx_on, y=y + (96 - kn) // 2,
                      x0=MARGIN_L + kx_on, x1=MARGIN_L + kx_off, t0=4.90, dur=0.55,
                      tstart=4.90, tend=5.45, sfx='tick.wav'))
    return items


# ---------------------------------------------------------------- СЦЕНА 5: РЕЗУЛЬТАТ
def scene_result(G):
    items = []
    PW, PH = G['pw'], G['ph']
    its, y = header_items('РЕЗУЛЬТАТ', GREEN, 'ВИДНО ВСЕХ', title_color_bar=GREEN)
    items += its
    kb = dict(s0=1.02, s1=1.12, dur=6.7, fx0=0.5, fx1=0.49, fy0=0.5, fy1=0.495)
    y += 6
    items.append(dict(kind='game', which='with', x=MARGIN_L, y=y, t0=0.62, dur=0.42,
                      kb=kb, sfx='pop.wav'))
    # шторка открывает «без теней»
    items.append(dict(kind='game', which='without', x=MARGIN_L, y=y, t0=1.70, dur=1.35,
                      wipe_in=True, kb=kb, sfx='whoosh.wav'))
    items.append(dict(kind='compdivider', x=MARGIN_L, y=y, w=PW, h=PH, t0=1.70, dur=1.35))
    tag_a = tag_chip('С ТЕНЯМИ', RED)
    tag_b = tag_chip('БЕЗ ТЕНЕЙ', GREEN)
    items.append(dict(kind='fade_slide', rgb=tag_a[0], a=tag_a[1],
                      x=MARGIN_L + PW - tag_a[0].shape[1] - 16, y=y + 16, dy=-12, t0=1.15,
                      dur=0.3, fade_out=(2.45, 0.45), sfx='tick.wav'))
    items.append(dict(kind='fade_slide', rgb=tag_b[0], a=tag_b[1], x=MARGIN_L + 16, y=y + 16,
                      dy=-12, t0=1.95, dur=0.3, sfx='tick.wav'))
    # прицел: сначала dim по центру, после шторки — золотой на фигуре
    sxp, syp = G['soldier_px']
    items.append(dict(kind='crosshair', layer='cross_dim', x=MARGIN_L, y=y,
                      dx0=0, dy0=0, dx1=sxp - PW // 2, dy1=syp - PH // 2,
                      mv_t0=1.75, mv_dur=1.2, t0=0.75, dur=0.3))
    items.append(dict(kind='crosshair', layer='cross_gold', x=MARGIN_L, y=y,
                      dx0=sxp - PW // 2, dy0=syp - PH // 2, dx1=sxp - PW // 2, dy1=syp - PH // 2,
                      mv_t0=99, mv_dur=0.1, t0=2.95, dur=0.22, pulse=True, sfx='lock.wav'))
    y += PH + 26
    rows, ry = row_items([('ТУМАН / ЗАКАТ', 'МОДЕЛИ НЕ ПРЯЧУТСЯ', 'g'),
                          ('КОНТРАСТ', 'ВЫШЕ', 'g')], 104, 41, 43, y, 3.20)
    items += rows
    y = ry + 26
    bx_rgb, bx_a = R.build_box_result('БЕЗ ТЕНЕЙ', 'МОДЕЛИ ВИДНО СРАЗУ', GREEN, CW, bh=150)
    items.append(dict(kind='zoomfade', rgb=bx_rgb, a=bx_a, x=MARGIN_L, y=y, dy=18, t0=4.05,
                      dur=0.42, glow=(GREEN, 110, 0.08), sfx='pop.wav'))
    cr_rgb, cr_a = text_layer('Эффект в игре · по гайду Bryce, Steam Community', 24, 600,
                              (96, 103, 114), 0.4)
    items.append(dict(kind='fade_slide', rgb=cr_rgb, a=cr_a, x=MARGIN_L,
                      y=y + bx_rgb.shape[0] + 16, dy=14, t0=4.45, dur=0.34))
    return items


# ---------------------------------------------------------------- СЦЕНА 6: CTA
def scene_cta(G):
    items = []
    f_rgb, f_a = R.flame(205)
    items.append(dict(kind='zoomfade', rgb=f_rgb, a=f_a, x=(W - f_rgb.shape[1]) // 2, y=400,
                      t0=0.05, dur=0.5, glow=((255, 140, 30), 190, 0.10), sfx='whoosh.wav'))
    y = 400 + f_rgb.shape[0] + 44
    ts = title_size('СОХРАНИ', W - 260)
    tp = int(ts * 1.06)
    t_rgb, t_a = R.build_title(['СОХРАНИ', 'И ПОДПИШИСЬ'], ts, tp, 'center', W - 200)
    items.append(dict(kind='wipe', rgb=t_rgb, a=t_a, x=100, y=y, soft=200, t0=0.42, dur=0.46,
                      glow=(GOLD, 140, 0.05), sfx='whoosh.wav'))
    y += t_rgb.shape[0] + 40
    d_rgb, d_a = gradient_fill(mask_lines_wrap(['Чтобы не потерять настройки'], 45, 600, W - 260),
                               [(0, (146, 154, 165)), (1, (172, 180, 191))])
    items.append(dict(kind='fade_slide', rgb=d_rgb, a=d_a, x=(W - d_rgb.shape[1]) // 2, y=y,
                      dy=18, t0=0.82, dur=0.34))
    y += d_rgb.shape[0] + 50
    m = mask('WARDOGS', 50, 900, 8)
    br_rgb, br_a = colorize(m, GOLD)
    items.append(dict(kind='fade_slide', rgb=br_rgb, a=br_a, x=(W - m.width) // 2, y=y, dy=20,
                      t0=1.42, dur=0.34, sfx='shimmer.wav'))
    ln_rgb, ln_a = solid(W - 380, 2, (52, 54, 58), 255)
    items.append(dict(kind='wipe', rgb=ln_rgb, a=ln_a, x=190, y=y - 40, soft=200, t0=1.34, dur=0.34))
    items.append(dict(kind='wipe', rgb=ln_rgb, a=ln_a, x=190, y=y + m.height + 30, soft=200,
                      t0=1.34, dur=0.34))
    y += m.height + 56
    s_rgb, s_a = text_layer('ЛУЧШИЕ НАСТРОЙКИ ГРАФИКИ', 29, 700, (110, 117, 128), 7.0)
    items.append(dict(kind='fade_slide', rgb=s_rgb, a=s_a, x=(W - s_rgb.shape[1]) // 2, y=y,
                      dy=16, t0=1.74, dur=0.34))
    y += s_rgb.shape[0] + 44
    # пульсирующая CTA-кнопка
    btn_rgb, btn_a = R.build_badge('ПОДПИСАТЬСЯ →', GREEN, size=40, padx=46, pady=22)
    items.append(dict(kind='zoomfade', rgb=btn_rgb, a=btn_a, x=(W - btn_rgb.shape[1]) // 2, y=y,
                      dy=18, t0=2.20, dur=0.44, sfx='pop.wav'))
    items.append(dict(kind='pulse', rgb=btn_rgb, a=btn_a, x=(W - btn_rgb.shape[1]) // 2, y=y,
                      t0=2.7, dur=3.6, glow=(GREEN, 120, 0.14)))
    c_rgb, c_a = R.build_chip('ЕЩЁ ГАЙДЫ — СКОРО', GOLD)
    items.append(dict(kind='fade_slide', rgb=c_rgb, a=c_a, x=(W - c_rgb.shape[1]) // 2,
                      y=y + btn_rgb.shape[0] + 30, dy=14, t0=3.20, dur=0.32))
    items.append(dict(kind='fadeout', t0=6.45, dur=0.42))
    return items


SCENE_FNS = [scene_hook, scene_step1, scene_step2, scene_step3, scene_result, scene_cta]
SCENE_DURS = [7.125, 8.354, 6.718, 9.145, 6.749, 6.831]
TOTAL = 44.922
