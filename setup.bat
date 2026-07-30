@echo off
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo [1/3] Dang tao moi truong Python...
    py -3.12 -m venv .venv 2>nul || py -3.11 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo Khong tao duoc moi truong Python. Hay cai Python 3.11 hoac 3.12.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Moi truong Python da ton tai.
)

echo [2/3] Dang cai thu vien...
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo Cai thu vien that bai.
    pause
    exit /b 1
)

if not exist .env (
    copy .env.example .env >nul
    echo [3/3] Da tao file .env.
) else (
    echo [3/3] File .env da ton tai.
)

echo.
echo Cai dat xong. Hay mo file .env, dien token va ID, sau do chay start.bat.
pause
