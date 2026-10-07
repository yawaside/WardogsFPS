#!/usr/bin/env python3
"""WARDOGS / NVIDIA Reflex short. Build: ../.venv/bin/python Reflex/build.py

The menu image is a sourced in-game screenshot, not an invented UI. FPS changes
are the creator's estimates, not benchmark results or a universal guarantee.
"""
from pathlib import Path
import math
import subprocess
import wave

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TMP = HERE / 'frames'
TMP.mkdir(exist_ok=True)
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H = 1080, 1920
INK = '#080b12'
WHITE = '#f5f4f0'
MUTED = '#a2aabb'
GOLD = '#ffc64a'
RED = '#fb594e'
TEAL = '#66e5bc'
FONT = ROOT / 'assets/fonts/Montserrat.ttf'
MONO = ROOT / 'assets/fonts/JetBrainsMono-Bold.ttf'
DURS = [4.0, 5.5, 4.5, 5.0, 5.2, 9.0]  # 33.2s, 0.32s crossfades
XFADE = .32
OUT = HERE / 'wardogs_reflex_1080x1920.mp4'


def font(size, weight=700, mono=False):
    f = ImageFont.truetype(str(MONO if mono else FONT), size)
    if not mono:
        try: f.set_variation_by_axes([weight])
        except (AttributeError, ValueError, OSError): pass
    return f


def txt(im, text, xy, size=40, fill=WHITE, weight=700, mono=False, spacing=0):
    d = ImageDraw.Draw(im)
    f = font(size, weight, mono)
    x, y = xy
    if spacing:
        for c in text:
            d.text((x, y), c, font=f, fill=fill, stroke_width=0)
            x += d.textlength(c, font=f) + spacing
    else:
        d.text((x, y), text, font=f, fill=fill, stroke_width=0)
    return x if spacing else x + d.textlength(text, font=f)


def center(im, text, y, size, fill=WHITE, weight=700):
    f = font(size, weight)
    x = int((W - ImageDraw.Draw(im).textlength(text, font=f)) / 2)
    txt(im, text, (x, y), size, fill, weight)


def rr(im, box, fill, radius=22, outline=None, width=2):
    ImageDraw.Draw(im).rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def label(im, text, x, y, color=GOLD):
    txt(im, text, (x, y), 26, color, mono=True, spacing=2)


