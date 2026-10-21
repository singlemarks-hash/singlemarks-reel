#!/bin/bash
# Mac: 이 파일을 더블클릭하면 릴 메이커가 켜지고 브라우저가 열립니다. 끌 때는 이 창에서 Ctrl+C.
cd "$(dirname "$0")"
PORT=8000

echo "▶ 릴 메이커 시작"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "✗ ffmpeg 가 없습니다. 터미널에서  brew install ffmpeg  를 먼저 실행해 주세요."
  read -n 1 -s -r -p "아무 키나 누르면 닫힙니다"; exit 1
fi

PY=python3
command -v $PY >/dev/null 2>&1 || { echo "✗ python3 가 없습니다. https://www.python.org 에서 설치해 주세요."; read -n 1 -s -r; exit 1; }

# 최신 코드
if [ -d .git ]; then
  echo "· 최신 코드 확인"; git pull -q 2>/dev/null || echo "  (업데이트 생략: 네트워크 또는 변경사항 충돌)"
fi

# 가상환경 + 패키지
if [ ! -d .venv ]; then echo "· 가상환경 생성"; $PY -m venv .venv; fi
source .venv/bin/activate
pip install -q -r requirements.txt 2>&1 | grep -v -i "warning\|notice" || true

# 기존에 떠 있는 서버 정리
lsof -ti tcp:$PORT 2>/dev/null | xargs kill 2>/dev/null

echo "· 서버 켜는 중 → http://localhost:$PORT"
( sleep 2; open "http://localhost:$PORT" ) &
exec uvicorn app.main:app --port $PORT
