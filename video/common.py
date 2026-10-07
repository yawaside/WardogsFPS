# -*- coding: utf-8 -*-
"""Общие помощники рендера видео №2: смешивание слоёв, свечение, строки настроек."""
import numpy as np
from render import W, H, MARGIN_L, MARGIN_R, COL, LABEL, mask, colorize, solid, paste

CW = MARGIN_R - MARGIN_L


def blend(frame, rgb, a, x, y, alpha=1.0, wipe=None, grow=None):
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


def title_size(text, maxw):
    s = 100
    while s > 54:
        if mask(text, s, 900, -2.0).width <= maxw:
            return s
        s -= 2
    return s


def make_rows(rows, pitch, lsize, vsize, cw=CW):
    out = []
    for (lab, val, cc) in rows:
        rgb = np.zeros((pitch, cw, 3), np.float32)
        a = np.zeros((pitch, cw), np.float32)
        lm = mask(lab, lsize, 600, 0.6)
        l_rgb, l_a = colorize(lm, LABEL)
        vm = mask(val, vsize, 800, 0.2)
        v_rgb, v_a = colorize(vm, COL[cc])
        y = max(0, (pitch - lm.height) // 2)
        paste(rgb, a, l_rgb, l_a, 0, y)
        paste(rgb, a, v_rgb, v_a, cw - vm.width, y)
        out.append(dict(kind='fade_slide', rgb=rgb, a=a, x=MARGIN_L, y=0, h=pitch, dx=-38))
        d_rgb, d_a = solid(cw, 2, (34, 35, 38), 255)
        out.append(dict(kind='divider', rgb=d_rgb, a=d_a, x=MARGIN_L, y=0, h=2, dx=0))
    return out