def base(scene, tint=(255, 160, 25)):
    """Subtle blurred city, tonal vignette, technical grid, consistent chrome."""
    im = Image.new('RGB', (W, H), INK)
    bg = Image.open(ROOT / 'assets/refs/bg_city.jpg').convert('RGB')
    scale = max(W / bg.width, H / bg.height)
    bg = bg.resize((int(bg.width * scale), int(bg.height * scale)), Image.Resampling.LANCZOS)
    bg = bg.crop(((bg.width-W)//2, (bg.height-H)//2, (bg.width+W)//2, (bg.height+H)//2))
    bg = bg.filter(ImageFilter.GaussianBlur(34))
    im = Image.blend(im, bg, 0.13)
    a = np.asarray(im, dtype=np.float32).copy()
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    glow = np.exp(-((xx-860)**2/(600**2)+(yy-590)**2/(730**2))*2.0)*.105
    a += glow[...,None] * np.asarray(tint, dtype=np.float32)
    dark = np.clip(1 - .18*((xx-W/2)/(W/2))**2 - .14*((yy-H/2)/(H/2))**2, .6, 1)
    a *= dark[...,None]
    im = Image.fromarray(np.clip(a, 0, 255).astype('uint8'))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 90): d.line((x, 225, x, 1660), fill='#1b2129', width=1)
    for y in range(250, 1670, 90): d.line((0, y, W, y), fill='#1b2129', width=1)
    d.rectangle((0, 0, W, 205), fill='#0a0d14')
    d.rectangle((0, 1670, W, H), fill='#090c12')
    d.line((90, 209, 990, 209), fill=GOLD, width=2)
    d.line((90, 1655, 990, 1655), fill='#35404b', width=2)
    d.rectangle((90, 55, 106, 120), fill=GOLD)
    txt(im, 'WARDOGS', (129, 50), 40, WHITE, 800)
    label(im, 'FPS / НАСТРОЙКИ', 132, 111, MUTED)
    txt(im, f'{scene+1:02d} / 06', (850, 64), 32, GOLD, mono=True)
    gap = 11
    segw = (900 - 5*gap)//6
    for i in range(6):
        d.rounded_rectangle((90+i*(segw+gap), 177, 90+i*(segw+gap)+segw, 187),
                            radius=5, fill=GOLD if i <= scene else '#39404b')
    label(im, 'WARDOGS   /   NVIDIA REFLEX', 90, 1721, GOLD)
    txt(im, 'Результат зависит от системы и сцены', (90, 1776), 25, MUTED, 500)
    return im


def shadow_panel(im, rect, color='#141b26', outline='#46515d', radius=27):
    x0,y0,x1,y1 = rect
    rr(im, (x0+9,y0+14,x1+9,y1+14), '#08090b', radius)
    rr(im, rect, color, radius, outline, 2)


def screenshot(im, xy=(120, 455), width=840):
    src = Image.open(HERE / 'wardogs_video_settings_source.webp').convert('RGB')
    src = ImageEnhance.Brightness(src).enhance(1.17)
    src = ImageEnhance.Contrast(src).enhance(1.20)
    src = src.filter(ImageFilter.UnsharpMask(radius=1.1, percent=165))
    h = round(src.height * width / src.width)
    src = src.resize((width, h), Image.Resampling.LANCZOS)
    x,y = xy
    shadow_panel(im, (x-13,y-13,x+width+13,y+h+13), '#0c0e12', '#5f6872', 14)
    im.paste(src, (x,y))
    # On-screen annotation, not a change to the source screenshot.
    scale = width / 768
    draw = ImageDraw.Draw(im)
    row = (x+76*scale, y+479*scale, x+756*scale, y+536*scale)
    draw.rounded_rectangle(row, radius=8, outline=GOLD, width=5)
    return tuple(map(int, row))


def scene0():
    im = base(0, (250,65,20))
    label(im, '01  /  ХУК', 90, 271)
    txt(im, 'НАСТРОЙКА,', (86, 354), 93, WHITE, 800)
    txt(im, 'КОТОРАЯ', (86, 469), 93, WHITE, 800)
    txt(im, 'УБИВАЕТ', (86, 584), 102, GOLD, 800)
    txt(im, 'ВАШ FPS', (86, 708), 105, WHITE, 800)
    shadow_panel(im, (90, 950, 990, 1412), '#171a22', '#744440')
    label(im, 'NVIDIA REFLEX / BOOST', 133, 1001, RED)
    txt(im, '−40+', (124, 1072), 195, RED, 800)
    txt(im, 'FPS', (680, 1185), 74, WHITE, 800)
    ImageDraw.Draw(im).line((133, 1316, 942, 1316), fill='#62423c', width=2)
    txt(im, 'ПРОВЕРЬ НА СВОЁМ ПК', (134, 1341), 37, WHITE, 700)
    label(im, 'ОЦЕНКА / НЕ ГАРАНТИЯ', 90, 1495, MUTED)
    return im


def scene1():
    im = base(1)
    label(im, '02  /  ГДЕ НАЙТИ', 90, 260)
    txt(im, 'НАСТРОЙКИ', (84, 315), 80, WHITE, 800)
    txt(im, '→ ВИДЕО', (84, 412), 76, GOLD, 800)
    row = screenshot(im, (120, 552), 840)
    # Small indicator points to the actual Reflex row.
    d = ImageDraw.Draw(im)
    d.line((115, row[1]+24, row[0]-20, row[1]+24), fill=GOLD, width=6)
    rr(im, (90, 1571, 990, 1631), '#212129', 12)
    txt(im, 'РЕАЛЬНЫЙ СКРИН МЕНЮ ИГРЫ', (136, 1579), 31, GOLD, 700)
    return im


def scene2():
    im = base(2)
    label(im, '03  /  НУЖНАЯ СТРОКА', 90, 270)
    txt(im, 'NVIDIA', (85, 344), 103, WHITE, 800)
    txt(im, 'REFLEX', (85, 463), 121, GOLD, 800)
    # Unmodified crop from the real screenshot, enlarged for legibility.
    src = Image.open(HERE/'wardogs_video_settings_source.webp').convert('RGB')
    crop = src.crop((77, 470, 765, 548))
    crop = ImageEnhance.Brightness(crop).enhance(1.4)
    crop = ImageEnhance.Contrast(crop).enhance(1.3)
    crop = crop.resize((840, 190), Image.Resampling.LANCZOS)
    shadow_panel(im, (90, 665, 990, 955), '#11151d', '#9c7443')
    label(im, 'ФРАГМЕНТ СКРИНШОТА', 122, 693, MUTED)
    im.paste(crop, (120, 751))
    ImageDraw.Draw(im).rounded_rectangle((116,747,964,947), radius=8, outline=GOLD, width=4)
    label(im, 'СРАВНИ ТРИ РЕЖИМА', 90, 1030)
    for n, val, col in [(0,'ВЫКЛЮЧЕНО',MUTED),(1,'ВКЛЮЧЕНО',GOLD),(2,'ВКЛ. + УСКОРЕНИЕ',RED)]:
        y=1101+n*153
        shadow_panel(im,(90,y,990,y+128),'#171d27','#394655')
        rr(im,(116,y+26,190,y+101),col,15)
        txt(im,str(n+1),(139,y+34),39,INK,800)
        txt(im,val,(216,y+32),42,WHITE,700)
    return im


def scene3():
    im=base(3,(244,166,42))
    label(im, '04  /  РЕЖИМ', 90, 263)
    txt(im,'ВКЛЮЧЕНО', (85,345), 99, WHITE,800)
    shadow_panel(im,(90,570,990,1195),'#1b1d23','#766132')
    label(im,'ВОЗМОЖНАЯ ПРОСАДКА',138,628,GOLD)
    txt(im,'−5', (122,747), 174,GOLD,800)
    txt(im,'…', (429,772), 124,WHITE,800)
    txt(im,'−15', (560,747), 168,GOLD,800)
    ImageDraw.Draw(im).line((132,981,946,981),fill='#685c3f',width=2)
    txt(im,'FPS', (139,1005), 88, WHITE,800)
    label(im,'ПО НАБЛЮДЕНИЯМ АВТОРА',90,1324,MUTED)
    txt(im,'На разных ПК эффект', (90,1380), 48,WHITE,600)
    txt(im,'может отличаться.', (90,1455), 48,WHITE,600)
    return im


def scene4():
    im=base(4,(210,35,40))
    label(im,'05  /  РЕЖИМ',90,260,RED)
    txt(im,'ВКЛЮЧЕНО', (84,332),88,WHITE,800)
    txt(im,'+ УСКОРЕНИЕ',(84,441),77,RED,800)
    shadow_panel(im,(90,624,990,1198),'#25191e','#a74342')
    label(im,'ВОЗМОЖНАЯ ПРОСАДКА',132,672,RED)
    txt(im,'−40', (119,772), 215,RED,800)
    txt(im,'FPS', (702,931), 73,WHITE,800)
    txt(im,'И ВЫШЕ', (129,1049), 78,WHITE,800)
    txt(im,'Зависит от системы:',(90,1335),46,WHITE,600)
    txt(im,'проверь в своей игре.',(90,1415),46,WHITE,600)
    return im


def scene5():
    im=base(5,(32,160,125))
    label(im,'06  /  ПРОВЕРКА',90,261,TEAL)
    txt(im,'НЕ ВЫКЛЮЧАЙ',(84,339),78,WHITE,800)
    txt(im,'ВСЛЕПУЮ',(84,438),92,TEAL,800)
    rr(im,(90,603,990,689),'#183d3b',16,TEAL,2)
    txt(im,'REFLEX СНИЖАЕТ ЗАДЕРЖКУ', (116,623),35,TEAL,700)
    label(im,'ОДНА КАРТА · ОДНИ НАСТРОЙКИ',90,789,GOLD)
    for i,(text,col) in enumerate([('01   ВЫКЛЮЧЕНО',MUTED),('02   ВКЛЮЧЕНО',GOLD),('03   ВКЛ. + УСКОРЕНИЕ',RED)]):
        y=875+i*148
        shadow_panel(im,(90,y,990,y+117),'#181e28','#3b4652')
        rr(im,(90,y,103,y+117),col,5)
        txt(im,text,(126,y+31),42,WHITE,700)
    txt(im,'Сравни FPS и отклик', (90,1377),53,WHITE,700)
    rr(im,(90,1494,990,1618),'#f8bc49',23)
    center(im,'СОХРАНИ И ПРОВЕРЬ',1518,46,INK,800)
    return im


def sfx():
    """Short subdued tonal transients at scene cuts; deterministic; no extra assets."""
    sr=48000
    seconds=sum(DURS)-XFADE*(len(DURS)-1)
    snd=np.zeros(int(sr*(seconds+.15)),dtype=np.float32)
    start=0
    for i,d in enumerate(DURS[:-1]):
        start += d if i==0 else d-XFADE
        t0=start-XFADE
        n=int(.18*sr)
        t=np.arange(n,dtype=np.float32)/sr
        wavelet=(np.sin(2*np.pi*(920-600*t/.18)*t)*.07 + np.sin(2*np.pi*125*t)*.034)
        env=np.sin(np.pi*np.arange(n)/n)**1.5
        snd[int(t0*sr):int(t0*sr)+n]+=wavelet*env
    path=TMP/'cuts.wav'
    with wave.open(str(path),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(snd,-1,1)*32767).astype('<i2').tobytes())
    return path


