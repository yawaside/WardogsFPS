# -*- coding: utf-8 -*-
"""
База рендера видео №3 (улучшенный ремейк гайда WARDOGS «тени в ноль»).
1080x1920 @ 30fps. Улучшения относительно v2:
 - supersampled-текст (SS=4) с кэшем слоёв
 - кинетические анимации: wordpop (масштаб+overshoot), zoomfade, flash, shake
 - процедурный bloom/тени/зерно, сегментированный прогресс-бар
 - кроссфейды между сценами, Ken Burns на игровых панелях
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30

GOLD = (250, 172, 20)
GOLD_HI = (255, 214, 120)
GREEN = (78, 236, 96)
RED = (248, 62, 62)
LABEL = (188, 195, 204)
VALUE_W = (232, 236, 242)
DESC = (150, 159, 170)
FOOT = (78, 85, 96)
DIV = (34, 35, 38)
BG0, BG1 = (15, 14, 16), (5, 5, 6)

COL = {'o': GOLD, 'g': GREEN, 'r': RED, 'w': VALUE_W}
HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.normpath(os.path.join(HERE, '..', '..', 'assets', 'fonts'))

MARGIN_L, MARGIN_R = 104, 946          # безопасная зона под UI Shorts/TikTok
CW = MARGIN_R - MARGIN_L               # 842
TOP, BOTTOM = 250, 1580
PROGRESS_Y = 196

_fcache = {}
def fnt(size, weight=700, name='Montserrat'):
    key = (name, size, weight)
    if key not in _fcache:
        if name == 'Montserrat':
            f = ImageFont.truetype(os.path.join(FONTS, 'Montserrat.ttf'), size)
            try:
                f.set_variation_by_axes([weight])
            except Exception:
                pass
        else:
            wmap = {500: 'Regular', 600: 'Medium', 700: 'Bold', 800: 'ExtraBold'}
            w = wmap.get(weight, 'Regular')
            f = ImageFont.truetype(os.path.join(FONTS, f'JetBrainsMono-{w}.ttf'), size)
        _fcache[key] = f
    return _fcache[key]


# ---------------------------------------------------------------- text (SS=4)
_mcache = {}
def mask(text, size, weight=700, tracking=0.0, name='Montserrat', ss=4):
    """Ч/б маска строки с суперсэмплингом. Кэш по параметрам."""
    key = (text, size, weight, tracking, name, ss)
    if key in _mcache:
        return _mcache[key]
    f = fnt(size * ss, weight, name)
    ascent, descent = f.getmetrics()
    chars = list(text)
    widths = [f.getlength(c) for c in chars]
    total = sum(widths) + tracking * ss * max(0, len(chars) - 1)
    img = Image.new('L', (max(2, int(math.ceil(total)) + 8 * ss), (ascent + descent + 4 * ss)), 0)
    d = ImageDraw.Draw(img)
    x = 0.0
    for c, wd in zip(chars, widths):
        d.text((x, 2 * ss), c, font=f, fill=255)
        x += wd + tracking * ss
    img = img.resize((max(2, img.width // ss), max(2, img.height // ss)), Image.LANCZOS)
    _mcache[key] = img
    return img


def mask_lines(lines, size, weight=700, tracking=0.0, pitch=None, align='left', width=None, name='Montserrat'):
    ms = [mask(t, size, weight, tracking, name) for t in lines]
    ascent, descent = fnt(size, weight, name).getmetrics()
    pitch = pitch or int((ascent + descent) * 1.06)
    tw = max(m.width for m in ms)
    width = width or tw
    img = Image.new('L', (width, pitch * len(ms) + 4), 0)
    for i, m in enumerate(ms):
        if align == 'center':
            x = (width - m.width) // 2
        elif align == 'right':
            x = width - m.width
        else:
            x = 0
        img.paste(m, (max(0, x), i * pitch), m)
    return img


def colorize(m, color):
    rgb = np.zeros((m.height, m.width, 3), np.float32)
    rgb[..., 0], rgb[..., 1], rgb[..., 2] = color
    return rgb, (np.asarray(m, np.float32) / 255.0)


def gradient_fill(m, stops):
    a = np.asarray(m, np.float32) / 255.0
    h, w = a.shape
    ys = np.linspace(0, 1, h)[:, None]
    rgb = np.zeros((h, w, 3), np.float32)
    for i in range(len(stops) - 1):
        p0, c0 = stops[i]; p1, c1 = stops[i + 1]
        seg = (ys >= p0) & (ys <= p1)
        t = np.clip((ys - p0) / max(1e-6, (p1 - p0)), 0, 1)
        for ch in range(3):
            rgb[..., ch] = np.where(seg, c0[ch] + (c1[ch] - c0[ch]) * t, rgb[..., ch])
    return rgb, a


def solid(w, h, color, alpha=255):
    rgb = np.zeros((h, w, 3), np.float32)
    rgb[..., 0], rgb[..., 1], rgb[..., 2] = color
    return rgb, np.full((h, w), alpha / 255.0, np.float32)


def paste(canvas_rgb, canvas_a, rgb, a, x, y):
    x0, y0 = max(0, x), max(0, y)
    h, w = rgb.shape[:2]
    sx, sy = x0 - x, y0 - y
    x1, y1 = min(canvas_a.shape[1], x0 + w - sx), min(canvas_a.shape[0], y0 + h - sy)
    if x1 <= x0 or y1 <= y0:
        return
    sub = a[sy:sy + (y1 - y0), sx:sx + (x1 - x0)]
    canvas_a[y0:y1, x0:x1] += sub
    sub3 = sub[..., None]
    canvas_rgb[y0:y1, x0:x1] = canvas_rgb[y0:y1, x0:x1] * (1 - sub3) + \
                                rgb[sy:sy + (y1 - y0), sx:sx + (x1 - x0)] * sub3


# ---------------------------------------------------------------- easing
def cl(t):
    return 0.0 if t < 0 else (1.0 if t > 1 else t)

def eo(t):
    """cubic out"""
    t = cl(t)
    return 1 - (1 - t) ** 3

def ei(t):
    t = cl(t)
    return t ** 3

def eb(t, s=1.45):
    """back out (overshoot)"""
    t = cl(t)
    return 1 + (s + 1) * (t - 1) ** 3 + s * (t - 1) ** 2

def eio(t):
    """ease in-out (smoothstep-ish cubic)"""
    t = cl(t)
    return t * t * (3 - 2 * t)


# ---------------------------------------------------------------- canvas ops
def blend(frame, rgb, a, x, y, alpha=1.0, wipe=None, grow=None):
    """Наложение premultiplied-ish слоя (rgb уже «прямой» цвет, a — покрытие)."""
    h, w = a.shape
    aa = a
    if wipe is not None:
        soft = int(wipe[1])
        k = wipe[0] * (w + soft)
        ramp = np.clip((k - np.arange(w)) / max(1, soft), 0, 1).astype(np.float32)
        aa = aa * ramp[None, :]
    if grow is not None:
        k = int(grow * h)
        aa = aa.copy()
        aa[k:] = 0
    if alpha != 1.0:
        aa = aa * alpha
    x0, y0 = max(0, x), max(0, y)
    sx, sy = x0 - x, y0 - y
    x1, y1 = min(W, x0 + w - sx), min(H, y0 + h - sy)
    if x1 <= x0 or y1 <= y0:
        return
    sub = aa[sy:sy + y1 - y0, sx:sx + x1 - x0][..., None]
    reg = frame[y0:y1, x0:x1]
    reg *= (1 - sub)
    reg += rgb[sy:sy + y1 - y0, sx:sx + x1 - x0] * sub


def add_glow(frame, rgb, a, x, y, k):
    h, w = a.shape
    x0, y0 = max(0, x), max(0, y)
    sx, sy = x0 - x, y0 - y
    x1, y1 = min(W, x0 + w - sx), min(H, y0 + h - sy)
    if x1 <= x0 or y1 <= y0:
        return
    sub = a[sy:sy + y1 - y0, sx:sx + x1 - x0][..., None] * k
    frame[y0:y1, x0:x1] += rgb[sy:sy + y1 - y0, sx:sx + x1 - x0] * sub


def box_blur(arr, r):
    """Separable box blur (приближение gaussian, 3 прохода). float32, 2D или 3D."""
    if r < 1:
        return arr
    for _ in range(3):
        arr = _box1d(arr, r, axis=0)
        arr = _box1d(arr, r, axis=1)
    return arr


def _box1d(arr, r, axis):
    n = arr.shape[axis]
    pad = [(0, 0)] * arr.ndim
    pad[axis] = (r, r)
    p = np.pad(arr, pad, mode='edge')
    c = np.cumsum(p, axis=axis, dtype=np.float64)
    k = 2 * r + 1
    # out[i] = mean(p[i .. i+k-1]) = (c[i+k-1] - c[i-1]) / k,  c[-1] = 0
    sl_hi = [slice(None)] * arr.ndim; sl_hi[axis] = slice(k - 1, k - 1 + n)
    hi = c[tuple(sl_hi)]
    lo_full = np.take(c, list(range(0, n - 1)), axis=axis)
    zshape = list(arr.shape); zshape[axis] = 1
    lo = np.concatenate([np.zeros(zshape, np.float64), lo_full], axis=axis)
    out = (hi - lo) / k
    return out.astype(np.float32)


def scale_layer(rgb, a, s):
    """Масштаб слоя (bilinear через PIL). s>0. Для маленьких слоёв — дёшево."""
    h, w = a.shape
    nw, nh = max(1, int(round(w * s))), max(1, int(round(h * s)))
    if nw == w and nh == h:
        return rgb, a
    im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), 'RGB').resize((nw, nh), Image.BILINEAR)
    am = Image.fromarray((a * 255).astype(np.uint8), 'L').resize((nw, nh), Image.BILINEAR)
    return np.asarray(im, np.float32), np.asarray(am, np.float32) / 255.0


def glow_sprite(r, color, power=2.0):
    S = 2
    n = r * 2 * S
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    d = np.sqrt((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / (n / 2)
    a = np.clip(1 - d, 0, 1) ** power
    rgb = np.zeros((n, n, 3), np.float32)
    rgb[..., 0], rgb[..., 1], rgb[..., 2] = color
    a = a * (a > 0.004)
    a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((r * 2, r * 2), Image.LANCZOS), np.float32) / 255
    rgb = np.asarray(Image.fromarray(rgb.astype(np.uint8)).resize((r * 2, r * 2), Image.LANCZOS), np.float32)
    return rgb, a


# ---------------------------------------------------------------- backgrounds
def radial_bg():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ty = (yy / H)[..., None]
    base = np.array(BG0, np.float32) * (1 - ty) + np.array(BG1, np.float32) * ty
    cx, cy = W * 0.42, H * 0.26
    r = np.sqrt(((xx - cx) / (W * 0.95)) ** 2 + ((yy - cy) / (H * 0.75)) ** 2)
    gl = np.clip(1 - r, 0, 1) ** 2.2
    base += gl[..., None] * np.array([26, 17, 4], np.float32)
    r2 = np.sqrt(((xx - W * 1.05) / (W * 0.9)) ** 2 + ((yy - H * 1.02) / (H * 0.8)) ** 2)
    base += (np.clip(1 - r2, 0, 1) ** 2.4)[..., None] * np.array([4, 6, 12], np.float32)
    rv = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
    vig = np.clip(1.06 - 0.34 * rv ** 2, 0.45, 1.0)
    base *= vig[..., None]
    return np.clip(base, 0, 255)


def corner_frame():
    S = 4
    im = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    inset, arm, th = 54 * S, 118 * S, 5 * S
    g = GOLD + (215,)
    def rect(x0, y0, x1, y1, fill):
        d.rectangle([min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)], fill=fill)
    for (cx0, cy0, dx, dy) in [(inset, inset, 1, 1), (W * S - inset, inset, -1, 1),
                               (inset, H * S - inset, 1, -1), (W * S - inset, H * S - inset, -1, -1)]:
        rect(cx0 - th / 2, cy0 - th / 2, cx0 + dx * arm, cy0 + th / 2, g)
        rect(cx0 - th / 2, cy0 - th / 2, cx0 + th / 2, cy0 + dy * arm, g)
    d.rectangle([inset, inset, W * S - inset, H * S - inset], outline=GOLD + (16,), width=S)
    im = im.resize((W, H), Image.LANCZOS)
    a = np.asarray(im, np.float32)
    return a[..., :3].copy(), a[..., 3].copy() / 255.0


def footer_layer(text='WARDOGS · ГАЙД ПО КОНФИГУ'):
    m = mask(text, 27, 700, tracking=9)
    return colorize(m, FOOT)


# ---------------------------------------------------------------- decor elements
def rr_layer(w, h, radius, fill=None, outline=None, ow=2, S=2):
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=radius * S,
                                         fill=fill, outline=outline, width=ow * S)
    a = np.asarray(im.resize((w, h), Image.LANCZOS), np.float32)
    return a[..., :3].copy(), a[..., 3].copy() / 255.0


def build_chip(text, color):
    m = mask(text, 31, 800, tracking=3.5)
    rgb, a = colorize(m, color)
    padx, pady, th = 26, 15, 3
    w, h = rgb.shape[1] + padx * 2, rgb.shape[0] + pady * 2
    out_rgb, out_a = solid(w, h, (0, 0, 0), 0)
    box = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle([th / 2, th / 2, w - th / 2 - 1, h - th / 2 - 1],
                                          7, outline=color + (235,), width=th)
    ba = np.asarray(box, np.float32)
    out_a += ba[..., 3] / 255.0
    out_rgb = out_rgb * (1 - (ba[..., 3:] / 255.0)) + ba[..., :3] * (ba[..., 3:] / 255.0)
    paste(out_rgb, out_a, rgb, a, padx, pady)
    return out_rgb, out_a


def build_title(lines, size, pitch, align='left', width=None, tracking=-2.0):
    m = mask_lines(lines, size, 900, tracking, pitch, align, width)
    return gradient_fill(m, [(0.0, (247, 249, 252)), (0.44, (201, 208, 216)), (1.0, (126, 133, 143))])


def build_badge(text, color, size=44, padx=38, pady=24, th=3):
    m = mask(text, size, 800, tracking=1.5)
    w, h = m.width + padx * 2, m.height + pady * 2
    rgb, a = solid(w, h, (0, 0, 0), 0)
    box = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle([th / 2, th / 2, w - th / 2 - 1, h - th / 2 - 1],
                                          8, outline=color + (240,), width=th)
    ba = np.asarray(box, np.float32); al = ba[..., 3] / 255.0
    rgb = rgb * (1 - al[..., None]) + ba[..., :3] * al[..., None]
    a += al
    grgb, ga = solid(w, h, color, 0.055)
    al2 = ga * 0.075
    rgb = rgb * (1 - al2[..., None]) + grgb * al2[..., None]
    t_rgb, t_a = colorize(m, color)
    paste(rgb, a, t_rgb, t_a, padx, pady)
    return rgb, a


def build_note(title, text, color, width=842, tsize=33, bsize=36):
    pad = 34
    body = wrap(text, bsize, 500, width - pad * 2 - 22)
    bm = mask_lines(body, bsize, 500, 0.2, int(bsize * 1.42))
    tm = mask(title, 30, 800, tracking=3) if title else None
    w = width
    h = pad + (tm.height + 20 if tm is not None else 0) + bm.height + pad
    inner_rgb, inner_a = solid(w, h, (0, 0, 0), 0)
    bar_w = 6
    brgb, ba = solid(bar_w, h - 2, color, 235)
    paste(inner_rgb, inner_a, brgb, ba, 0, 1)
    fill_rgb, fill_a = solid(w, h, (26, 18, 4) if color != RED else (30, 8, 8), 0.55)
    bg_rgb, bg_a = solid(w, h, color, 0.055)
    for (r_, a_, x_, y_) in [(fill_rgb, fill_a, 0, 0), (bg_rgb, bg_a, 0, 0)]:
        paste(inner_rgb, inner_a, r_, a_, x_, y_)
    box = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle([1, 1, w - 2, h - 2], 10, outline=color + (170,), width=2)
    ba2 = np.asarray(box, np.float32)
    al = ba2[..., 3] / 255.0
    inner_rgb = inner_rgb * (1 - al[..., None]) + ba2[..., :3] * al[..., None]
    inner_a += al
    y = pad
    if tm is not None:
        t_rgb, t_a = colorize(tm, color)
        paste(inner_rgb, inner_a, t_rgb, t_a, pad + 18, y)
        y += tm.height + 20
    bc = (214, 148, 148) if color == RED else (196, 202, 210)
    b_rgb, b_a = colorize(bm, bc)
    paste(inner_rgb, inner_a, b_rgb, b_a, pad + 18, y)
    return inner_rgb, inner_a


def build_box_result(big, small, color, width=842, bh=196):
    rgb, a = solid(width, bh, (0, 0, 0), 0)
    box = Image.new('RGBA', (width, bh), (0, 0, 0, 0))
    ImageDraw.Draw(box).rounded_rectangle([2, 2, width - 3, bh - 3], 10, outline=color + (215,), width=3)
    ba = np.asarray(box, np.float32); al = ba[..., 3] / 255.0
    rgb = rgb * (1 - al[..., None]) + ba[..., :3] * al[..., None]
    a += al
    grgb, ga = solid(width, bh, color, 0.05)
    rgb = rgb * (1 - ga[..., None] * 0.9) + grgb * (ga[..., None] * 0.9)
    bm = mask(big, 78, 900, tracking=-1.5)
    b_rgb, b_a = colorize(bm, color)
    sm = mask(small, 29, 700, tracking=5)
    s_rgb, s_a = colorize(sm, (140, 148, 158))
    th = bm.height + 16 + sm.height
    y = (bh - th) // 2
    paste(rgb, a, b_rgb, b_a, (width - bm.width) // 2, y)
    paste(rgb, a, s_rgb, s_a, (width - sm.width) // 2, y + bm.height + 16)
    return rgb, a


def wrap(text, size, weight, maxw, name='Montserrat'):
    f = fnt(size, weight, name)
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if f.getlength(t) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def title_size(text, maxw, weight=900):
    s = 100
    while s > 54:
        if mask(text, s, weight, -2.0).width <= maxw:
            return s
        s -= 2
    return s


def check_mark(d=52, color=GREEN):
    S = 3
    im = Image.new('RGBA', (d * S, d * S), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    dd.ellipse([2, 2, d * S - 3, d * S - 3], outline=color + (235,), width=4 * S)
    dd.line([d * S * 0.28, d * S * 0.52, d * S * 0.44, d * S * 0.70], fill=color + (255,), width=5 * S)
    dd.line([d * S * 0.44, d * S * 0.70, d * S * 0.74, d * S * 0.30], fill=color + (255,), width=5 * S)
    a = np.asarray(im.resize((d, d), Image.LANCZOS), np.float32)
    return a[..., :3].copy(), a[..., 3].copy() / 255.0


def cross_mark(d=52, color=RED):
    S = 3
    im = Image.new('RGBA', (d * S, d * S), (0, 0, 0, 0))
    dd = ImageDraw.Draw(im)
    dd.ellipse([2, 2, d * S - 3, d * S - 3], outline=color + (235,), width=4 * S)
    dd.line([d * S * 0.32, d * S * 0.32, d * S * 0.68, d * S * 0.68], fill=color + (255,), width=5 * S)
    dd.line([d * S * 0.68, d * S * 0.32, d * S * 0.32, d * S * 0.68], fill=color + (255,), width=5 * S)
    a = np.asarray(im.resize((d, d), Image.LANCZOS), np.float32)
    return a[..., :3].copy(), a[..., 3].copy() / 255.0


def flame(height=210):
    S = 4
    Wf, Hf = int(height * 0.78) * S, int(height * S)

    def poly_mask(cx, top, bot, width_k, skew, p_exp=1.02):
        n = 220
        left, right = [], []
        for i in range(n + 1):
            t = i / n
            hw = width_k * (math.sin(math.pi * (t ** p_exp)) ** 0.72) * (1 - 0.05 * t)
            hw *= (0.13 + 0.87 * min(1.0, t * 1.45)) ** 0.62
            y = top + (bot - top) * t
            xc = cx + width_k * skew * math.sin(math.pi * t * 0.85)
            left.append((xc - hw, y)); right.append((xc + hw, y))
        m = Image.new('L', (Wf, Hf), 0)
        ImageDraw.Draw(m).polygon(left + right[::-1], fill=255)
        return np.asarray(m, np.float32) / 255.0

    layers = [
        (poly_mask(Wf / 2, Hf * 0.010, Hf * 0.99, Wf * 0.40, 0.11), (243, 24, 16), (250, 112, 8), 0.72),
        (poly_mask(Wf / 2 - Wf * 0.015, Hf * 0.26, Hf * 0.966, Wf * 0.315, 0.16), (249, 132, 10), (252, 170, 18), 0.78),
        (poly_mask(Wf / 2 + Wf * 0.008, Hf * 0.48, Hf * 0.946, Wf * 0.205, 0.10), (253, 196, 36), (254, 232, 120), 0.84),
        (poly_mask(Wf / 2 + Wf * 0.014, Hf * 0.70, Hf * 0.930, Wf * 0.105, 0.06), (255, 226, 110), (255, 252, 216), 1.0),
    ]
    img = np.zeros((Hf, Wf, 4), np.float32)
    ys = np.linspace(0, 1, Hf)[:, None].astype(np.float32)
    for m, c0, c1, pw in layers:
        p = np.clip(ys, 0, 1) ** pw
        col = np.stack([c0[ch] + (c1[ch] - c0[ch]) * p[:, 0] for ch in range(3)], -1)
        ms = m[..., None]
        img[..., :3] = col[:, None, :] * ms + img[..., :3] * (1 - ms)
        img[..., 3:4] = ms + img[..., 3:4] * (1 - ms)
    out_arr = np.clip(img, 0, 255)
    out_arr[..., 3] *= 255.0
    out = Image.fromarray(out_arr.astype(np.uint8), 'RGBA').resize((Wf // S, Hf // S), Image.LANCZOS)
    a = np.asarray(out, np.float32)
    return a[..., :3].copy(), a[..., 3].copy() / 255.0


def film_grain_tile(size=128, amp=1.0):
    rng = np.random.default_rng(7)
    return ((rng.random((size, size), dtype=np.float32) - 0.5) * 2.0) * amp
