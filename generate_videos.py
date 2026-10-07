#!/usr/bin/env python3
"""
Generator for WARDOGS Config Guide YouTube Shorts / TikTok videos (1080x1920, 30 FPS).
Produces:
1. wardogs_config_1080x1920.mp4 (44.27s — 1:1 synced with original voiceover timeline, all visual bugs fixed + real game screenshots)
2. wardogs_shorts_viral_1080x1920.mp4 (33.80s — fast-cut viral Shorts edition with dead-air silence removed, 0.05s hook start, beat drop at 0s, SFX & seamless loop)
3. wardogs_otkluchenie_teney_konfig_1080x1920.mp4 (ready-to-upload copy of the viral Shorts edition as named in upload pack)
"""

import os
import sys
import math
import wave
import shutil
import subprocess
import numpy as np
from numpy.fft import rfft, irfft
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
import imageio_ffmpeg

W, H = 1080, 1920
FPS = 30

# Color palette (Dark Tactical Gold / Emerald / Crimson)
BG_TOP = (12, 11, 10)
BG_BOT = (18, 15, 12)
GOLD = (245, 176, 37)
GOLD_BRIGHT = (255, 212, 75)
GOLD_DIM = (140, 100, 28)
GREEN = (46, 232, 108)
GREEN_DIM = (22, 95, 48)
RED = (250, 76, 76)
RED_DIM = (110, 28, 32)
WHITE = (246, 248, 252)
SILVER = (192, 200, 214)
MUTED = (130, 138, 152)
CARD_BG = (22, 25, 32)
CARD_BG_DARK = (15, 18, 24)
CARD_BORDER = (62, 70, 88)

FONT_CACHE = {}


def get_font(family: str, size: int, weight: str = 'Bold') -> ImageFont.FreeTypeFont:
    key = (family, size, weight)
    if key in FONT_CACHE:
        return FONT_CACHE[key]
    path_map = {
        'sans': 'assets/fonts/Montserrat.ttf',
        'mono': 'assets/fonts/JetBrainsMono.ttf',
        'display': 'assets/fonts/Unbounded.ttf',
        'inter': 'assets/fonts/Inter.ttf',
    }
    p = path_map.get(family, 'assets/fonts/Montserrat.ttf')
    if not os.path.exists(p):
        p = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    fnt = ImageFont.truetype(p, size)
    try:
        fnt.set_variation_by_name(weight.encode('utf-8'))
    except Exception:
        pass
    FONT_CACHE[key] = fnt
    return fnt


