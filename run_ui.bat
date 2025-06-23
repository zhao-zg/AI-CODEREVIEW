@echo off
echo Starting AI Code Review Dashboard...
echo.
echo Access the dashboard at: http://localhost:8501
echo Press Ctrl+C to stop the server
echo.
streamlit run ui.py --server.port 8501 --server.headless true
pause
