@echo off
chcp 65001 >nul
REM Windows 环境配置检查脚本
REM 确保 .env 文件存在并包含 .env.dist 中的所有参数

setlocal enabledelayedexpansion

echo [INFO] Start environment configuration check...

REM 定义文件路径
set ENV_DIST=conf\.env.dist
set ENV_FILE=conf\.env

REM 检查 .env.dist 是否存在
if not exist "%ENV_DIST%" (
    echo [ERROR] Configuration template file %ENV_DIST% does not exist!
    exit /b 1
)

echo [INFO] Reading configuration template: %ENV_DIST%

REM 检查 .env 文件是否存在
if not exist "%ENV_FILE%" (
    echo [WARNING] Environment configuration file %ENV_FILE% does not exist
    echo [INFO] Copying configuration from %ENV_DIST%...
    
    REM 确保目录存在
    if not exist "conf" mkdir conf
    
    REM 复制文件
    copy "%ENV_DIST%" "%ENV_FILE%" >nul
    if errorlevel 1 (
        echo [ERROR] Failed to copy configuration file
        exit /b 1
    )
    
    echo [INFO] Successfully created %ENV_FILE%
    goto :validate_config
)

echo [INFO] Checking existing environment configuration: %ENV_FILE%

REM 比较两个文件的参数（简化版本）
REM 提取 .env.dist 中的所有参数名
set TEMP_DIST=%TEMP%\env_dist_keys.tmp
set TEMP_CURRENT=%TEMP%\env_current_keys.tmp

REM 提取 .env.dist 中的参数
findstr /r "^[A-Z_]*=" "%ENV_DIST%" | findstr /v "^#" > "%TEMP_DIST%" 2>nul

REM 提取 .env 中的参数  
findstr /r "^[A-Z_]*=" "%ENV_FILE%" | findstr /v "^#" > "%TEMP_CURRENT%" 2>nul

REM 检查是否有缺失的参数（简化检查）
set MISSING_COUNT=0
for /f "tokens=1 delims==" %%a in (%TEMP_DIST%) do (
    findstr /b "%%a=" "%ENV_FILE%" >nul 2>&1
    if errorlevel 1 (
        set /a MISSING_COUNT+=1
        echo [WARNING] Missing parameter: %%a
    )
)

REM 清理临时文件
del "%TEMP_DIST%" 2>nul
del "%TEMP_CURRENT%" 2>nul

if !MISSING_COUNT! gtr 0 (
    echo [WARNING] Found !MISSING_COUNT! missing environment variables
    echo [INFO] Adding missing environment variables...
    
    REM 追加缺失的参数（简化处理）
    echo. >> "%ENV_FILE%"
    echo # ======================================== >> "%ENV_FILE%"
    echo # Parameters automatically added by environment check script >> "%ENV_FILE%"
    echo # ======================================== >> "%ENV_FILE%"
    
    REM 找出缺失的参数并追加
    for /f "tokens=* delims=" %%a in (%ENV_DIST%) do (
        set "LINE=%%a"
        if "!LINE:~0,1!" neq "#" if "!LINE!" neq "" (
            for /f "tokens=1 delims==" %%b in ("%%a") do (
                findstr /b "%%b=" "%ENV_FILE%" >nul 2>&1
                if errorlevel 1 (
                    echo %%a >> "%ENV_FILE%"
                )
            )
        )
    )
    
    echo [INFO] Environment configuration update completed
) else (
    echo [INFO] Environment configuration is complete, all required parameters exist
)

:validate_config
echo [INFO] Validating critical configuration items...

REM 检查关键配置项
findstr /b "LLM_PROVIDER=" "%ENV_FILE%" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Missing critical configuration: LLM_PROVIDER
)

findstr /b "SERVER_PORT=" "%ENV_FILE%" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Missing critical configuration: SERVER_PORT
)

echo [INFO] Environment configuration check completed
echo.

REM 显示配置摘要
echo ========================================
echo Configuration Summary:
for /f "tokens=1,2 delims==" %%a in ('findstr /b "LLM_PROVIDER=\|SERVER_PORT=\|TZ=" "%ENV_FILE%" 2^>nul') do (
    echo   %%a: %%b
)
echo ========================================
echo.

exit /b 0