def run():
    funcs=[scene0,scene1,scene2,scene3,scene4,scene5]
    for i,fn in enumerate(funcs):
        fn().save(TMP/f'{i:02}.png',optimize=True)
        print(f'Scene {i+1}/6 saved',flush=True)
    cmd=[FF,'-y','-hide_banner','-loglevel','error']
    for i,d in enumerate(DURS):
        cmd += ['-loop','1','-framerate','30','-t',str(d),'-i',str(TMP/f'{i:02}.png')]
    chains=[]
    for i in range(6):
        chains.append(f'[{i}:v]format=yuv420p,setsar=1[v{i}]')
    prev='v0'
    offset=0
    for i in range(1,6):
        offset+=DURS[i-1] if i==1 else DURS[i-1]-XFADE
        offset-= XFADE if i==1 else 0
        chains.append(f'[{prev}][v{i}]xfade=transition=fade:duration={XFADE}:offset={offset:.3f}[x{i}]')
        prev=f'x{i}'
    cmd+=['-filter_complex',';'.join(chains),'-map',f'[{prev}]',
          '-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p',
          '-r','30','-movflags','+faststart',str(TMP/'silent.mp4')]
    print('Encoding video...',flush=True)
    subprocess.run(cmd,check=True)
    print('Mixing soundtrack...',flush=True)
    # Apply the same broad processing approach as previous video's narration.
    # The voice is an APPROXIMATION, not an exact clone of the old speaker.
    dur=sum(DURS)-XFADE*5
    audio=(
        '[1:a]aresample=48000,acompressor=threshold=-19dB:ratio=3:attack=6:release=140,'
        'loudnorm=I=-16:TP=-1.5:LRA=9,volume=1.15,adelay=850|850[vo];'
        '[2:a]aresample=48000,volume=0.13,atrim=duration='+str(dur)+',afade=t=out:st='+str(dur-1.3)+':d=1.3[music];'
        '[3:a]volume=0.6[fx];'
        '[vo][music][fx]amix=inputs=3:duration=longest:normalize=0,'
        'alimiter=limit=0.92,atrim=duration='+str(dur)+'[mixed]'
    )
    subprocess.run([FF,'-y','-hide_banner','-loglevel','error',
                    '-i',str(TMP/'silent.mp4'),'-i',str(HERE/'voice_approx.mp3'),
                    '-i',str(ROOT/'wardogs_music.mp3'),'-i',str(sfx()),
                    '-filter_complex',audio,'-map','0:v:0','-map','[mixed]',
                    '-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000',
                    '-movflags','+faststart','-t',str(dur),str(OUT)],check=True)
    print('Finished:',OUT,flush=True)


if __name__=='__main__':
    run()
