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
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out


def thumbnail(video: Path, out: Path, at: float = 2.0) -> Path:
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-ss", f"{at}", "-i", str(video),
         "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "4", str(out)],
        check=True, capture_output=True,
    )
    return out
