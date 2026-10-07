"""업로드 → 하이라이트 분석 → 렌더 → 캡션. 잡 상태는 jobs/<id>/status.json 에 기록."""
from __future__ import annotations

import json
import shutil
import subprocess
import time
import traceback
import uuid
from pathlib import Path

from . import config as C
from .caption import build_caption
from .highlight import find_highlights, probe
from .render import render_clip, thumbnail


def _errmsg(e: Exception) -> str:
    if isinstance(e, subprocess.CalledProcessError):
        tail = "\n".join((e.stderr or "").strip().splitlines()[-12:]) if isinstance(e.stderr, str) else ""
        return f"ffmpeg 종료 코드 {e.returncode}\n{tail}"
    if isinstance(e, (RuntimeError, ValueError)):
        return str(e)
    return f"{type(e).__name__}: {e}\n{traceback.format_exc()[-800:]}"


class Job:
    def __init__(self, job_id: str | None = None):
        self.id = job_id or uuid.uuid4().hex[:12]
        self.dir = C.JOBS_DIR / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
        if job_id and self.status_file.exists():
            self.state = json.loads(self.status_file.read_text(encoding="utf-8"))
            return
        self.state = {
            "id": self.id, "status": "queued", "stage": "대기 중",
            "progress": 0, "clips": [], "caption": "", "error": None,
            "created": time.time(),
        }
        self.save()

    @property
    def status_file(self) -> Path:
        return self.dir / "status.json"

    def save(self):
        self.status_file.write_text(json.dumps(self.state, ensure_ascii=False, indent=1),
                                    encoding="utf-8")

    def update(self, **kw):
        self.state.update(kw)
        self.save()

    @staticmethod
    def load(job_id: str) -> dict | None:
        f = C.JOBS_DIR / job_id / "status.json"
        if not f.exists():
            return None
        return json.loads(f.read_text(encoding="utf-8"))


def analyze_job(job: Job, src: Path, clip_sec: float = C.CLIP_SECONDS,
                count: int = C.CLIP_COUNT):
    """1단계: 하이라이트 후보만 찾고 사용자의 확인을 기다립니다."""
    try:
        job.update(status="analyzing", stage="영상 정보 확인 중", progress=3)
        info = probe(str(src))
        job.update(source={**info, "url": f"/jobs/{job.id}/{src.name}", "file": src.name})

        def prog(msg):
            job.update(stage=msg, progress=max(job.state["progress"], 8))

        segs, curve = find_highlights(str(src), clip_sec=clip_sec, count=count,
                                      progress=prog, return_curve=True)
        job.update(status="ready", stage="구간을 확인하고 렌더링을 시작하세요", progress=20,
                   segments=[s.to_dict() for s in segs], curve=curve,
                   clip_seconds=clip_sec)
    except Exception as e:  # noqa: BLE001
        job.update(status="error", stage="오류", error=_errmsg(e))


def render_job(job: Job, segments: list[dict], artist_name: str, artist_handle: str,
               schedule: str, focus: float = 0.5, title_font: str | None = None):
    """2단계: 확정된 구간으로 릴스를 렌더링합니다. 원본은 재조정을 위해 보관합니다."""
    try:
        src = job.dir / job.state["source"]["file"]
        info = job.state["source"]
        job.update(status="rendering", clips=[], caption="", progress=25,
                   segments=segments, artist={"name": artist_name, "handle": artist_handle},
                   title_font=title_font)
        for old in job.dir.glob("reel_*"):
            old.unlink()

        clips = []
        for i, s in enumerate(segments, 1):
            job.update(stage=f"릴스 {i}/{len(segments)} 렌더링 중 ({s['start']:.0f}s~{s['end']:.0f}s)",
                       progress=25 + int(70 * (i - 1) / len(segments)))
            out = job.dir / f"reel_{i}.mp4"
            render_clip(str(src), s["start"], s["end"], out, focus=focus,
                        src_w=info["width"], src_h=info["height"], title_font=title_font,
                        hdr=bool(info.get("hdr")), src_fps=info.get("fps"))
            thumb = job.dir / f"reel_{i}.jpg"
            thumbnail(out, thumb)
            clips.append({
                "index": i, "start": s["start"], "end": s["end"],
                "video": f"/jobs/{job.id}/{out.name}?v={int(time.time())}",
                "thumb": f"/jobs/{job.id}/{thumb.name}?v={int(time.time())}",
            })
            job.update(clips=clips)

        caption = build_caption(artist_name, artist_handle, schedule)
        (job.dir / "caption.txt").write_text(caption, encoding="utf-8")
        job.update(status="done", stage="완료", progress=100, caption=caption)
    except Exception as e:  # noqa: BLE001
        job.update(status="error", stage="오류", error=_errmsg(e))


def run_job(job: Job, src: Path, artist_name: str, artist_handle: str, schedule: str,
            clip_sec: float = C.CLIP_SECONDS, count: int = C.CLIP_COUNT,
            focus: float = 0.5):
    """CLI용: 분석과 렌더를 한 번에 실행하고 원본을 지웁니다."""
    analyze_job(job, src, clip_sec, count)
    if job.state["status"] == "ready":
        render_job(job, job.state["segments"], artist_name, artist_handle, schedule, focus)
    try:
        if src.exists():
            src.unlink()
    except OSError:
        pass


def cleanup_old_jobs(max_age_hours: float = 24):
    now = time.time()
    if not C.JOBS_DIR.exists():
        return
    for d in C.JOBS_DIR.iterdir():
        if d.is_dir() and now - d.stat().st_mtime > max_age_hours * 3600:
            shutil.rmtree(d, ignore_errors=True)
