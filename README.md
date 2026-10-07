# WardogsFPS

Ролики-ガイド по конфигу WARDOGS (War Dogs) в формате вертикальных Shorts (1080x1920).

## Видео

- `wardogs_config_1080x1920.mp4` — оригинальный ролик (44 сек), гайд «отключение теней через конфиг». Пакет для загрузки: `wardogs_config_upload_pack.md`. Инструменты: `video/` (build2.py, render.py, mix2.py, ...).
- `wardogs_otkluchenie_teney_konfig_v3_1080x1920.mp4` — **v3, улучшенный ремейк** (44.9 сек): усиленный хук (интрига → решение за 1.5с), кинетические анимации, Ken Burns на игровых кадрах, анимированный прицел, кроссфейды, частицы, зерно, синтезированные SFX. Пакет для загрузки: `wardogs_config_upload_pack_v3.md`. Инструменты: `video/v3/`.

Оба ролика используют одну и ту же озвучку (`wardogs2_audio.mp3`) и музыку (`wardogs_music.mp3`).

## Сборка v3 (видео/v3/)

Требования: Python 3.11, `pip install numpy pillow imageio-ffmpeg` (ffmpeg идёт в комплекте).
Шрифты и AI-фоны уже в `assets/`.

```bash
cd video/v3
python build3.py          # рендер видео (без звука) -> master3_mute.mp4 + timeline3.json
python build3.py preview  # превью-кадры сцен (проверка вёрстки)
python mix3.py            # автогенерация SFX/конвертация аудио + финальный микс
                          # -> ../wardogs_otkluchenie_teney_konfig_v3_1080x1920.mp4
```

Пайплайн: `render3.py` (база) → `game3.py` (игровые кадры «с/без теней») → `scenes3.py` (6 сцен под тайминги озвучки) → `build3.py` (рендер) → `sfx3.py` (синтез SFX) → `mix3.py` (микс: озвучка + музыка с дакингом + SFX).
