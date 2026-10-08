@echo off
REM ═══════════════════════════════════════════════════════════
REM  Discord Reputation Bot - Startup Script
REM ═══════════════════════════════════════════════════════════

title Discord Reputation Bot

REM Run from the folder this script lives in
cd /d "%~dp0"

REM Use the project's virtual environment if there is one
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
) else (
    echo No virtualenv found. Consider creating one with: python -m venv .venv
)

:menu
echo ═══════════════════════════════════════════════════════════
echo                  Discord Reputation Bot
echo ═══════════════════════════════════════════════════════════
echo.
echo   [1] Start the bot
echo   [2] Install/Update requirements
echo   [0] Exit
echo.
set "choice="
set /p choice="Enter your choice (0-2): "

if "%choice%"=="1" goto :run_bot
if "%choice%"=="2" goto :install_requirements
if "%choice%"=="0" goto :eof

echo Invalid choice. Please enter 0, 1 or 2.
echo.
goto :menu

:install_requirements
echo.
echo Installing/updating requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Requirements installation completed!
echo.
goto :menu

:run_bot
echo.
echo Starting Discord bot... Press Ctrl+C to stop.
echo.
python bot.py
echo.
echo Discord bot has exited.
pause
