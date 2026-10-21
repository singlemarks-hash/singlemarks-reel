@echo off
chcp 65001 >nul
setlocal
REM ─────────────────────────────────────────────────────────────
REM  Reel Maker (Windows) — 이 파일을 더블클릭하면 켜집니다.
REM  처음 실행하면 필요한 것(ffmpeg, Python 패키지)을 자동으로 내려받습니다. (2~4분)
REM  끌 때는 이 창을 닫거나 Ctrl + C.
REM ─────────────────────────────────────────────────────────────
cd /d "%~dp0"
set PORT=8000
set BIN=%CD%\bin
if not exist "%BIN%" mkdir "%BIN%"
set PATH=%BIN%;%PATH%
echo ▶ Reel Maker 시작

REM ── 1. Python ──
set PY=
py -3 -c "import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1 && set PY=py -3
if not defined PY python -c "import sys;sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>&1 && set PY=python
if not defined PY (
  echo ✗ Python 이 없습니다. 설치 페이지를 엽니다.
  echo   설치할 때 "Add python.exe to PATH" 체크박스를 꼭 켜고, 설치 후 이 파일을 다시 더블클릭하세요.
  start https://www.python.org/downloads/windows/
  pause & exit /b 1
)
echo · Python 확인

REM ── 2. ffmpeg (없으면 자동 다운로드) ──
where ffmpeg >nul 2>&1 && where ffprobe >nul 2>&1
if errorlevel 1 (
  echo · ffmpeg 내려받는 중 (처음 한 번, 약 100MB)...
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ProgressPreference='SilentlyContinue';" ^
    "Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip' -OutFile \"$env:BIN\ff.zip\";" ^
    "Expand-Archive -Force \"$env:BIN\ff.zip\" \"$env:BIN\ff\";" ^
    "Get-ChildItem \"$env:BIN\ff\" -Recurse -Include ffmpeg.exe,ffprobe.exe | ForEach-Object { Move-Item -Force $_.FullName \"$env:BIN\" };" ^
    "Remove-Item -Recurse -Force \"$env:BIN\ff\",\"$env:BIN\ff.zip\""
  where ffmpeg >nul 2>&1 || (echo ✗ ffmpeg 자동 설치 실패. 인터넷 연결을 확인하거나 PowerShell 에서  winget install ffmpeg  후 다시 실행하세요. & pause & exit /b 1)
)
echo · ffmpeg 확인

REM ── 3. 최신 코드 (git 으로 받은 경우에만) ──
if exist .git (where git >nul 2>&1 && git pull -q 2>nul && echo · 최신 코드 확인)

REM ── 4. Python 패키지 ──
if not exist .venv\Scripts\python.exe (echo · 가상환경 생성 & %PY% -m venv .venv)
call .venv\Scripts\activate.bat
echo · 패키지 확인 중...
pip install -q --disable-pip-version-check -r requirements.txt

REM ── 5. 서버 ──
echo.
echo ✓ 준비 완료 → 브라우저가 열립니다: http://localhost:%PORT%
echo   (이 창은 닫지 마세요. 끝낼 때 Ctrl + C 또는 창 닫기)
echo.
start "" /b cmd /c "timeout /t 2 >nul & start http://localhost:%PORT%"
uvicorn app.main:app --port %PORT%
pause
