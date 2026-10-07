"""업로드 → 하이라이트 분석 → 렌더 → 캡션. 잡 상태는 jobs/<id>/status.json 에 기록."""
from __future__ import annotations

import json
import shutil
import time
import traceback
import uuid
from pathlib import Path

from . import config as C
from .caption import build_caption
from .highlight import find_highlights, probe
from .render import render_clip, thumbnail


class Job:
    def __init__(self, job_id: str | None = None):
        self.id = job_id or uuid.uuid4().hex[:12]
        self.dir = C.JOBS_DIR / self.id
        self.dir.mkdir(parents=True, exist_ok=True)
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


def run_job(job: Job, src: Path, artist_name: str, artist_handle: str, schedule: str,
            clip_sec: float = C.CLIP_SECONDS, count: int = C.CLIP_COUNT,
            focus: float = 0.5):
    try:
        job.update(status="running", stage="영상 정보 확인 중", progress=3)
        info = probe(str(src))
        job.update(source={"duration": info["duration"], "width": info["width"],
                           "height": info["height"]})

        def prog(msg):
            job.update(stage=msg, progress=max(job.state["progress"], 8))

        segs = find_highlights(str(src), clip_sec=clip_sec, count=count, progress=prog)
        job.update(stage=f"하이라이트 {len(segs)}개 선택 완료", progress=25,
                   segments=[s.to_dict() for s in segs])

        clips = []
        for i, s in enumerate(segs, 1):
            job.update(stage=f"릴스 {i}/{len(segs)} 렌더링 중 ({s.start:.0f}s~{s.end:.0f}s)",
                       progress=25 + int(70 * (i - 1) / len(segs)))
            out = job.dir / f"reel_{i}.mp4"
            render_clip(str(src), s.start, s.end, out, focus=focus,
                        src_w=info["width"], src_h=info["height"])
            thumb = job.dir / f"reel_{i}.jpg"
            thumbnail(out, thumb)
            clips.append({
                "index": i, "start": s.start, "end": s.end, "score": s.score,
                "video": f"/jobs/{job.id}/{out.name}", "thumb": f"/jobs/{job.id}/{thumb.name}",
            })
            job.update(clips=clips)

        caption = build_caption(artist_name, artist_handle, schedule)
        (job.dir / "caption.txt").write_text(caption, encoding="utf-8")
        job.update(status="done", stage="완료", progress=100, caption=caption)
    except Exception as e:  # noqa: BLE001
        job.update(status="error", stage="오류", error=f"{e}\n{traceback.format_exc()[-1500:]}")
    finally:
        # 원본은 용량이 크므로 처리 후 삭제 (클립만 보관)
        try:
            if src.exists() and src.parent == job.dir:
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
