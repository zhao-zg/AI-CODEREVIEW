@echo off
chcp 65001 >nul
echo Starting AI-CodeReview UI...
echo UI will automatically read configuration from .env file
cd /d "%~dp0"
python ui.py
pause