def ease_out_cubic(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return 1.0 - (1.0 - x) ** 3


def ease_in_out_sine(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return -(math.cos(math.pi * x) - 1.0) / 2.0


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def lerp_color(c1, c2, t: float):
    t = clamp01(t)
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(len(c1)))


def draw_text_centered(draw: ImageDraw.ImageDraw, cx: float, cy: float, text: str, font, fill=WHITE, stroke_width=0, stroke_fill=(0, 0, 0)):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = cx - tw / 2.0 - bbox[0]
    y = cy - th / 2.0 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def draw_text_left(draw: ImageDraw.ImageDraw, x: float, cy: float, text: str, font, fill=WHITE, stroke_width=0, stroke_fill=(0, 0, 0)):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    th = bbox[3] - bbox[1]
    y = cy - th / 2.0 - bbox[1]
    draw.text((x - bbox[0], y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


def draw_text_right(draw: ImageDraw.ImageDraw, rx: float, cy: float, text: str, font, fill=WHITE, stroke_width=0, stroke_fill=(0, 0, 0)):
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = rx - tw - bbox[0]
    y = cy - th / 2.0 - bbox[1]
    draw.text((x, y), text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)


# --- Vector Icon Helpers (Zero tofu boxes!) ---

def draw_check_icon(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float = 16, color=GREEN, bg_fill=(14, 58, 28)):
    if bg_fill is not None:
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=bg_fill, outline=color, width=2)
    pts = [
        (cx - r * 0.45, cy + r * 0.02),
        (cx - r * 0.10, cy + r * 0.38),
        (cx + r * 0.50, cy - r * 0.34),
    ]
    draw.line(pts, fill=color, width=max(3, int(r * 0.22)), joint='curve')


def draw_arrow_right(draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float = 14, color=GOLD_BRIGHT):
    draw.line([(cx - size, cy), (cx + size * 0.7, cy)], fill=color, width=4)
    pts = [
        (cx + size, cy),
        (cx + size * 0.15, cy - size * 0.65),
        (cx + size * 0.15, cy + size * 0.65),
    ]
    draw.polygon(pts, fill=color)


def draw_search_icon(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float = 10, color=GOLD_BRIGHT):
    draw.ellipse([cx - r, cy - r, cx + r * 0.6, cy + r * 0.6], outline=color, width=3)
    draw.line([(cx + r * 0.4, cy + r * 0.4), (cx + r * 1.15, cy + r * 1.15)], fill=color, width=3)


def draw_window_controls(draw: ImageDraw.ImageDraw, rx: float, cy: float, color=MUTED):
    # Minimize line
    draw.line([(rx - 86, cy), (rx - 70, cy)], fill=color, width=2)
    # Maximize square
    draw.rectangle([rx - 48, cy - 7, rx - 34, cy + 7], outline=color, width=2)
    # Close X
    draw.line([(rx - 14, cy - 7), (rx, cy + 7)], fill=color, width=2)
    draw.line([(rx - 14, cy + 7), (rx, cy - 7)], fill=color, width=2)


def draw_slider_handle(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float = 24, color=GOLD_BRIGHT):
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(16, 18, 24), outline=color, width=3)
    # Left triangle
    pts_l = [(cx - 13, cy), (cx - 4, cy - 8), (cx - 4, cy + 8)]
    # Right triangle
    pts_r = [(cx + 13, cy), (cx + 4, cy - 8), (cx + 4, cy + 8)]
    draw.polygon(pts_l, fill=color)
    draw.polygon(pts_r, fill=color)


def draw_flame_icon(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float = 1.0):
    s = scale
    pts_outer = [
        (cx, cy - 68 * s),
        (cx + 24 * s, cy - 32 * s),
        (cx + 42 * s, cy + 8 * s),
        (cx + 36 * s, cy + 42 * s),
        (cx + 18 * s, cy + 62 * s),
        (cx, cy + 68 * s),
        (cx - 18 * s, cy + 62 * s),
        (cx - 36 * s, cy + 42 * s),
        (cx - 42 * s, cy + 8 * s),
        (cx - 24 * s, cy - 32 * s),
    ]
    draw.polygon(pts_outer, fill=(238, 68, 22))
    pts_mid = [
        (cx, cy - 36 * s),
        (cx + 18 * s, cy - 6 * s),
        (cx + 29 * s, cy + 20 * s),
        (cx + 22 * s, cy + 46 * s),
        (cx, cy + 62 * s),
        (cx - 22 * s, cy + 46 * s),
        (cx - 29 * s, cy + 20 * s),
        (cx - 18 * s, cy - 6 * s),
    ]
    draw.polygon(pts_mid, fill=(252, 146, 24))
    pts_in = [
        (cx, cy - 2 * s),
        (cx + 14 * s, cy + 22 * s),
        (cx + 16 * s, cy + 44 * s),
        (cx, cy + 58 * s),
        (cx - 16 * s, cy + 44 * s),
        (cx - 14 * s, cy + 22 * s),
    ]
    draw.polygon(pts_in, fill=(255, 220, 65))
    draw.ellipse([cx - 9 * s, cy + 28 * s, cx + 9 * s, cy + 54 * s], fill=(255, 250, 195))


def create_base_background() -> Image.Image:
    arr = np.zeros((H, W, 3), dtype=np.float32)
    y_grid, x_grid = np.mgrid[0:H, 0:W].astype(np.float32)
    t_y = y_grid / H
    for c in range(3):
        arr[:, :, c] = BG_TOP[c] * (1.0 - t_y) + BG_BOT[c] * t_y

    r1 = np.sqrt(((x_grid - W * 0.5) / 520.0) ** 2 + ((y_grid - H * 0.26) / 480.0) ** 2)
    glow1 = np.exp(-r1 ** 2 * 1.4)
    arr[:, :, 0] += glow1 * 26.0
    arr[:, :, 1] += glow1 * 15.0
    arr[:, :, 2] += glow1 * 4.0

    r2 = np.sqrt(((x_grid - W * 0.5) / 600.0) ** 2 + ((y_grid - H * 0.62) / 600.0) ** 2)
    glow2 = np.exp(-r2 ** 2 * 1.5)
    arr[:, :, 0] += glow2 * 16.0
    arr[:, :, 1] += glow2 * 11.0
    arr[:, :, 2] += glow2 * 4.0

    grid_mask = ((x_grid.astype(int) % 60 == 0) & (y_grid.astype(int) % 60 == 0)).astype(np.float32)
    arr += grid_mask[:, :, None] * 12.0

    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB')
    draw = ImageDraw.Draw(img)

    m_x, m_y = 54, 48
    b_len = 118
    b_col = (182, 128, 34)
    b_w = 3
    draw.line([(m_x, m_y), (m_x + b_len, m_y)], fill=b_col, width=b_w)
    draw.line([(m_x, m_y), (m_x, m_y + b_len)], fill=b_col, width=b_w)
    draw.line([(W - m_x - b_len, m_y), (W - m_x, m_y)], fill=b_col, width=b_w)
    draw.line([(W - m_x, m_y), (W - m_x, m_y + b_len)], fill=b_col, width=b_w)
    draw.line([(m_x, H - m_y), (m_x + b_len, H - m_y)], fill=b_col, width=b_w)
    draw.line([(m_x, H - m_y - b_len), (m_x, H - m_y)], fill=b_col, width=b_w)
    draw.line([(W - m_x - b_len, H - m_y), (W - m_x, H - m_y)], fill=b_col, width=b_w)
    draw.line([(W - m_x, H - m_y - b_len), (W - m_x, H - m_y)], fill=b_col, width=b_w)

    f_foot = get_font('sans', 21, 'SemiBold')
    draw_text_centered(draw, W / 2, 1595, "W A R D O G S   ·   Г А Й Д   П О   К О Н Ф И Г У", f_foot, fill=(118, 124, 135))
    return img


class AssetsBundle:
    def __init__(self):
        self.base_bg = create_base_background()
        self.alley_on = Image.open('assets/alley_shadows_on.png').convert('RGB')
        self.alley_off = Image.open('assets/alley_shadows_off.png').convert('RGB')
        self.silos_on = Image.open('assets/silos_shadows_on.png').convert('RGB')
        self.silos_off = Image.open('assets/silos_shadows_off.png').convert('RGB')
        self.heli_on = Image.open('assets/heli_shadows_on.png').convert('RGB')
        self.heli_off = Image.open('assets/heli_shadows_off.png').convert('RGB')
        self.sniper_on = Image.open('assets/sniper_warehouse_shadows_on.png').convert('RGB')
        self.sniper_off = Image.open('assets/sniper_warehouse_shadows_off.png').convert('RGB')
        self.win_explorer = Image.open('assets/win_explorer_config.png').convert('RGB')
        self.win_notepad = Image.open('assets/win_notepad_config.png').convert('RGB')
        self.game_settings = Image.open('assets/game_video_settings.png').convert('RGB')


def crop_from_pil(im: Image.Image, target_w: int, target_h: int, focus_x: float = 0.5, focus_y: float = 0.5, zoom: float = 1.0) -> Image.Image:
    iw, ih = im.size
    scale = max(target_w / iw, target_h / ih) * zoom
    nw, nh = max(target_w, int(iw * scale)), max(target_h, int(ih * scale))
    im_resized = im.resize((nw, nh), Image.Resampling.BILINEAR)
    cx = int(nw * focus_x)
    cy = int(nh * focus_y)
    x0 = max(0, min(nw - target_w, cx - target_w // 2))
    y0 = max(0, min(nh - target_h, cy - target_h // 2))
    return im_resized.crop((x0, y0, x0 + target_w, y0 + target_h))


def make_rounded_mask(w: int, h: int, radius: int) -> Image.Image:
    mask = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    return mask


def draw_comparison_card(
    canvas: Image.Image,
    draw: ImageDraw.ImageDraw,
    x0: int,
    y0: int,
    cw: int,
    ch: int,
    img_off: Image.Image,
    img_on: Image.Image,
    split_ratio: float,
    focus_x: float = 0.5,
    focus_y: float = 0.45,
    zoom: float = 1.08,
    left_badge: str = "БЕЗ ТЕНЕЙ · 172 FPS",
    right_badge: str = "С ТЕНЯМИ · 116 FPS",
    target_box=None,
    caption_bottom: str = None,
):
    """Draws a real in-game before/after split comparison card with animated wipe slider and ZERO overlapping badges."""
    crop_off = crop_from_pil(img_off, cw, ch, focus_x=focus_x, focus_y=focus_y, zoom=zoom)
    crop_on = crop_from_pil(img_on, cw, ch, focus_x=focus_x, focus_y=focus_y, zoom=zoom)
    crop_off = ImageEnhance.Contrast(crop_off).enhance(1.08)

    split_x = int(cw * clamp01(split_ratio))
    combined = crop_on.copy()
    if split_x > 0:
        combined.paste(crop_off.crop((0, 0, split_x, ch)), (0, 0))

    cdraw = ImageDraw.Draw(combined)

    # Target callout box
    if target_box is not None:
        bx0, by0, bx1, by1, label_txt = target_box
        is_revealed = split_x > (bx0 + bx1) // 2
        col_outline = GREEN if is_revealed else RED
        cdraw.rounded_rectangle([bx0, by0, bx1, by1], radius=8, outline=col_outline, width=3)
        f_lbl = get_font('sans', 19, 'ExtraBold')
        tb = cdraw.textbbox((0, 0), label_txt, font=f_lbl)
        lw = (tb[2] - tb[0]) + 24
        lh = 32
        lx = max(14, min(cw - lw - 14, (bx0 + bx1 - lw) // 2))
        ly = max(68, by0 - lh - 8)
        col_box = (14, 96, 42) if is_revealed else (130, 22, 26)
        cdraw.rounded_rectangle([lx, ly, lx + lw, ly + lh], radius=6, fill=col_box, outline=col_outline, width=2)
        draw_text_centered(cdraw, lx + lw / 2, ly + lh / 2, label_txt, f_lbl, fill=WHITE)

    # Top badges (Left = БЕЗ ТЕНЕЙ, Right = С ТЕНЯМИ)
    f_badge = get_font('sans', 21, 'ExtraBold')
    tb_l = cdraw.textbbox((0, 0), left_badge, font=f_badge)
    lb_w = (tb_l[2] - tb_l[0]) + 32
    cdraw.rounded_rectangle([16, 16, 16 + lb_w, 58], radius=8, fill=(12, 48, 24), outline=GREEN, width=2)
    draw_text_centered(cdraw, 16 + lb_w / 2, 37, left_badge, f_badge, fill=GREEN)

    tb_r = cdraw.textbbox((0, 0), right_badge, font=f_badge)
    rb_w = (tb_r[2] - tb_r[0]) + 32
    cdraw.rounded_rectangle([cw - 16 - rb_w, 16, cw - 16, 58], radius=8, fill=(54, 16, 18), outline=RED, width=2)
    draw_text_centered(cdraw, cw - 16 - rb_w / 2, 37, right_badge, f_badge, fill=RED)

    # Bottom centered caption pill (No side pills at the bottom so it NEVER overlaps!)
    if caption_bottom:
        f_cap = get_font('sans', 20, 'ExtraBold')
        tb_c = cdraw.textbbox((0, 0), caption_bottom, font=f_cap)
        cap_w = min(cw - 32, (tb_c[2] - tb_c[0]) + 40)
        cdraw.rounded_rectangle([cw // 2 - cap_w // 2, ch - 54, cw // 2 + cap_w // 2, ch - 14], radius=9, fill=(14, 16, 22), outline=GOLD, width=2)
        draw_text_centered(cdraw, cw / 2, ch - 34, caption_bottom, f_cap, fill=GOLD_BRIGHT)

    # Vertical wipe line & vector slider handle
    if 12 < split_x < cw - 12:
        cdraw.line([(split_x, 0), (split_x, ch)], fill=GOLD_BRIGHT, width=4)
        draw_slider_handle(cdraw, split_x, ch // 2, r=24, color=GOLD_BRIGHT)

    mask = make_rounded_mask(cw, ch, 18)
    canvas.paste(combined, (x0, y0), mask)
    draw.rounded_rectangle([x0, y0, x0 + cw, y0 + ch], radius=18, outline=(95, 105, 122), width=2)


def draw_top_progress(draw: ImageDraw.ImageDraw, progress: float, step_label: str = None, badge_color=GOLD):
    x_left, x_right = 92, W - 92
    y_bar = 108
    draw.rounded_rectangle([x_left, y_bar - 3, x_right, y_bar + 3], radius=3, fill=(45, 48, 55))
    fill_w = int((x_right - x_left) * clamp01(progress))
    if fill_w > 6:
        draw.rounded_rectangle([x_left, y_bar - 3, x_left + fill_w, y_bar + 3], radius=3, fill=GOLD)
        gx = x_left + fill_w
        draw.ellipse([gx - 6, y_bar - 6, gx + 6, y_bar + 6], fill=GOLD_BRIGHT)

    if step_label:
        f_step = get_font('sans', 24, 'ExtraBold')
        tb = draw.textbbox((0, 0), step_label, font=f_step)
        bw = (tb[2] - tb[0]) + 44
        bh = 52
        bx, by = 92, 146
        bg_fill = (32, 26, 14) if badge_color == GOLD else (14, 36, 22)
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=10, fill=bg_fill, outline=badge_color, width=2)
        draw_text_centered(draw, bx + bw / 2, by + bh / 2, step_label, f_step, fill=badge_color)


def draw_section_title(draw: ImageDraw.ImageDraw, title: str, y_center: int = 248, accent_color=GOLD):
    bx = 92
    draw.rounded_rectangle([bx, y_center - 30, bx + 10, y_center + 30], radius=4, fill=accent_color)
    f_title = get_font('sans', 58, 'Black')
    draw_text_left(draw, bx + 28, y_center, title, f_title, fill=WHITE)


def draw_kv_row(draw: ImageDraw.ImageDraw, y_center: int, left_text: str, right_text: str, right_color=GREEN, alpha: float = 1.0):
    if alpha <= 0.02:
        return
    c_left = lerp_color(BG_TOP, SILVER, alpha)
    c_right = lerp_color(BG_TOP, right_color, alpha)
    c_line = lerp_color(BG_TOP, (40, 44, 52), alpha)
    f_l = get_font('sans', 29, 'SemiBold')
    f_r = get_font('sans', 30, 'ExtraBold')
    draw_text_left(draw, 92, y_center, left_text, f_l, fill=c_left)
    draw_text_right(draw, W - 92, y_center, right_text, f_r, fill=c_right)
    draw.line([(92, y_center + 34), (W - 92, y_center + 34)], fill=c_line, width=1)


def render_scene_hook(bundle: AssetsBundle, local_t: float, scene_dur: float, global_progress: float) -> Image.Image:
    """Scene 1: HOOK — Real In-Game Comparison + 'ТЕНИ В НОЛЬ' right from Frame 0!"""
    img = bundle.base_bg.copy()
    draw = ImageDraw.Draw(img)
    draw_top_progress(draw, global_progress)

    pulse = 1.0 + 0.05 * math.sin(local_t * 6.0)
    draw_flame_icon(draw, W / 2, 178, scale=0.68 * pulse)

    f_pill = get_font('sans', 23, 'ExtraBold')
    pw, ph = 360, 48
    px, py = (W - pw) // 2, 238
    draw.rounded_rectangle([px, py, px + pw, py + ph], radius=9, fill=(28, 22, 12), outline=GOLD, width=2)
    draw_text_centered(draw, W / 2, py + ph / 2, "STEAM  ·  WARDOGS", f_pill, fill=GOLD_BRIGHT)

    f_hero = get_font('sans', 76, 'Black')
    draw_text_centered(draw, W / 2, 338, "ТЕНИ В НОЛЬ", f_hero, fill=WHITE)

    f_sub = get_font('sans', 30, 'SemiBold')
    draw_text_centered(draw, W / 2, 405, "Видно всех врагов — даже в тумане и на закате", f_sub, fill=SILVER)

    cx0, cy0, cw, ch = 84, 452, W - 168, 720
    half_t = scene_dur * 0.52
    if local_t < half_t:
        sub_p = local_t / max(0.01, half_t)
        split_r = 0.22 + 0.60 * ease_in_out_sine(min(1.0, sub_p * 1.35))
        zoom = 1.12 + 0.05 * sub_p
        draw_comparison_card(
            img, draw, cx0, cy0, cw, ch,
            bundle.alley_off, bundle.alley_on,
            split_ratio=split_r,
            focus_x=0.48, focus_y=0.45, zoom=zoom,
            left_badge="БЕЗ ТЕНЕЙ · 172 FPS",
            right_badge="С ТЕНЯМИ · 116 FPS",
            target_box=(340, 210, 560, 470, "ПРОХОД И ОКНА ВИДНО СРАЗУ"),
            caption_bottom="РЕАЛЬНЫЕ КАДРЫ ИЗ ИГРЫ · КАРТА NO MANS LAND",
        )
    else:
        sub_p = (local_t - half_t) / max(0.01, scene_dur - half_t)
        split_r = 0.20 + 0.64 * ease_in_out_sine(min(1.0, sub_p * 1.35))
        zoom = 1.10 + 0.06 * sub_p
        draw_comparison_card(
            img, draw, cx0, cy0, cw, ch,
            bundle.sniper_off, bundle.sniper_on,
            split_ratio=split_r,
            focus_x=0.46, focus_y=0.46, zoom=zoom,
            left_badge="БЕЗ ТЕНЕЙ · КОНТРАСТ Х2",
            right_badge="С ТЕНЯМИ · ВРАГ В ТЕНИ",
            target_box=(210, 215, 445, 425, "МОДЕЛИ В ОКНАХ СВЕТЯТСЯ"),
            caption_bottom="РЕАЛЬНЫЙ СКРИНШОТ WARDOGS · ГАЙД BRYCE",
        )

    # Bottom Callout Box: 2 МИНУТЫ -> +КОНТРАСТ И +FPS
    bw, bh = 760, 84
    bx, by = (W - bw) // 2, 1210
    draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=12, fill=(30, 24, 12), outline=GOLD, width=2)
    f_cta = get_font('sans', 34, 'ExtraBold')
    draw_text_centered(draw, W / 2, by + bh / 2, "2 МИНУТЫ   >>   +КОНТРАСТ И +FPS", f_cta, fill=GOLD_BRIGHT)

    bw2, bh2 = 760, 66
    bx2, by2 = (W - bw2) // 2, 1318
    draw.rounded_rectangle([bx2, by2, bx2 + bw2, by2 + bh2], radius=10, fill=(14, 36, 22), outline=GREEN, width=2)
    draw_check_icon(draw, bx2 + 38, by2 + bh2 / 2, r=15, color=GREEN, bg_fill=None)
    f_sub2 = get_font('sans', 24, 'ExtraBold')
    draw_text_centered(draw, W / 2 + 16, by2 + bh2 / 2, "1 ЦИФРА В GAMEUSERSETTINGS.INI · БЕЗ БАНА", f_sub2, fill=GREEN)

    f_tag = get_font('sans', 22, 'SemiBold')
    draw_text_centered(draw, W / 2, 1430, "ПОШАГОВЫЙ ГАЙД ПО КОНФИГУ  ·  3 ПРОСТЫХ ШАГА", f_tag, fill=MUTED)
    return img


def render_scene_step1(bundle: AssetsBundle, local_t: float, scene_dur: float, global_progress: float) -> Image.Image:
    """Scene 2: STEP 1 — Path to Config (Win+R + Real Windows 11 Explorer screenshot)."""
    img = bundle.base_bg.copy()
    draw = ImageDraw.Draw(img)
    draw_top_progress(draw, global_progress, "ШАГ 1 ИЗ 3", GOLD)
    draw_section_title(draw, "ПУТЬ К КОНФИГУ", y_center=248, accent_color=GOLD)

    draw_kv_row(draw, 336, "ИГРА", "ЗАКРЫТА ПОЛНОСТЬЮ", GREEN, clamp01(local_t / 0.35))
    draw_kv_row(draw, 408, "WIN + R", "ОТКРЫТЬ «ВЫПОЛНИТЬ»", GREEN, clamp01((local_t - 0.15) / 0.35))

    cx0, cy0, cw, ch = 84, 468, W - 168, 376
    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=16, fill=CARD_BG, outline=CARD_BORDER, width=2)
    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + 58], radius=16, fill=(30, 34, 44))
    draw.rectangle([cx0, cy0 + 40, cx0 + cw, cy0 + 58], fill=(30, 34, 44))
    draw.rounded_rectangle([cx0 + 22, cy0 + 16, cx0 + 48, cy0 + 42], radius=4, fill=(0, 168, 255))
    draw_text_left(draw, cx0 + 62, cy0 + 29, "Выполнить (Win + R)", get_font('sans', 23, 'Bold'), fill=WHITE)
    draw_window_controls(draw, cx0 + cw - 22, cy0 + 29, color=MUTED)

    draw_text_left(draw, cx0 + 32, cy0 + 100, "Введите путь к папке конфигов и нажмите ОК:", get_font('sans', 25, 'SemiBold'), fill=SILVER)

    ix0, iy0, iw, ih = cx0 + 32, cy0 + 138, cw - 64, 82
    draw.rounded_rectangle([ix0, iy0, ix0 + iw, iy0 + ih], radius=10, fill=(12, 15, 20), outline=GOLD if local_t > 1.0 else (80, 90, 110), width=2)

    full_path = r"%LocalAppData%\Wardogs\Saved\Config\WindowsClient"
    type_p = clamp01((local_t - 0.35) / 1.85)
    n_chars = int(len(full_path) * type_p)
    typed_str = full_path[:n_chars]
    f_path = get_font('mono', 25, 'Bold')
    draw_text_left(draw, ix0 + 18, iy0 + ih / 2, typed_str, f_path, fill=WHITE)

    if int(local_t * 4) % 2 == 0:
        tb = draw.textbbox((0, 0), typed_str, font=f_path)
        cur_x = min(ix0 + iw - 18, ix0 + 18 + (tb[2] - tb[0]) + 4)
        draw.line([(cur_x, iy0 + 18), (cur_x, iy0 + ih - 18)], fill=GOLD_BRIGHT, width=3)

    enter_active = local_t >= 2.1
    eb_x, eb_y, eb_w, eb_h = cx0 + 32, cy0 + 250, 170, 56
    draw.rounded_rectangle(
        [eb_x, eb_y, eb_x + eb_w, eb_y + eb_h],
        radius=10,
        fill=(18, 52, 28) if enter_active else (22, 26, 34),
        outline=GREEN if enter_active else (70, 78, 92),
        width=2,
    )
    draw_text_centered(draw, eb_x + eb_w / 2, eb_y + eb_h / 2, "ENTER", get_font('sans', 24, 'ExtraBold'), fill=GREEN if enter_active else MUTED)
    draw_text_left(draw, eb_x + eb_w + 18, eb_y + eb_h / 2, "после вставки пути", get_font('sans', 23, 'SemiBold'), fill=SILVER)

    ok_x, ok_y, ok_w, ok_h = cx0 + cw - 172, cy0 + 250, 140, 56
    can_x = ok_x - 165
    draw.rounded_rectangle([can_x, ok_y, can_x + 148, ok_y + ok_h], radius=10, fill=(28, 32, 42), outline=(80, 88, 105), width=2)
    draw_text_centered(draw, can_x + 74, ok_y + ok_h / 2, "Отмена", get_font('sans', 24, 'Bold'), fill=SILVER)

    draw.rounded_rectangle([ok_x, ok_y, ok_x + ok_w, ok_y + ok_h], radius=10, fill=(92, 68, 14) if enter_active else (55, 42, 12), outline=GOLD_BRIGHT, width=2)
    draw_text_centered(draw, ok_x + ok_w / 2, ok_y + ok_h / 2, "ОК", get_font('sans', 25, 'ExtraBold'), fill=GOLD_BRIGHT)

    # Bottom Card: Real Windows 11 Explorer Screenshot showing GameUserSettings.ini
    ex0, ey0, ew, eh = 84, 875, W - 168, 600
    exp_crop = crop_from_pil(bundle.win_explorer, ew, eh, focus_x=0.38, focus_y=0.28, zoom=1.18)
    exp_draw = ImageDraw.Draw(exp_crop)
    exp_draw.rectangle([0, 0, ew, 54], fill=(16, 20, 28))
    draw_text_left(exp_draw, 22, 27, "РЕАЛЬНАЯ ПАПКА В ПРОВОДНИКЕ WINDOWS:", get_font('sans', 21, 'ExtraBold'), fill=GOLD_BRIGHT)

    zoom_box = bundle.win_explorer.crop((95, 60, 740, 235)).resize((ew - 40, 230), Image.Resampling.LANCZOS)
    z_draw = ImageDraw.Draw(zoom_box)
    z_draw.rounded_rectangle([14, 148, ew - 54, 205], radius=8, outline=(18, 195, 75), width=4)
    exp_crop.paste(zoom_box, (20, eh - 295))
    exp_draw.rounded_rectangle([20, eh - 295, ew - 20, eh - 65], radius=12, outline=GREEN, width=3)

    exp_draw.rectangle([0, eh - 56, ew, eh], fill=(14, 38, 22))
    draw_text_centered(exp_draw, ew / 2 - 18, eh - 28, "НУЖЕН ФАЙЛ:  GameUserSettings.ini", get_font('mono', 24, 'ExtraBold'), fill=GREEN)
    draw_check_icon(exp_draw, ew / 2 + 285, eh - 28, r=14, color=GREEN, bg_fill=None)

    mask = make_rounded_mask(ew, eh, 16)
    img.paste(exp_crop, (ex0, ey0), mask)
    draw.rounded_rectangle([ex0, ey0, ex0 + ew, ey0 + eh], radius=16, outline=GREEN if enter_active else CARD_BORDER, width=2)
    return img


def render_scene_step2(bundle: AssetsBundle, local_t: float, scene_dur: float, global_progress: float) -> Image.Image:
    """Scene 3: STEP 2 — Find Parameter (100% Fixed Notepad UI + Real Notepad Screenshot)."""
    img = bundle.base_bg.copy()
    draw = ImageDraw.Draw(img)
    draw_top_progress(draw, global_progress, "ШАГ 2 ИЗ 3", GOLD)
    draw_section_title(draw, "НАЙДИ ПАРАМЕТР", y_center=248, accent_color=GOLD)

    draw_kv_row(draw, 336, "ОТКРЫТЬ ФАЙЛ", "БЛОКНОТОМ", GOLD_BRIGHT, clamp01(local_t / 0.35))
    draw_kv_row(draw, 408, "CTRL + F", "ПОИСК ПО ФАЙЛУ", GREEN, clamp01((local_t - 0.15) / 0.35))

    nx0, ny0, nw, nh = 84, 468, W - 168, 486
    draw.rounded_rectangle([nx0, ny0, nx0 + nw, ny0 + nh], radius=16, fill=CARD_BG_DARK, outline=(72, 82, 102), width=2)

    draw.rounded_rectangle([nx0, ny0, nx0 + nw, ny0 + 56], radius=16, fill=(28, 33, 44))
    draw.rectangle([nx0, ny0 + 38, nx0 + nw, ny0 + 56], fill=(28, 33, 44))
    draw.rounded_rectangle([nx0 + 22, ny0 + 15, nx0 + 48, ny0 + 41], radius=5, fill=(56, 152, 255))
    draw_text_left(draw, nx0 + 62, ny0 + 28, "GameUserSettings.ini — Блокнот", get_font('sans', 23, 'Bold'), fill=WHITE)
    draw_window_controls(draw, nx0 + nw - 22, ny0 + 28, color=MUTED)

    my = ny0 + 90
    draw_text_left(draw, nx0 + 28, my, "Файл     Правка     Вид", get_font('sans', 22, 'SemiBold'), fill=SILVER)

    sx0, sy0, sw, sh = nx0 + 390, ny0 + 66, nw - 414, 48
    found_state = local_t >= 1.50
    draw.rounded_rectangle([sx0, sy0, sx0 + sw, sy0 + sh], radius=9, fill=(10, 13, 18), outline=GOLD_BRIGHT if found_state else (90, 102, 125), width=2)
    draw_search_icon(draw, sx0 + 24, sy0 + sh / 2 - 1, r=9, color=GOLD_BRIGHT)

    search_target = "sg.ShadowQuality"
    sp = clamp01((local_t - 0.30) / 1.10)
    s_typed = search_target[:int(len(search_target) * sp)]
    draw_text_left(draw, sx0 + 46, sy0 + sh / 2, s_typed, get_font('mono', 22, 'Bold'), fill=WHITE)

    draw.line([(nx0 + 16, ny0 + 126), (nx0 + nw - 16, ny0 + 126)], fill=(45, 52, 66), width=1)

    ini_lines = [
        ("[ScalabilityGroups]", (130, 175, 255)),
        ("sg.ResolutionQuality=100", (175, 186, 204)),
        ("sg.ViewDistanceQuality=1", (175, 186, 204)),
        ("sg.AntiAliasingQuality=1", (175, 186, 204)),
    ]
    f_ini = get_font('mono', 24, 'Medium')
    for idx, (txt, col) in enumerate(ini_lines):
        ly = ny0 + 162 + idx * 46
        draw_text_left(draw, nx0 + 36, ly, txt, f_ini, fill=col)

    hy0, hy1 = ny0 + 356, ny0 + 432
    if found_state:
        draw.rounded_rectangle([nx0 + 24, hy0, nx0 + nw - 24, hy1], radius=10, fill=(68, 50, 12), outline=GOLD_BRIGHT, width=2)
        draw.rounded_rectangle([nx0 + 24, hy0, nx0 + 34, hy1], radius=4, fill=GOLD_BRIGHT)
        draw_text_left(draw, nx0 + 52, (hy0 + hy1) / 2, "sg.ShadowQuality = 0", get_font('mono', 31, 'ExtraBold'), fill=WHITE)
        draw.rounded_rectangle([nx0 + nw - 235, hy0 + 12, nx0 + nw - 42, hy1 - 12], radius=8, fill=(18, 65, 32), outline=GREEN, width=2)
        draw_text_centered(draw, nx0 + nw - 152, (hy0 + hy1) / 2, "НАЙДЕНО", get_font('sans', 21, 'ExtraBold'), fill=GREEN)
        draw_check_icon(draw, nx0 + nw - 68, (hy0 + hy1) / 2, r=11, color=GREEN, bg_fill=None)
    else:
        draw_text_left(draw, nx0 + 36, (hy0 + hy1) / 2, "sg.ShadowQuality = 0", get_font('mono', 30, 'Bold'), fill=GOLD_BRIGHT)

    # Bottom Card: Real Windows 11 Notepad Screenshot from the Guide
    rx0, ry0, rw, rh = 84, 982, W - 168, 505
    np_crop = bundle.win_notepad.crop((0, 380, 760, 657)).resize((rw, rh - 56), Image.Resampling.LANCZOS)
    np_card = Image.new('RGB', (rw, rh), (16, 20, 28))
    np_card.paste(np_crop, (0, 56))
    np_draw = ImageDraw.Draw(np_card)
    np_draw.rectangle([0, 0, rw, 56], fill=(18, 22, 32))
    draw_text_left(np_draw, 22, 28, "РЕАЛЬНЫЙ ФАЙЛ GAMEUSERSETTINGS.INI В БЛОКНОТЕ:", get_font('sans', 21, 'ExtraBold'), fill=GOLD_BRIGHT)

    np_draw.rounded_rectangle([12, 398, 460, 448], radius=8, outline=(22, 210, 85), width=4)
    np_draw.rounded_rectangle([475, 396, rw - 20, 450], radius=8, fill=(14, 52, 26), outline=GREEN, width=2)
    draw_text_centered(np_draw, (475 + rw - 20) / 2, 423, "<< ВОТ ЭТА СТРОКА!", get_font('sans', 22, 'ExtraBold'), fill=GREEN)

    mask = make_rounded_mask(rw, rh, 16)
    img.paste(np_card, (rx0, ry0), mask)
    draw.rounded_rectangle([rx0, ry0, rx0 + rw, ry0 + rh], radius=16, outline=GOLD if found_state else CARD_BORDER, width=2)
    return img


def render_scene_step3(bundle: AssetsBundle, local_t: float, scene_dur: float, global_progress: float) -> Image.Image:
    """Scene 4: STEP 3 — Set '= 4' + Read-Only + Warning (ZERO overlap on 0/4 and ВКЛ/ВЫКЛ!)."""
    img = bundle.base_bg.copy()
    draw = ImageDraw.Draw(img)
    draw_top_progress(draw, global_progress, "ШАГ 3 ИЗ 3", GOLD)
    draw_section_title(draw, "ПОСТАВЬ ЦИФРУ 4", y_center=248, accent_color=GOLD)

    switched_to_4 = local_t >= 1.25
    toggle_off = local_t >= 3.60

    bx0, by0, bw, bh = 84, 310, W - 168, 162
    draw.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=16, fill=CARD_BG_DARK, outline=GREEN if switched_to_4 else RED, width=3)

    f_code = get_font('mono', 35, 'Bold')
    f_val = get_font('mono', 42, 'ExtraBold')
    cy_code = by0 + 62

    draw_text_left(draw, bx0 + 30, cy_code, "sg.ShadowQuality =", f_code, fill=WHITE)

    if not switched_to_4:
        vx = bx0 + 448
        draw.rounded_rectangle([vx, cy_code - 32, vx + 72, cy_code + 32], radius=10, fill=(75, 18, 22), outline=RED, width=2)
        draw_text_centered(draw, vx + 36, cy_code, "0", f_val, fill=RED)
        draw.rounded_rectangle([vx + 92, cy_code - 26, bx0 + bw - 24, cy_code + 26], radius=8, fill=(55, 16, 18), outline=RED, width=1)
        draw_text_centered(draw, (vx + 92 + bx0 + bw - 24) / 2, cy_code, "0 = ТЕНИ ЕСТЬ", get_font('sans', 22, 'ExtraBold'), fill=RED)
    else:
        # Separated 0 (crossed out) -> vector arrow -> 4 -> green pill
        vx0 = bx0 + 442
        draw.rounded_rectangle([vx0, cy_code - 26, vx0 + 54, cy_code + 26], radius=8, fill=(45, 16, 18), outline=(140, 45, 45), width=1)
        draw_text_centered(draw, vx0 + 27, cy_code, "0", get_font('mono', 28, 'Bold'), fill=(180, 70, 70))
        draw.line([(vx0 + 10, cy_code + 13), (vx0 + 44, cy_code - 13)], fill=RED, width=3)

        draw_arrow_right(draw, vx0 + 82, cy_code, size=14, color=GOLD_BRIGHT)

        vx4 = vx0 + 112
        draw.rounded_rectangle([vx4, cy_code - 34, vx4 + 80, cy_code + 34], radius=12, fill=(14, 72, 34), outline=GREEN, width=3)
        draw_text_centered(draw, vx4 + 40, cy_code, "4", f_val, fill=GREEN)

        draw.rounded_rectangle([vx4 + 96, cy_code - 28, bx0 + bw - 22, cy_code + 28], radius=9, fill=(14, 52, 26), outline=GREEN, width=2)
        draw_check_icon(draw, vx4 + 122, cy_code, r=12, color=GREEN, bg_fill=None)
        draw_text_centered(draw, (vx4 + 138 + bx0 + bw - 22) / 2, cy_code, "ТЕНИ В НОЛЬ!", get_font('sans', 21, 'ExtraBold'), fill=GREEN)

    draw.line([(bx0 + 24, by0 + 112), (bx0 + bw - 24, by0 + 112)], fill=(42, 48, 60), width=1)
    draw_text_centered(
        draw, W / 2, by0 + 136,
        "Внимание: именно цифра 4 (а не 0!) полностью выключает тени",
        get_font('sans', 21, 'SemiBold'),
        fill=GOLD_BRIGHT if switched_to_4 else SILVER,
    )

    draw_kv_row(draw, 522, "СОХРАНИТЬ ФАЙЛ", "CTRL + S", GOLD_BRIGHT, clamp01((local_t - 1.3) / 0.35))
    draw_kv_row(draw, 594, "СВОЙСТВА ФАЙЛА (ПКМ)", "ТОЛЬКО ДЛЯ ЧТЕНИЯ", GREEN, clamp01((local_t - 1.7) / 0.35))
    draw_kv_row(draw, 666, "МЕНЮ НАСТРОЕК В ИГРЕ", "НЕ ТРОГАТЬ!", RED, clamp01((local_t - 2.1) / 0.35))

    # Warning Card + Real In-Game Video Settings Preview
    wx0, wy0, ww, wh = 84, 724, W - 168, 590
    draw.rounded_rectangle([wx0, wy0, wx0 + ww, wy0 + wh], radius=16, fill=(28, 14, 16), outline=(185, 52, 52), width=2)

    warn_hdr = "ВАЖНО: ИНАЧЕ НАСТРОЙКА СЛЕТИТ"
    f_wh = get_font('sans', 21, 'ExtraBold')
    tb_w = draw.textbbox((0, 0), warn_hdr, font=f_wh)
    wh_w = (tb_w[2] - tb_w[0]) + 40
    draw.rounded_rectangle([wx0 + 28, wy0 + 22, wx0 + 28 + wh_w, wy0 + 66], radius=8, fill=(95, 22, 26), outline=RED, width=1)
    draw_text_centered(draw, wx0 + 28 + wh_w / 2, wy0 + 44, warn_hdr, f_wh, fill=WHITE)

    f_warn = get_font('sans', 25, 'SemiBold')
    draw_text_left(draw, wx0 + 28, wy0 + 98, "Любое изменение в меню игры (даже звук или бинды)", f_warn, fill=WHITE)
    draw_text_left(draw, wx0 + 28, wy0 + 136, "сбросит тени — тогда просто повтори шаг с конфигом.", f_warn, fill=SILVER)

    sw_w, sw_h = ww - 48, wh - 194
    set_crop = crop_from_pil(bundle.game_settings, sw_w, sw_h, focus_x=0.26, focus_y=0.52, zoom=1.12)
    set_draw = ImageDraw.Draw(set_crop)
    set_draw.rectangle([0, sw_h - 54, sw_w, sw_h], fill=(45, 12, 14))
    draw_text_centered(
        set_draw, sw_w / 2, sw_h - 27,
        "МЕНЮ НАСТРОЕК В ИГРЕ НЕ ТРОГАТЬ (СТОИТ «ТОЛЬКО ЧТЕНИЕ»)",
        get_font('sans', 20, 'ExtraBold'), fill=(255, 150, 150),
    )
    mask_s = make_rounded_mask(sw_w, sw_h, 12)
    img.paste(set_crop, (wx0 + 24, wy0 + 172), mask_s)
    draw.rounded_rectangle([wx0 + 24, wy0 + 172, wx0 + 24 + sw_w, wy0 + 172 + sw_h], radius=12, outline=(140, 45, 48), width=2)

    # Bottom Shadow Status Toggle — 100% FIXED: ZERO OVERLAP!
    tx0, ty0, tw, th = 84, 1348, W - 168, 112
    if not toggle_off:
        draw.rounded_rectangle([tx0, ty0, tx0 + tw, ty0 + th], radius=18, fill=(32, 26, 14), outline=GOLD, width=2)
        trk_x, trk_y, trk_w, trk_h = tx0 + 32, ty0 + 26, 124, 60
        draw.rounded_rectangle([trk_x, trk_y, trk_x + trk_w, trk_y + trk_h], radius=30, fill=(110, 82, 18), outline=GOLD_BRIGHT, width=2)
        kx = trk_x + trk_w - 30
        ky = trk_y + trk_h // 2
        draw.ellipse([kx - 22, ky - 22, kx + 22, ky + 22], fill=GOLD_BRIGHT)
        draw_text_left(draw, trk_x + trk_w + 32, ty0 + th / 2, "ТЕНИ:  ВКЛЮЧЕНЫ (ПО УМОЛЧАНИЮ)", get_font('sans', 28, 'ExtraBold'), fill=GOLD_BRIGHT)
    else:
        draw.rounded_rectangle([tx0, ty0, tx0 + tw, ty0 + th], radius=18, fill=(14, 42, 24), outline=GREEN, width=3)
        trk_x, trk_y, trk_w, trk_h = tx0 + 32, ty0 + 26, 124, 60
        draw.rounded_rectangle([trk_x, trk_y, trk_x + trk_w, trk_y + trk_h], radius=30, fill=(20, 68, 36), outline=GREEN, width=2)
        kx = trk_x + 30
        ky = trk_y + trk_h // 2
        draw.ellipse([kx - 22, ky - 22, kx + 22, ky + 22], fill=GREEN)
        draw_text_left(draw, trk_x + trk_w + 32, ty0 + th / 2, "ТЕНИ В ИГРЕ:  ВЫКЛЮЧЕНЫ В НОЛЬ", get_font('sans', 27, 'ExtraBold'), fill=GREEN)
        draw_check_icon(draw, tx0 + tw - 46, ty0 + th / 2, r=18, color=GREEN, bg_fill=(10, 32, 18))

    return img


def render_scene_result(bundle: AssetsBundle, local_t: float, scene_dur: float, global_progress: float) -> Image.Image:
    """Scene 5: RESULT — 3 Real In-Game Comparison Scenarios + Fixed Padded Summary Box."""
    img = bundle.base_bg.copy()
    draw = ImageDraw.Draw(img)
    draw_top_progress(draw, global_progress, "РЕЗУЛЬТАТ В ИГРЕ", GREEN)
    draw_section_title(draw, "ВИДНО ВСЕХ ВРАГОВ", y_center=248, accent_color=GREEN)

    cx0, cy0, cw, ch = 84, 312, W - 168, 724
    p_norm = clamp01(local_t / max(0.01, scene_dur))

    if p_norm < 0.36:
        sub_p = p_norm / 0.36
        split_r = 0.16 + 0.70 * ease_in_out_sine(min(1.0, sub_p * 1.25))
        draw_comparison_card(
            img, draw, cx0, cy0, cw, ch,
            bundle.sniper_off, bundle.sniper_on,
            split_ratio=split_r,
            focus_x=0.46, focus_y=0.46, zoom=1.08 + 0.05 * sub_p,
            left_badge="БЕЗ ТЕНЕЙ · КОНТРАСТ Х2",
            right_badge="С ТЕНЯМИ · ТЕМНО",
            target_box=(205, 210, 445, 430, "ВРАГИ В ОКНАХ КАК НА ЛАДОНИ"),
            caption_bottom="РЕАЛЬНЫЙ КАДР 1/3 · ТЁМНЫЙ АНГАР И ОКНА",
        )
    elif p_norm < 0.70:
        sub_p = (p_norm - 0.36) / 0.34
        split_r = 0.18 + 0.68 * ease_in_out_sine(min(1.0, sub_p * 1.25))
        draw_comparison_card(
            img, draw, cx0, cy0, cw, ch,
            bundle.alley_off, bundle.alley_on,
            split_ratio=split_r,
            focus_x=0.48, focus_y=0.45, zoom=1.10 + 0.05 * sub_p,
            left_badge="БЕЗ ТЕНЕЙ · 172 FPS",
            right_badge="С ТЕНЯМИ · 116 FPS",
            target_box=(340, 200, 560, 470, "НЕТ ТЕНЕЙ МЕЖДУ ЗДАНИЯМИ"),
            caption_bottom="РЕАЛЬНЫЙ КАДР 2/3 · УЛИЦА И ОКНА (+56 FPS)",
        )
    else:
        sub_p = (p_norm - 0.70) / 0.30
        split_r = 0.20 + 0.68 * ease_in_out_sine(min(1.0, sub_p * 1.25))
        draw_comparison_card(
            img, draw, cx0, cy0, cw, ch,
            bundle.silos_off, bundle.silos_on,
            split_ratio=split_r,
            focus_x=0.50, focus_y=0.48, zoom=1.08 + 0.05 * sub_p,
            left_badge="БЕЗ ТЕНЕЙ · 177 FPS",
            right_badge="С ТЕНЯМИ · 126 FPS",
            target_box=(360, 290, 620, 465, "ЗА УКРЫТИЕМ ВСЁ ЧИТАЕТСЯ"),
            caption_bottom="РЕАЛЬНЫЙ КАДР 3/3 · ПРОМЗОНА И УКРЫТИЯ (+51 FPS)",
        )

    draw_kv_row(draw, 1088, "ТУМАН / ЗАКАТ", "МОДЕЛИ НЕ ПРЯЧУТСЯ", GREEN, 1.0)
    draw_kv_row(draw, 1158, "КОНТРАСТ И FPS", "НАМНОГО ВЫШЕ (+50 FPS)", GREEN, 1.0)

    gx0, gy0, gw, gh = 84, 1222, W - 168, 184
    draw.rounded_rectangle([gx0, gy0, gx0 + gw, gy0 + gh], radius=16, fill=(14, 42, 24), outline=GREEN, width=3)
    draw_text_centered(draw, W / 2, gy0 + 66, "БЕЗ ТЕНЕЙ", get_font('sans', 54, 'Black'), fill=GREEN)
    draw_text_centered(draw, W / 2, gy0 + 134, "МОДЕЛИ ИГРОКОВ ВИДНО СРАЗУ", get_font('sans', 26, 'Bold'), fill=WHITE)

    draw_text_left(draw, 88, 1448, "Реальные скриншоты из игры: Bryce · гайд в Steam Community", get_font('sans', 22, 'SemiBold'), fill=SILVER)
    return img


def render_scene_outro(bundle: AssetsBundle, local_t: float, scene_dur: float, global_progress: float) -> Image.Image:
    """Scene 6: OUTRO — Cheat Sheet ('ШПАРГАЛКА — СОХРАНИ') + Real Game Preview for Seamless Loop!"""
    img = bundle.base_bg.copy()
    draw = ImageDraw.Draw(img)
    draw_top_progress(draw, 1.0)

    pulse = 1.0 + 0.06 * math.sin(local_t * 6.5)
    draw_flame_icon(draw, W / 2, 182, scale=0.72 * pulse)

    f_cta1 = get_font('sans', 58, 'Black')
    draw_text_centered(draw, W / 2, 286, "СОХРАНИ ВИДЕО", f_cta1, fill=WHITE)
    draw_text_centered(draw, W / 2, 354, "И ПОДПИШИСЬ НА КАНАЛ", get_font('sans', 44, 'ExtraBold'), fill=GOLD_BRIGHT)
    draw_text_centered(draw, W / 2, 414, "Сделай скрин шпаргалки, чтобы не искать путь заново:", get_font('sans', 25, 'SemiBold'), fill=SILVER)

    cx0, cy0, cw, ch = 84, 456, W - 168, 496
    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + ch], radius=18, fill=CARD_BG_DARK, outline=GOLD, width=2)
    draw.rounded_rectangle([cx0, cy0, cx0 + cw, cy0 + 58], radius=18, fill=(38, 30, 14))
    draw.rectangle([cx0, cy0 + 40, cx0 + cw, cy0 + 58], fill=(38, 30, 14))
    draw_text_centered(draw, W / 2, cy0 + 29, "ШПАРГАЛКА ПО КОНФИГУ WARDOGS (СОХРАНИ)", get_font('sans', 23, 'ExtraBold'), fill=GOLD_BRIGHT)

    steps_info = [
        ("ШАГ 1 · WIN + R (ПАПКА КОНФИГА):", r"%LocalAppData%\Wardogs\Saved\Config\WindowsClient", GOLD_BRIGHT),
        ("ШАГ 2 · ОТКРЫТЬ ФАЙЛ БЛОКНОТОМ:", "GameUserSettings.ini   (поиск через Ctrl + F)", WHITE),
        ("ШАГ 3 · ИЗМЕНИТЬ ПАРАМЕТР + ЗАЩИТА:", "sg.ShadowQuality=4   +   Только для чтения", GREEN),
    ]
    for idx, (st_lbl, st_val, st_col) in enumerate(steps_info):
        ry = cy0 + 82 + idx * 134
        draw.rounded_rectangle([cx0 + 24, ry, cx0 + cw - 24, ry + 116], radius=12, fill=(18, 22, 30), outline=(55, 64, 80), width=1)
        draw_text_left(draw, cx0 + 44, ry + 34, st_lbl, get_font('sans', 21, 'ExtraBold'), fill=SILVER)
        f_v = get_font('mono', 23 if idx == 0 else 26, 'Bold')
        draw_text_left(draw, cx0 + 44, ry + 78, st_val, f_v, fill=st_col)
        if idx == 2:
            draw_check_icon(draw, cx0 + cw - 58, ry + 58, r=16, color=GREEN, bg_fill=(12, 42, 22))

    px0, py0, pw, ph = 84, 982, W - 168, 490
    loop_p = clamp01(local_t / max(0.01, scene_dur))
    split_r = 0.68 - 0.46 * ease_in_out_sine(loop_p)
    draw_comparison_card(
        img, draw, px0, py0, pw, ph,
        bundle.alley_off, bundle.alley_on,
        split_ratio=split_r,
        focus_x=0.48, focus_y=0.45, zoom=1.12,
        left_badge="БЕЗ ТЕНЕЙ · 172 FPS",
        right_badge="С ТЕНЯМИ · 116 FPS",
        caption_bottom="НАПИШИ В КОММЕНТАХ: СКОЛЬКО FPS ДАЛО ТЕБЕ?",
    )
    return img


if __name__ == '__main__':
    bundle = AssetsBundle()
    os.makedirs('/tmp/preview_new', exist_ok=True)
    samples = [
        ('01_hook_alley.jpg', render_scene_hook(bundle, 1.2, 6.5, 0.05)),
        ('02_hook_sniper.jpg', render_scene_hook(bundle, 4.8, 6.5, 0.12)),
        ('03_step1_path.jpg', render_scene_step1(bundle, 3.5, 8.4, 0.28)),
        ('04_step2_search.jpg', render_scene_step2(bundle, 1.0, 6.7, 0.42)),
        ('05_step2_found.jpg', render_scene_step2(bundle, 3.2, 6.7, 0.48)),
        ('06_step3_before4.jpg', render_scene_step3(bundle, 0.8, 9.1, 0.56)),
        ('07_step3_after4.jpg', render_scene_step3(bundle, 2.5, 9.1, 0.62)),
        ('08_step3_toggle_off.jpg', render_scene_step3(bundle, 5.0, 9.1, 0.68)),
        ('09_result_sniper.jpg', render_scene_result(bundle, 1.2, 6.8, 0.76)),
        ('10_result_alley.jpg', render_scene_result(bundle, 3.5, 6.8, 0.82)),
        ('11_result_silos.jpg', render_scene_result(bundle, 5.8, 6.8, 0.88)),
        ('12_outro_cheatsheet.jpg', render_scene_outro(bundle, 2.0, 6.7, 0.96)),
    ]
    for name, im in samples:
        im.save(f'/tmp/preview_new/{name}', quality=93)

    cw, ch = 360, 640
    for s_idx in range(2):
        sheet = Image.new('RGB', (cw * 3, ch * 2), (0, 0, 0))
        for i in range(6):
            name, im = samples[s_idx * 6 + i]
            r, c = divmod(i, 3)
            sheet.paste(im.resize((cw, ch), Image.Resampling.LANCZOS), (c * cw, r * ch))
        sheet.save(f'/tmp/preview_sheet_{s_idx+1}.jpg', quality=92)
    print("Updated preview sheets generated!")


def fix_step3_toggle_text():
    pass


def load_wav_mono_48k(src_path: str) -> np.ndarray:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    tmp_wav = f"/tmp/tmp_{os.path.basename(src_path)}.wav"
    subprocess.run(
        [ffmpeg_exe, "-hide_banner", "-y", "-i", src_path, "-ac", "1", "-ar", "48000", tmp_wav],
        check=True,
        capture_output=True,
    )
    with wave.open(tmp_wav, "rb") as wf:
        data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
    return data


def extract_clean_voice_48k(audio_mix: np.ndarray, music: np.ndarray, sr: int = 48000) -> np.ndarray:
    """Removes the background music from wardogs2_audio.mp3 using STFT transfer function + Wiener mask."""
    n = min(len(audio_mix), len(music))
    a = audio_mix[:n]
    m = music[:n]

    win_len = 2048
    hop = 512
    window = np.hanning(win_len)

    silence_ranges = [
        (1.00, 1.25),
        (6.05, 7.25),
        (14.45, 15.65),
        (21.15, 23.00),
        (30.25, 31.15),
        (38.05, 38.65),
    ]
    num = np.zeros(win_len // 2 + 1, dtype=np.complex128)
    den = np.zeros(win_len // 2 + 1, dtype=np.float64)

    for t0, t1 in silence_ranges:
        for start in range(int(t0 * sr), int(t1 * sr) - win_len, hop):
            fa = rfft(a[start : start + win_len] * window)
            fm = rfft(m[start : start + win_len] * window)
            num += fa * np.conj(fm)
            den += np.abs(fm) ** 2

    H = num / (den + 1e-12)

    clean_v = np.zeros_like(a)
    norm_w = np.zeros_like(a)
    for start in range(0, n - win_len, hop):
        fa = rfft(a[start : start + win_len] * window)
        fm = rfft(m[start : start + win_len] * window)
        pm = fm * H
        diff_spec = fa - pm
        mag_d = np.abs(diff_spec)
        mag_m = np.abs(pm) * 0.20
        gain = np.clip((mag_d ** 2 - mag_m ** 2) / (mag_d ** 2 + 1e-12), 0.0, 1.0) ** 0.5
        cv = irfft(diff_spec * gain) * window
        clean_v[start : start + win_len] += cv
        norm_w[start : start + win_len] += window ** 2

    clean_v /= np.maximum(norm_w, 1e-8)
    return clean_v


def add_sfx_whoosh(buf: np.ndarray, t_sec: float, sr: int = 48000, vol: float = 0.16):
    dur = 0.26
    n = int(dur * sr)
    i0 = int(t_sec * sr)
    if i0 < 0 or i0 + n > len(buf):
        return
    t = np.linspace(0, dur, n, endpoint=False)
    env = np.sin(np.pi * t / dur) ** 1.5
    # Low-to-mid frequency sweep + subtle noise
    freq = np.linspace(90, 380, n)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    sig = (0.65 * np.sin(phase) + 0.35 * np.sin(phase * 0.5)) * env * vol
    buf[i0 : i0 + n] += sig.astype(np.float32)


def add_sfx_chime(buf: np.ndarray, t_sec: float, sr: int = 48000, vol: float = 0.15):
    dur = 0.24
    n = int(dur * sr)
    i0 = int(t_sec * sr)
    if i0 < 0 or i0 + n > len(buf):
        return
    t = np.linspace(0, dur, n, endpoint=False)
    env = np.exp(-t * 14.0) * np.minimum(1.0, t / 0.008)
    sig = (0.6 * np.sin(2 * np.pi * 880 * t) + 0.4 * np.sin(2 * np.pi * 1318.5 * t)) * env * vol
    buf[i0 : i0 + n] += sig.astype(np.float32)


def add_sfx_typing(buf: np.ndarray, t_start: float, t_end: float, n_clicks: int = 12, sr: int = 48000, vol: float = 0.09):
    times = np.linspace(t_start, t_end, n_clicks)
    for tc in times:
        dur = 0.018
        n = int(dur * sr)
        i0 = int(tc * sr)
        if 0 <= i0 and i0 + n <= len(buf):
            t = np.linspace(0, dur, n, endpoint=False)
            env = np.exp(-t * 220.0)
            click = (np.sin(2 * np.pi * 1450 * t) + 0.5 * np.sin(2 * np.pi * 2900 * t)) * env * vol
            buf[i0 : i0 + n] += click.astype(np.float32)


def build_audio_44s(orig_audio: np.ndarray, music: np.ndarray, sr: int = 48000) -> str:
    """Builds the enhanced 44.27s audio track (1:1 synced with wardogs2_audio.mp3 + subtle SFX & punchier intro beat)."""
    target_len = int(44.27 * sr)
    out = np.zeros(target_len, dtype=np.float32)
    n_copy = min(target_len, len(orig_audio))
    out[:n_copy] = orig_audio[:n_copy] * 1.04

    # Add subtle Phonk beat reinforcement in the first 17.5s so the Hook has rhythm right from 0.0s!
    # In wardogs_music.mp3, 18.0s..35.5s is the main beat section; we blend it softly at 8% during 0..17.5s
    beat_len = int(17.5 * sr)
    beat_src = music[int(18.0 * sr) : int(18.0 * sr) + beat_len]
    fade_env = np.ones(beat_len, dtype=np.float32) * 0.075
    fade_env[-int(1.0 * sr) :] *= np.linspace(1.0, 0.0, int(1.0 * sr))
    out[:beat_len] += beat_src * fade_env

    # Add crisp UI sound effects synced to visual transitions & actions
    for t_w in [0.02, 3.30, 6.50, 14.90, 21.60, 30.70, 33.15, 35.40, 37.50]:
        add_sfx_whoosh(out, t_w, sr=sr, vol=0.14)
    add_sfx_typing(out, 6.95, 8.65, n_clicks=14, sr=sr, vol=0.08)
    add_sfx_typing(out, 15.30, 16.25, n_clicks=9, sr=sr, vol=0.08)
    for t_c in [8.75, 16.45, 22.85, 25.25, 31.10, 38.00]:
        add_sfx_chime(out, t_c, sr=sr, vol=0.14)

    out = np.clip(out, -0.98, 0.98)
    wav_path = "/tmp/audio_44s_final.wav"
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((out * 32767).astype(np.int16).tobytes())
    return wav_path


def build_audio_viral_fast(clean_voice: np.ndarray, music: np.ndarray, sr: int = 48000):
    """
    Builds the tightened ~33.6s Viral Shorts audio track:
    - Eliminates the 1.25s silence at 0:00 (voice starts immediately at 0.08s!)
    - Tightens all 5 dead-air gaps between scenes from ~2.1s down to 0.30s!
    - Mixes over the punchy Phonk beat section of wardogs_music.mp3 with sidechain ducking!
    Returns (wav_path, scenes_timeline, total_duration)
    """
    # Original voice segments (start_s, end_s)
    orig_segs = [
        ("hook", 1.22, 6.00),     # dur = 4.78s
        ("step1", 8.00, 14.38),   # dur = 6.38s
        ("step2", 16.42, 21.00),  # dur = 4.58s
        ("step3", 23.18, 30.18),  # dur = 7.00s
        ("result", 32.12, 36.92), # dur = 4.80s
        ("outro", 38.68, 42.88),  # dur = 4.20s
    ]

    gap = 0.32
    cur_t = 0.08
    placed_segs = []
    scenes_timeline = []

    for idx, (name, s0, s1) in enumerate(orig_segs):
        dur = s1 - s0
        scene_start = 0.0 if idx == 0 else cur_t - gap * 0.5
        v_start = cur_t
        v_end = cur_t + dur
        scene_end = v_end + (gap * 0.5 if idx < len(orig_segs) - 1 else 0.35)
        placed_segs.append((name, s0, s1, v_start, v_end))
        scenes_timeline.append((name, scene_start, scene_end))
        cur_t = v_end + gap

    total_dur = scenes_timeline[-1][2]
    total_samples = int(total_dur * sr)
    voice_track = np.zeros(total_samples, dtype=np.float32)
    voice_env = np.zeros(total_samples, dtype=np.float32)

    fade_n = int(0.03 * sr)
    for name, s0, s1, v_start, v_end in placed_segs:
        seg = clean_voice[int(s0 * sr) : int(s1 * sr)].copy()
        if len(seg) > 2 * fade_n:
            seg[:fade_n] *= np.linspace(0.0, 1.0, fade_n)
            seg[-fade_n:] *= np.linspace(1.0, 0.0, fade_n)
        dst0 = int(v_start * sr)
        dst1 = min(total_samples, dst0 + len(seg))
        voice_track[dst0:dst1] += seg[: dst1 - dst0] * 1.18
        voice_env[dst0:dst1] = 1.0

    # Smooth voice envelope for sidechain ducking of the Phonk beat
    win_smooth = int(0.18 * sr)
    kernel = np.ones(win_smooth, dtype=np.float32) / win_smooth
    duck_env = np.convolve(voice_env, kernel, mode="same")
    # Music gain: 0.22 when voice is active, swells to 0.36 in transitions
    music_gain = 0.34 - 0.13 * duck_env

    # Start music right at 17.8s of wardogs_music.mp3 (where the Phonk beat drops!)
    m_start = int(17.8 * sr)
    music_seg = np.zeros(total_samples, dtype=np.float32)
    rem = len(music) - m_start
    if rem >= total_samples:
        music_seg[:] = music[m_start : m_start + total_samples]
    else:
        music_seg[:rem] = music[m_start:]
        music_seg[rem:] = music[int(18.0 * sr) : int(18.0 * sr) + (total_samples - rem)]

    out = voice_track + music_seg * music_gain

    # Add crisp UI sound effects synced to the new viral timeline
    for name, sc0, sc1 in scenes_timeline:
        add_sfx_whoosh(out, max(0.01, sc0), sr=sr, vol=0.15)
        if name == "hook":
            add_sfx_whoosh(out, sc0 + (sc1 - sc0) * 0.52, sr=sr, vol=0.13)
        elif name == "step1":
            add_sfx_typing(out, sc0 + 0.35, sc0 + 2.10, n_clicks=14, sr=sr, vol=0.08)
            add_sfx_chime(out, sc0 + 2.15, sr=sr, vol=0.14)
        elif name == "step2":
            add_sfx_typing(out, sc0 + 0.30, sc0 + 1.40, n_clicks=9, sr=sr, vol=0.08)
            add_sfx_chime(out, sc0 + 1.50, sr=sr, vol=0.14)
        elif name == "step3":
            add_sfx_chime(out, sc0 + 1.25, sr=sr, vol=0.15)
            add_sfx_chime(out, sc0 + 3.60, sr=sr, vol=0.14)
        elif name == "result":
            add_sfx_whoosh(out, sc0 + (sc1 - sc0) * 0.36, sr=sr, vol=0.13)
            add_sfx_whoosh(out, sc0 + (sc1 - sc0) * 0.70, sr=sr, vol=0.13)

    # Seamless loop audio fade at very end (last 60ms)
    loop_f = int(0.06 * sr)
    out[-loop_f:] *= np.linspace(1.0, 0.25, loop_f)
    out = np.clip(out, -0.98, 0.98)

    wav_path = "/tmp/audio_viral_fast.wav"
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes((out * 32767).astype(np.int16).tobytes())
    return wav_path, scenes_timeline, total_dur


def render_frame_for_timeline(bundle: AssetsBundle, t: float, scenes_timeline, total_dur: float) -> Image.Image:
    global_progress = clamp01(t / max(0.01, total_dur))
    for name, sc0, sc1 in scenes_timeline:
        if sc0 <= t <= sc1 or (name == scenes_timeline[-1][0] and t >= sc0):
            local_t = max(0.0, t - sc0)
            scene_dur = max(0.01, sc1 - sc0)
            if name == "hook":
                return render_scene_hook(bundle, local_t, scene_dur, global_progress)
            elif name == "step1":
                return render_scene_step1(bundle, local_t, scene_dur, global_progress)
            elif name == "step2":
                return render_scene_step2(bundle, local_t, scene_dur, global_progress)
            elif name == "step3":
                return render_scene_step3(bundle, local_t, scene_dur, global_progress)
            elif name == "result":
                return render_scene_result(bundle, local_t, scene_dur, global_progress)
            elif name == "outro":
                return render_scene_outro(bundle, local_t, scene_dur, global_progress)
    return render_scene_hook(bundle, 0.0, 5.0, 0.0)


def encode_video(bundle: AssetsBundle, scenes_timeline, total_dur: float, wav_path: str, out_mp4: str):
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    n_frames = int(round(total_dur * FPS))
    cmd = [
        ffmpeg_exe,
        "-hide_banner",
        "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}",
        "-r", str(FPS),
        "-i", "-",
        "-i", wav_path,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
        "-shortest",
        "-movflags", "+faststart",
        out_mp4,
    ]
    print(f"Encoding {out_mp4} ({n_frames} frames, {total_dur:.2f}s)...")
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    for f_idx in range(n_frames):
        t = f_idx / float(FPS)
        im = render_frame_for_timeline(bundle, t, scenes_timeline, total_dur)
        proc.stdin.write(im.tobytes())
        if (f_idx + 1) % 150 == 0 or f_idx == n_frames - 1:
            print(f"  Frame {f_idx + 1}/{n_frames} ({t:.1f}s)")
    proc.stdin.close()
    stderr_out = proc.stderr.read().decode("utf-8", errors="ignore")
    ret = proc.wait()
    if ret != 0:
        print("FFmpeg error:", stderr_out)
        raise RuntimeError(f"FFmpeg exited with code {ret}")
    print(f"Successfully generated {out_mp4} ({os.path.getsize(out_mp4) / 1024 / 1024:.2f} MB)")


def build_all_videos():
    bundle = AssetsBundle()
    print("Loading audio tracks...")
    orig_audio = load_wav_mono_48k("wardogs2_audio.mp3")
    music = load_wav_mono_48k("wardogs_music.mp3")
    clean_voice = extract_clean_voice_48k(orig_audio, music, sr=48000)

    # 1. Build 44.27s Original-Synced Version (wardogs_config_1080x1920.mp4)
    timeline_44s = [
        ("hook", 0.00, 6.50),
        ("step1", 6.50, 14.90),
        ("step2", 14.90, 21.60),
        ("step3", 21.60, 30.70),
        ("result", 30.70, 37.50),
        ("outro", 37.50, 44.27),
    ]
    wav_44s = build_audio_44s(orig_audio, music, sr=48000)
    encode_video(bundle, timeline_44s, 44.27, wav_44s, "wardogs_config_1080x1920.mp4")

    # 2. Build ~33.6s Fast-Cut Viral Shorts Version (wardogs_shorts_viral_1080x1920.mp4)
    wav_viral, timeline_viral, dur_viral = build_audio_viral_fast(clean_voice, music, sr=48000)
    print("Viral timeline:", [(n, round(s0, 2), round(s1, 2)) for n, s0, s1 in timeline_viral])
    encode_video(bundle, timeline_viral, dur_viral, wav_viral, "wardogs_shorts_viral_1080x1920.mp4")

    # Also copy the viral version to the upload-pack filename wardogs_otkluchenie_teney_konfig_1080x1920.mp4
    shutil.copy2("wardogs_shorts_viral_1080x1920.mp4", "wardogs_otkluchenie_teney_konfig_1080x1920.mp4")
    print("Copied viral Shorts video to wardogs_otkluchenie_teney_konfig_1080x1920.mp4")


if __name__ == "__main__":
    if "--build" in sys.argv:
        build_all_videos()
