@echo off
cd /d "%~dp0"
pythonw alan_tanim2.py 2>nul
if %errorlevel% neq 0 (
    python alan_tanim2.py
    if %errorlevel% neq 0 (
        echo.
        echo [HATA] Uygulama baslatilamadi!
        pause
    )
)
