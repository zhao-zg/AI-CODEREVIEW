@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

REM AI-CodeReview 项目清理脚本 (Windows)
REM 用于清理临时文件、缓存文件和备份文件

echo 🧹 开始清理 AI-CodeReview 项目...

REM 清理 Python 缓存文件
echo 清理 Python 缓存文件...
for /d /r . %%d in (__pycache__) do @if exist "%%d" rd /s /q "%%d" 2>nul
del /s /q *.pyc 2>nul
del /s /q *.pyo 2>nul
del /s /q *.pyd 2>nul

REM 清理测试缓存
echo 清理测试缓存...
if exist ".pytest_cache" rd /s /q ".pytest_cache" 2>nul
if exist ".tox" rd /s /q ".tox" 2>nul
if exist "htmlcov" rd /s /q "htmlcov" 2>nul
if exist ".coverage" del /q ".coverage" 2>nul

REM 清理编辑器临时文件
echo 清理编辑器临时文件...
del /s /q *.swp 2>nul
del /s /q *.swo 2>nul
for /r . %%f in (*~) do @if exist "%%f" del /q "%%f" 2>nul

REM 清理备份文件
echo 清理备份文件...
for /r . %%f in (*-old.*) do @if exist "%%f" del /q "%%f" 2>nul
for /r . %%f in (*-new.*) do @if exist "%%f" del /q "%%f" 2>nul
for /r . %%f in (*-backup.*) do @if exist "%%f" del /q "%%f" 2>nul
for /r . %%f in (*_backup.*) do @if exist "%%f" del /q "%%f" 2>nul
del /s /q *.bak 2>nul

REM 清理临时文件
echo 清理临时文件...
del /s /q *.tmp 2>nul
del /s /q *.temp 2>nul
for /r . %%f in (*_temp.*) do @if exist "%%f" del /q "%%f" 2>nul

REM 清理系统文件
echo 清理系统文件...
del /s /q .DS_Store 2>nul
del /s /q Thumbs.db 2>nul
del /s /q Desktop.ini 2>nul

REM 清理日志文件（保留目录结构）
echo 清理日志文件...
if exist "log" (
    del /q "log\*.log" 2>nul
)

REM 清理 Node.js 相关（如果存在）
echo 清理 Node.js 文件...
if exist "node_modules" rd /s /q "node_modules" 2>nul
del /q npm-debug.log* 2>nul
del /q yarn-debug.log* 2>nul
del /q yarn-error.log* 2>nul

REM 清理构建产物
echo 清理构建产物...
if exist "build" rd /s /q "build" 2>nul
if exist "dist" rd /s /q "dist" 2>nul
for /d /r . %%d in (*.egg-info) do @if exist "%%d" rd /s /q "%%d" 2>nul

REM 显示清理结果
echo.
echo ✅ 项目清理完成！
echo.
echo 📊 当前项目结构：
echo ├── 核心文件
echo │   ├── api.py, ui.py (主应用)
echo │   ├── docker-compose*.yml (容器配置)
echo │   ├── Dockerfile (镜像构建)
echo │   └── requirements.txt (依赖)
echo ├── 配置目录
echo │   ├── conf/ (配置文件)
echo │   ├── scripts/ (脚本文件)
echo │   └── docs/ (文档)
echo ├── 启动脚本
echo │   ├── start.sh / start.bat (主启动脚本)
echo │   └── run_ui.sh / run_ui.bat (UI启动脚本)
echo └── 测试文件
echo     ├── test_multi_container.py
echo     └── test_single_container.py
echo.
echo 🚀 项目已准备就绪，可以使用 start.bat 启动！
echo.
pause
