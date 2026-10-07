"""서버 없이 터미널에서 바로 실행: python -m app.cli 영상.mp4 --artist 허지수 --handle j12xu --schedule "10/6(화)\n1부: 8:00~8:30" """
import argparse
import shutil
from pathlib import Path

from .pipeline import Job, run_job


def main():
    p = argparse.ArgumentParser(description="롱폼 공연 영상 → 30초 릴스 3개 자동 생성")
    p.add_argument("video")
    p.add_argument("--artist", default="")
    p.add_argument("--handle", default="")
    p.add_argument("--schedule", default="")
    p.add_argument("--seconds", type=float, default=30)
    p.add_argument("--count", type=int, default=3)
    p.add_argument("--focus", type=float, default=0.5,
                   help="가로 영상에서 세로로 자를 때 중심 위치 0(왼쪽)~1(오른쪽)")
    p.add_argument("--out", default=None, help="결과를 복사할 폴더")
    a = p.parse_args()

    job = Job()
    src = job.dir / ("source" + Path(a.video).suffix.lower())
    shutil.copy(a.video, src)
    run_job(job, src, a.artist, a.handle, a.schedule.replace("\\n", "\n"),
            a.seconds, a.count, a.focus)
    st = job.state
    if st["status"] != "done":
        print("실패:", st["error"])
        raise SystemExit(1)
    print(f"완료: {job.dir}")
    for c in st["clips"]:
        print(f"  reel_{c['index']}.mp4  {c['start']:.1f}s ~ {c['end']:.1f}s  (score {c['score']})")
    if a.out:
        out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
        for f in job.dir.glob("reel_*.mp4"):
            shutil.copy(f, out / f.name)
        shutil.copy(job.dir / "caption.txt", out / "caption.txt")
        print(f"복사 완료: {out}")


if __name__ == "__main__":
    main()
