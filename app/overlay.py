"""고정 템플릿 텍스트를 Pillow로 투명 PNG에 그립니다.
ffmpeg의 drawtext 필터(freetype 빌드 필요)에 의존하지 않기 위한 방식입니다."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from . import config as C


def _draw_tracked(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
                  cx: float, y: float, fill, tracking: int, word_gap: int):
    """글자 사이를 tracking px 만큼 띄워 가운데 정렬로 그립니다."""
    widths = []
    for ch in text:
        if ch == " ":
            widths.append(word_gap)
        else:
            widths.append(draw.textlength(ch, font=font) + tracking)
    total = sum(widths) - (tracking if text and text[-1] != " " else 0)
    x = cx - total / 2
    for ch, w in zip(text, widths):
        if ch != " ":
            draw.text((x, y), ch, font=font, fill=fill)
        x += w


def build_overlay(out: Path, w: int = C.OUT_W, h: int = C.OUT_H) -> Path:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    ds = ImageDraw.Draw(shadow)

    title_font = ImageFont.truetype(str(C.TITLE_FONT), C.TITLE_SIZE)
    sub_font = ImageFont.truetype(str(C.SUBTITLE_FONT), C.SUBTITLE_SIZE)

    # 타이틀 (필기체, 가운데)
    tw = d.textlength(C.TITLE_TEXT, font=title_font)
    bbox = title_font.getbbox(C.TITLE_TEXT)
    th = bbox[3] - bbox[1]
    tx, ty = (w - tw) / 2, h * C.TITLE_Y - th / 2 - bbox[1]
    ds.text((tx + 2, ty + 3), C.TITLE_TEXT, font=title_font, fill=(0, 0, 0, 150))
    d.text((tx, ty), C.TITLE_TEXT, font=title_font, fill=(255, 255, 255, 255))

    # 서브타이틀 (한글, 자간 넓게)
    sb = sub_font.getbbox("매")
    sh = sb[3] - sb[1]
    sy = h * C.SUBTITLE_Y - sh / 2 - sb[1]
    tracking = int(C.SUBTITLE_SIZE * 0.35)
    word_gap = int(C.SUBTITLE_SIZE * 0.9)
    _draw_tracked(ds, C.SUBTITLE_TEXT, sub_font, w / 2 + 1, sy + 2, (0, 0, 0, 160), tracking, word_gap)
    _draw_tracked(d, C.SUBTITLE_TEXT, sub_font, w / 2, sy, (255, 255, 255, 255), tracking, word_gap)

    shadow = shadow.filter(ImageFilter.GaussianBlur(3))
    final = Image.alpha_composite(shadow, img)
    out.parent.mkdir(parents=True, exist_ok=True)
    final.save(out)
    return out
