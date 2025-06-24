@echo off
chcp 65001 >nul
echo Starting AI-CodeReview UI...
cd /d "%~dp0"
python -m streamlit run ui.py --server.headless false --server.port 8501
pause
