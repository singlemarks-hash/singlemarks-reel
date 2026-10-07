"""ffmpeg로 9:16 릴스 클립을 렌더링하고 고정 템플릿 텍스트를 올립니다."""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import config as C
from .overlay import build_overlay


def build_filter(focus: float, clip_sec: float, has_vignette: bool = True) -> str:
    """[0:v]=원본, [1:v]=텍스트 오버레이 PNG. drawtext 없이 overlay 필터만 사용."""
    focus = min(1.0, max(0.0, focus))
    crop = (
        f"crop=w='min(iw,ih*9/16)':h='min(ih,iw*16/9)'"
        f":x='(iw-ow)*{focus}':y='(ih-oh)/2'"
    )
    base = [
        "format=yuv420p",      # 10비트 HEVC(아이폰) 등도 8비트로 통일한 뒤 필터 적용
        crop,
        f"scale={C.OUT_W}:{C.OUT_H}:flags=lanczos",
        "setsar=1",
        f"fps={C.FPS}",
    ]
    if has_vignette:
        base.append("vignette=angle=PI/5:mode=forward")   # 상단 텍스트 가독성을 위한 옅은 비네트
    return (
        f"[0:v]{','.join(base)}[base];"
        f"[1:v]format=rgba[txt];"
        f"[base][txt]overlay=0:0:format=auto:shortest=1,format=yuv420p[v]"
    )


_HAS_VIGNETTE: bool | None = None


def _has_vignette() -> bool:
    global _HAS_VIGNETTE
    if _HAS_VIGNETTE is None:
        out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True,
                             text=True).stdout
        _HAS_VIGNETTE = " vignette " in out
    return _HAS_VIGNETTE


def resolve_title_font(name: str | None) -> Path:
    """UI에서 넘어온 파일명을 app/fonts 안의 경로로 안전하게 변환."""
    if name:
        cand = C.FONT_DIR / Path(name).name
        if cand.exists() and cand.suffix.lower() in (".ttf", ".otf"):
            return cand
    return C.TITLE_FONT


def render_clip(src: str, start: float, end: float, out: Path, focus: float = 0.5,
                src_w: int = 1920, src_h: int = 1080, title_font: str | None = None) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    clip_sec = end - start
    font = resolve_title_font(title_font)
    overlay_png = out.parent / f"_overlay_{font.stem}.png"
    if not overlay_png.exists():
        build_overlay(overlay_png, title_font=font)

    af = "loudnorm=I=-14:TP=-1.5:LRA=11"
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{start:.3f}", "-t", f"{clip_sec:.3f}", "-i", src,
        "-loop", "1", "-framerate", str(C.FPS), "-i", str(overlay_png),
        "-filter_complex", build_filter(focus, clip_sec, _has_vignette()),
        "-map", "[v]", "-map", "0:a:0",
        "-af", af,
        "-t", f"{clip_sec:.3f}",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        str(out),
    ]
    _run(cmd)
    return out


class RenderError(RuntimeError):
    pass


def _run(cmd: list[str]):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or "").strip()
        tail = "\n".join(err.splitlines()[-12:])
        raise RenderError(f"ffmpeg 종료 코드 {proc.returncode}\n{tail}")


def check_ffmpeg() -> list[str]:
    """필요한 필터/인코더가 있는지 확인하고 문제 목록을 돌려줍니다 (서버 시작 시 호출)."""
    problems = []
    try:
        filters = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True,
                                 text=True).stdout
        for f in ("overlay", "loudnorm", "crop", "scale", "fade"):
            if f" {f} " not in filters:
                problems.append(f"ffmpeg에 '{f}' 필터가 없습니다")
        encoders = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True,
                                  text=True).stdout
        if "libx264" not in encoders:
            problems.append("ffmpeg에 libx264 인코더가 없습니다")
        if " aac " not in encoders:
            problems.append("ffmpeg에 aac 인코더가 없습니다")
    except FileNotFoundError:
        problems.append("ffmpeg를 찾을 수 없습니다. 설치 후 PATH에 추가해 주세요 (brew install ffmpeg)")
    return problems


def thumbnail(video: Path, out: Path, at: float = 2.0) -> Path:
    _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at}", "-i", str(video),
          "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "4", str(out)])
    return out
