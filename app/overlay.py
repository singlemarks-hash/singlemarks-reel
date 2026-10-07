"""고정 템플릿 텍스트를 Pillow로 투명 PNG에 그립니다.
ffmpeg의 drawtext 필터(freetype 빌드 필요)에 의존하지 않기 위한 방식입니다."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from . import config as C


def _draw_tracked(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
                  cx: float, y: float, tracking: int, word_gap: int):
    """글자 사이를 tracking px 만큼 띄워 가운데 정렬로, 검은 외곽선과 함께 그립니다."""
    widths = [word_gap if ch == " " else draw.textlength(ch, font=font) + tracking for ch in text]
    total = sum(widths) - (tracking if text and text[-1] != " " else 0)
    x = cx - total / 2
    for ch, wd in zip(text, widths):
        if ch != " ":
            draw.text((x, y), ch, font=font, fill=(255, 255, 255, 255),
                      stroke_width=C.SUBTITLE_STROKE, stroke_fill=(0, 0, 0, 230))
        x += wd


def _fit_font(path: Path, text: str, target_w: float) -> ImageFont.FreeTypeFont:
    probe = ImageFont.truetype(str(path), 100)
    w = probe.getlength(text)
    return ImageFont.truetype(str(path), max(10, int(100 * target_w / w)))


def build_overlay(out: Path, w: int = C.OUT_W, h: int = C.OUT_H,
                  title_font: Path | None = None) -> Path:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 타이틀: 가는 서명체, 화면 폭의 TITLE_WIDTH 만큼 차지하도록 크기 자동 조정
    title_font = _fit_font(title_font or C.TITLE_FONT, C.TITLE_TEXT, w * C.TITLE_WIDTH)
    bbox = d.textbbox((0, 0), C.TITLE_TEXT, font=title_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx, ty = (w - tw) / 2 - bbox[0], h * C.TITLE_Y - th / 2 - bbox[1]
    d.text((tx, ty), C.TITLE_TEXT, font=title_font, fill=(255, 255, 255, 255))

    # 서브타이틀: 흰 글씨 + 검은 외곽선, 자간 넓게
    sub_font = ImageFont.truetype(str(C.SUBTITLE_FONT), C.SUBTITLE_SIZE)
    sb = sub_font.getbbox("매일밤")
    sh = sb[3] - sb[1]
    sy = h * C.SUBTITLE_Y - sh / 2 - sb[1]
    _draw_tracked(d, C.SUBTITLE_TEXT, sub_font, w / 2, sy,
                  tracking=int(C.SUBTITLE_SIZE * C.SUBTITLE_TRACKING),
                  word_gap=int(C.SUBTITLE_SIZE * C.SUBTITLE_WORD_GAP))

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out
