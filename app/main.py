"""FastAPI 서버: 업로드 / 상태 조회 / 결과 다운로드."""
from __future__ import annotations

import shutil
import threading
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config as C
from pydantic import BaseModel

from .pipeline import Job, analyze_job, cleanup_old_jobs, render_job
from .render import check_ffmpeg

app = FastAPI(title="Singlemarks Reel Maker")
C.JOBS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/jobs", StaticFiles(directory=str(C.JOBS_DIR)), name="jobs")
STATIC = Path(__file__).parent / "static"
FFMPEG_PROBLEMS = check_ffmpeg()
for _p in FFMPEG_PROBLEMS:
    print("[경고]", _p)


@app.get("/api/health")
def health():
    return {"ok": not FFMPEG_PROBLEMS, "problems": FFMPEG_PROBLEMS}


ALLOWED = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".mts"}


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/api/template")
def template():
    return {
        "title": C.TITLE_TEXT, "subtitle": C.SUBTITLE_TEXT,
        "clip_seconds": C.CLIP_SECONDS, "clip_count": C.CLIP_COUNT,
        "caption_template": C.CAPTION_TEMPLATE,
    }


@app.post("/api/jobs")
async def create_job(
    background: BackgroundTasks,
    video: UploadFile = File(...),
    artist_name: str = Form(""),
    artist_handle: str = Form(""),
    schedule: str = Form(""),
    clip_seconds: float = Form(C.CLIP_SECONDS),
    clip_count: int = Form(C.CLIP_COUNT),
    focus: float = Form(0.5),
):
    ext = Path(video.filename or "upload.mp4").suffix.lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"지원하지 않는 형식입니다: {ext}")
    clip_seconds = max(10, min(90, clip_seconds))
    clip_count = max(1, min(6, clip_count))

    cleanup_old_jobs()
    job = Job()
    src = job.dir / f"source{ext}"
    with src.open("wb") as f:
        shutil.copyfileobj(video.file, f, length=1024 * 1024)
    job.update(stage="업로드 완료, 분석 대기 중", progress=2,
               artist={"name": artist_name, "handle": artist_handle}, schedule=schedule,
               focus=focus)

    threading.Thread(target=analyze_job, args=(job, src, clip_seconds, clip_count),
                     daemon=True).start()
    return {"id": job.id}


class SegmentIn(BaseModel):
    start: float
    end: float


class RenderIn(BaseModel):
    segments: list[SegmentIn]
    artist_name: str | None = None
    artist_handle: str | None = None
    schedule: str | None = None


@app.post("/api/jobs/{job_id}/render")
def start_render(job_id: str, body: RenderIn):
    st = Job.load(job_id)
    if st is None:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    if st["status"] not in ("ready", "done", "error"):
        raise HTTPException(409, "아직 분석이 끝나지 않았습니다.")
    src = C.JOBS_DIR / job_id / st["source"]["file"]
    if not src.exists():
        raise HTTPException(410, "원본 영상이 삭제되어 다시 렌더링할 수 없습니다. 새로 업로드해 주세요.")
    if not body.segments or len(body.segments) > 6:
        raise HTTPException(400, "구간은 1~6개여야 합니다.")
    dur = st["source"]["duration"]
    segs = []
    for sg in body.segments:
        start = max(0.0, min(sg.start, dur - 1))
        end = max(start + 5, min(sg.end, dur))
        segs.append({"start": round(start, 2), "end": round(end, 2)})
    segs.sort(key=lambda x: x["start"])

    job = Job(job_id)
    job.state = st
    artist = st.get("artist") or {}
    name = body.artist_name if body.artist_name is not None else artist.get("name", "")
    handle = body.artist_handle if body.artist_handle is not None else artist.get("handle", "")
    schedule = body.schedule if body.schedule is not None else st.get("schedule", "")
    threading.Thread(target=render_job,
                     args=(job, segs, name, handle, schedule, st.get("focus", 0.5)),
                     daemon=True).start()
    return {"id": job_id, "segments": segs}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    st = Job.load(job_id)
    if st is None:
        raise HTTPException(404, "작업을 찾을 수 없습니다.")
    return JSONResponse(st)


@app.get("/api/jobs/{job_id}/download/{n}")
def download(job_id: str, n: int):
    st = Job.load(job_id)
    if st is None:
        raise HTTPException(404)
    f = C.JOBS_DIR / job_id / f"reel_{n}.mp4"
    if not f.exists():
        raise HTTPException(404)
    name = (st.get("artist") or {}).get("name") or "reel"
    return FileResponse(f, media_type="video/mp4", filename=f"{name}_reel_{n}.mp4")


@app.get("/api/jobs/{job_id}/caption.txt")
def caption(job_id: str):
    f = C.JOBS_DIR / job_id / "caption.txt"
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f, media_type="text/plain; charset=utf-8", filename="caption.txt")
