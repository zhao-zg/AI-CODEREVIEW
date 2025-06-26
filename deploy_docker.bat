@echo off
chcp 65001 >nul
REM One-click build and deploy AI-CodeReview Docker image (Windows)
set IMAGE_NAME=ai-codereview:latest
set CONTAINER_NAME=ai-codereview

REM Build image
echo [1/3] Building Docker image...
docker build -t %IMAGE_NAME% .

REM Stop and remove old container (if exists)
echo [2/3] Stopping and removing old container (if exists)...
docker stop %CONTAINER_NAME% 2>nul
if not errorlevel 1 docker rm %CONTAINER_NAME% 2>nul

REM Start new container
echo [3/3] Starting new container...
docker run -d ^
  --name %CONTAINER_NAME% ^
  -p 5001:5001 ^
  -p 5002:5002 ^
  -v %cd%\conf:/app/conf ^
  -v %cd%\data:/app/data ^
  -v %cd%\log:/app/log ^
  -e TZ=Asia/Shanghai ^
  -e PYTHONUNBUFFERED=1 ^
  -e PYTHONIOENCODING=utf-8 ^
  %IMAGE_NAME%

echo Deploy complete! Visit http://localhost:5002 for UI, http://localhost:5001 for API.
