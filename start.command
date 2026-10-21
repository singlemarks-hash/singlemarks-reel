#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  Reel Maker (Mac)  — 이 파일을 더블클릭하면 켜집니다.
#  처음 실행하면 필요한 것(ffmpeg, Python 패키지)을 자동으로 내려받습니다. (1~3분)
#  끌 때는 이 창에서 Ctrl + C 또는 창 닫기.
# ─────────────────────────────────────────────────────────────
cd "$(dirname "$0")"
PORT=8000
BIN="$PWD/bin"; mkdir -p "$BIN"
export PATH="$BIN:/opt/homebrew/bin:/usr/local/bin:$PATH"

pause(){ echo; read -n 1 -s -r -p "아무 키나 누르면 창이 닫힙니다."; echo; }
echo "▶ Reel Maker 시작"

# ── 1. Python ──────────────────────────────────────────────
PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(0 if sys.version_info>=(3,9) else 1)" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "✗ Python 이 아직 준비되지 않았습니다."
  echo "  · 방금 '명령어 라인 개발자 도구' 설치 팝업이 떴다면 [설치] 를 누르고, 끝나면 이 파일을 다시 더블클릭하세요."
  echo "  · 팝업이 없었다면 https://www.python.org/downloads/ 에서 설치한 뒤 다시 실행하세요."
  xcode-select --install >/dev/null 2>&1
  pause; exit 1
fi
echo "· Python: $($PY --version)"

# ── 2. ffmpeg (없으면 자동 다운로드) ───────────────────────────
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "· ffmpeg 내려받는 중 (처음 한 번, 약 100MB)…"
  ARCH=$(uname -m); [ "$ARCH" = "arm64" ] && A="arm64" || A="amd64"
  ok=1
  for tool in ffmpeg ffprobe; do
    rm -f "$BIN/$tool.zip"
    curl -fsSL -o "$BIN/$tool.zip" "https://ffmpeg.martin-riedl.de/redirect/latest/macos/$A/release/$tool.zip" \
      || curl -fsSL -o "$BIN/$tool.zip" "https://evermeet.cx/ffmpeg/getrelease/$( [ $tool = ffmpeg ] && echo zip || echo $tool/zip )" \
      || { ok=0; break; }
    unzip -oq "$BIN/$tool.zip" -d "$BIN" && rm -f "$BIN/$tool.zip"
    chmod +x "$BIN/$tool" 2>/dev/null; xattr -d com.apple.quarantine "$BIN/$tool" 2>/dev/null
  done
  if [ $ok = 0 ] || ! command -v ffmpeg >/dev/null 2>&1; then
    echo "✗ ffmpeg 자동 설치에 실패했습니다. 인터넷 연결을 확인하거나, 터미널에서  brew install ffmpeg  후 다시 실행하세요."
    pause; exit 1
  fi
fi
echo "· ffmpeg: $(ffmpeg -version 2>/dev/null | head -1 | cut -d' ' -f1-3)"

# ── 3. 최신 코드 (git 으로 받은 경우에만) ────────────────────────
if [ -d .git ] && command -v git >/dev/null 2>&1; then
  git pull -q 2>/dev/null && echo "· 최신 코드 확인" || echo "· (코드 업데이트 생략)"
fi

# ── 4. Python 패키지 ───────────────────────────────────────────
if [ ! -d .venv ] || [ ! -x .venv/bin/python ]; then echo "· 가상환경 생성"; rm -rf .venv; "$PY" -m venv .venv || { echo "✗ 가상환경 생성 실패"; pause; exit 1; }; fi
source .venv/bin/activate
echo "· 패키지 확인 중…"
pip install -q --disable-pip-version-check -r requirements.txt 2>&1 | grep -iv "warning\|notice" || true

# ── 5. 서버 ───────────────────────────────────────────────────
lsof -ti tcp:$PORT 2>/dev/null | xargs kill 2>/dev/null
echo
echo "✓ 준비 완료 → 브라우저가 열립니다: http://localhost:$PORT"
echo "  (이 창은 닫지 마세요. 끝낼 때 Ctrl + C)"
echo
( sleep 2; open "http://localhost:$PORT" ) &
exec uvicorn app.main:app --port $PORT
