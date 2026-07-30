@echo off
cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
    echo Chua cai dat bot. Hay chay setup.bat truoc.
    pause
    exit /b 1
)

if not exist .env (
    echo Khong tim thay file .env. Hay chay setup.bat hoac copy .env.example thanh .env.
    pause
    exit /b 1
)

echo Dang khoi dong Venus Welcome Bot...
.venv\Scripts\python.exe bot.py
pause
