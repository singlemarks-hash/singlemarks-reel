"""ffmpeg로 9:16 릴스 클립을 렌더링하고 고정 템플릿 텍스트를 올립니다."""
from __future__ import annotations

import subprocess
from pathlib import Path

from . import config as C


def _esc_path(p: Path) -> str:
    # drawtext 옵션 안에서 ':' 와 '\' 는 이스케이프 필요
    return str(p).replace("\\", "\\\\").replace(":", "\\:")


def _tracked(text: str) -> str:
    """레퍼런스 디자인처럼 글자 사이를 넓게 벌립니다."""
    words = text.split(" ")
    return (C.SUBTITLE_TRACKING * 3).join(C.SUBTITLE_TRACKING.join(w) for w in words)


def build_filter(src_w: int, src_h: int, focus: float, title_file: Path,
                 subtitle_file: Path, clip_sec: float) -> str:
    focus = min(1.0, max(0.0, focus))
    fade = C.FADE_SECONDS
    fade_out_start = max(0.0, clip_sec - fade)

    crop = (
        f"crop=w='min(iw,ih*9/16)':h='min(ih,iw*16/9)'"
        f":x='(iw-ow)*{focus}':y='(ih-oh)/2'"
    )
    vf = [
        "format=yuv420p",      # 10비트 HEVC(아이폰) 등도 8비트로 통일한 뒤 필터 적용
        crop,
        f"scale={C.OUT_W}:{C.OUT_H}:flags=lanczos",
        "setsar=1",
        f"fps={C.FPS}",
        f"fade=t=in:st=0:d={fade},fade=t=out:st={fade_out_start}:d={fade}",
        # 상단 텍스트 가독성을 위한 아주 옅은 비네트
        "vignette=angle=PI/5:mode=forward",
        (
            f"drawtext=fontfile='{_esc_path(C.TITLE_FONT)}'"
            f":textfile='{_esc_path(title_file)}'"
            f":fontsize={C.TITLE_SIZE}:fontcolor=white"
            f":x=(w-text_w)/2:y=h*{C.TITLE_Y}-text_h/2"
            f":shadowcolor=black@0.45:shadowx=2:shadowy=3"
            f":alpha='if(lt(t,1.2),t/1.2,1)'"
        ),
        (
            f"drawtext=fontfile='{_esc_path(C.SUBTITLE_FONT)}'"
            f":textfile='{_esc_path(subtitle_file)}'"
            f":fontsize={C.SUBTITLE_SIZE}:fontcolor=white"
            f":x=(w-text_w)/2:y=h*{C.SUBTITLE_Y}-text_h/2"
            f":shadowcolor=black@0.5:shadowx=1:shadowy=2"
            f":alpha='if(lt(t,1.6),max(0,(t-0.4)/1.2),1)'"
        ),
    ]
    return ",".join(vf)


def render_clip(src: str, start: float, end: float, out: Path, focus: float = 0.5,
                src_w: int = 1920, src_h: int = 1080) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    clip_sec = end - start
    title_file = out.parent / "_title.txt"
    subtitle_file = out.parent / "_subtitle.txt"
    title_file.write_text(C.TITLE_TEXT, encoding="utf-8")
    subtitle_file.write_text(_tracked(C.SUBTITLE_TEXT), encoding="utf-8")

    fade = C.FADE_SECONDS
    af = (
        f"afade=t=in:st=0:d={fade},afade=t=out:st={max(0, clip_sec - fade)}:d={fade},"
        "loudnorm=I=-14:TP=-1.5:LRA=11"
    )
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-ss", f"{start:.3f}", "-t", f"{clip_sec:.3f}", "-i", src,
        "-vf", build_filter(src_w, src_h, focus, title_file, subtitle_file, clip_sec),
        "-af", af,
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
        for f in ("drawtext", "vignette", "loudnorm", "crop", "fade"):
            if f" {f} " not in filters:
                problems.append(f"ffmpeg에 '{f}' 필터가 없습니다 (drawtext는 freetype 포함 빌드 필요)")
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
