"""
롱폼 공연 영상에서 하이라이트 구간을 자동으로 찾습니다.

방식 (오디오 기반, 영상 디코딩 없이 빠름):
  1. ffmpeg로 모노 16kHz PCM 추출
  2. 0.5초 단위로 RMS(음량)와 스펙트럼 플럭스(연주의 에너지 변화·박수 등) 계산
     (numpy 벡터 연산 — 30분 영상도 1초 안팎)
  3. 30초 창을 1초씩 밀며 점수화 → 무음 비율이 높은 창은 감점
  4. 겹치지 않도록 상위 N개 선택 (Non-max suppression)
  5. 시작점을 근처의 음량이 잠깐 꺼지는 지점(프레이즈 경계)으로 스냅
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, asdict

import numpy as np

SR = 16000
HOP_SEC = 0.5
HOP = int(SR * HOP_SEC)
NFFT = 2048


@dataclass
class Segment:
    start: float
    end: float
    score: float

    def to_dict(self):
        return asdict(self)


def probe(path: str) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json",
         "-show_format", "-show_streams", path],
        capture_output=True, text=True, check=True,
    ).stdout
    info = json.loads(out)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    if v is None:
        raise ValueError("영상 스트림이 없습니다.")
    if a is None:
        raise ValueError("오디오 스트림이 없어 하이라이트를 분석할 수 없습니다.")
    dur = float(info["format"].get("duration") or v.get("duration") or 0)
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    w, h = int(v["width"]), int(v["height"])
    if rot in (90, -90, 270, -270):
        w, h = h, w
    return {"duration": dur, "width": w, "height": h}


def load_audio(path: str) -> np.ndarray:
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR),
         "-f", "s16le", "-"],
        capture_output=True, check=True,
    )
    pcm = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
    return pcm


def features(pcm: np.ndarray):
    """프레임별 RMS(dB)와 스펙트럼 플럭스 반환. 반복문 없이 한 번에 계산."""
    n_frames = max(1, len(pcm) // HOP)
    pcm = pcm[: n_frames * HOP]
    frames = pcm.reshape(n_frames, HOP)
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)

    # 각 프레임 시작 지점에서 NFFT 샘플만 떼어 FFT (프레임당 2048샘플 = 0.128초)
    padded = np.concatenate([pcm, np.zeros(NFFT, dtype=np.float32)])
    idx = np.arange(n_frames)[:, None] * HOP + np.arange(NFFT)[None, :]
    win = np.hanning(NFFT).astype(np.float32)
    mag = np.log1p(np.abs(np.fft.rfft(padded[idx] * win, axis=1)))
    d = np.diff(mag, axis=0)
    flux = np.concatenate([[0.0], np.sum(np.where(d > 0, d, 0), axis=1)]).astype(np.float32)

    rms_db = 20 * np.log10(rms + 1e-9).astype(np.float32)
    return rms_db, flux


def _norm(x: np.ndarray) -> np.ndarray:
    lo, hi = np.percentile(x, 5), np.percentile(x, 95)
    if hi - lo < 1e-6:
        return np.zeros_like(x)
    return np.clip((x - lo) / (hi - lo), 0, 1)


def find_highlights(path: str, clip_sec: float = 30, count: int = 3,
                    min_gap_sec: float | None = None, progress=None) -> list[Segment]:
    info = probe(path)
    duration = info["duration"]
    if progress:
        progress("오디오 추출 중…")
    pcm = load_audio(path)
    if progress:
        progress("에너지/다이내믹 분석 중…")
    rms_db, flux = features(pcm)
    n = len(rms_db)
    total = n * HOP_SEC
    duration = min(duration, total) if duration else total

    if duration <= clip_sec + 1:
        return [Segment(0.0, round(min(duration, clip_sec), 2), 1.0)]

    if min_gap_sec is None:
        # 공연 전체에 고르게 퍼지도록: 영상 길이의 10% (최소 20초). 30분이면 3분 간격.
        min_gap_sec = max(20.0, duration * 0.10)

    loud = _norm(rms_db)
    dyn = _norm(flux)
    silence = (rms_db < -45).astype(np.float32)

    win = int(round(clip_sec / HOP_SEC))
    step = int(round(1.0 / HOP_SEC))

    def wmean(x):
        c = np.concatenate([[0], np.cumsum(x)])
        return (c[win:] - c[:-win]) / win

    s_loud, s_dyn, s_sil = wmean(loud), wmean(dyn), wmean(silence)
    scores = 0.55 * s_loud + 0.45 * s_dyn - 0.8 * s_sil
    # 영상 맨 앞/뒤 1%는 사운드체크·마무리 멘트일 확률이 높아 약간 감점
    edge = int(0.01 * len(scores)) + 1
    scores[:edge] -= 0.1
    scores[-edge:] -= 0.1

    cand_idx = np.arange(0, len(scores), step)
    cand = [(float(scores[i]), int(i)) for i in cand_idx]
    cand.sort(reverse=True)

    chosen: list[int] = []
    excl = int(round((clip_sec + min_gap_sec) / HOP_SEC))
    for sc, i in cand:
        if len(chosen) >= count:
            break
        if all(abs(i - j) >= excl for j in chosen):
            chosen.append(i)
    if len(chosen) < count:  # 영상이 짧으면 겹침을 절반까지 허용해 재시도
        excl = max(1, win // 2)
        for sc, i in cand:
            if len(chosen) >= count:
                break
            if all(abs(i - j) >= excl for j in chosen):
                chosen.append(i)

    segs: list[Segment] = []
    snap = int(round(3.0 / HOP_SEC))
    for i in chosen:
        lo, hi = max(0, i - snap), min(n - win, i + snap)
        if hi > lo:
            local = rms_db[lo:hi]
            j = lo + int(np.argmin(local))      # 음량이 잠깐 낮아지는 경계점
        else:
            j = i
        start = j * HOP_SEC
        end = min(start + clip_sec, duration)
        start = max(0.0, end - clip_sec)
        segs.append(Segment(round(start, 2), round(end, 2), round(float(scores[i]), 4)))

    segs.sort(key=lambda s: s.start)
    return segs
