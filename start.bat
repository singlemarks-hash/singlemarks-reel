@echo off
chcp 65001 >nul
REM Windows: 이 파일을 더블클릭하면 릴 메이커가 켜지고 브라우저가 열립니다. 끌 때는 이 창을 닫거나 Ctrl+C.
cd /d "%~dp0"
set PORT=8000
echo ▶ 릴 메이커 시작

where ffmpeg >nul 2>&1 || (echo ✗ ffmpeg 가 없습니다. PowerShell 에서  winget install ffmpeg  를 먼저 실행해 주세요. & pause & exit /b 1)
where python >nul 2>&1 || (echo ✗ python 이 없습니다. https://www.python.org 에서 설치해 주세요. & pause & exit /b 1)

if exist .git (echo · 최신 코드 확인 & git pull -q 2>nul)
if not exist .venv (echo · 가상환경 생성 & python -m venv .venv)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt

echo · 서버 켜는 중 → http://localhost:%PORT%
start "" /b cmd /c "timeout /t 2 >nul & start http://localhost:%PORT%"
uvicorn app.main:app --port %PORT%
pause
