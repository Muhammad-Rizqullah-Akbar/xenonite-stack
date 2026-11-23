@echo off
setlocal enabledelayedexpansion
title Xenonite 4-Layer Stack - 1-Click Bootstrap (Windows)

:: 0. Lock working directory to script folder
cd /d "%~dp0"

echo ====================================================================
echo         XENONITE 4-LAYER STACK - 1-CLICK BOOTSTRAP (WINDOWS)
echo ====================================================================

:: 1. Detect Python 3.10+ (avoids Windows Store stub)
set "PYTHON_CMD="

where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    py -3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
    if !ERRORLEVEL! EQU 0 (
        set "PYTHON_CMD=py -3"
    )
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        python -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul
        if !ERRORLEVEL! EQU 0 (
            set "PYTHON_CMD=python"
        )
    )
)

if not defined PYTHON_CMD (
    echo.
    echo [ERROR] Python 3.10+ not found in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo IMPORTANT: Check 'Add python.exe to PATH' during installation.
    echo.
    pause
    exit /b 1
)

echo [*] Python detected: !PYTHON_CMD!

:: 2. Create isolated .venv
if exist ".venv" (
    if not exist ".venv\Scripts\python.exe" (
        echo [*] Cleaning incomplete .venv directory...
        rmdir /s /q ".venv"
    )
)
if not exist ".venv\Scripts\python.exe" (
    echo [*] Creating isolated virtual environment (.venv)...
    !PYTHON_CMD! -m venv .venv
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Failed to create .venv.
        pause
        exit /b 1
    )
)

:: 3. Activate and install editable package
call "%~dp0.venv\Scripts\activate.bat"
set "VENV_PY=%~dp0.venv\Scripts\python.exe"

"%VENV_PY%" -c "import xenonite_stack, mcp" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [*] Upgrading pip/setuptools/wheel...
    "%VENV_PY%" -m pip install --upgrade pip setuptools wheel >nul 2>nul
    echo [*] Installing xenonite-stack and MCP SDK...
    "%VENV_PY%" -m pip install -e .
    if !ERRORLEVEL! NEQ 0 (
        echo [ERROR] Failed to install xenonite-stack.
        pause
        exit /b 1
    )
)

:: 4. Ensure .env exists from template
if not exist ".env" (
    if exist ".env.example" (
        copy /y ".env.example" ".env" >nul
        echo [*] Created default .env from .env.example
    )
)

:: 5. Run Pre-Flight System Audit
echo.
"%VENV_PY%" -m xenonite_stack check

:: 6. Interactive Operational Menu
:menu
echo.
echo ====================================================================
echo                     SELECT OPERATIONAL ACTION:
echo ====================================================================
echo  [1] Install into Antigravity (~/.gemini/config) - Standard Rule
echo  [2] Install into Antigravity (~/.gemini/config) - Mr. Robot Persona
echo  [3] Print MCP JSON Snippet (Claude Desktop / Cursor / Windsurf)
echo  [4] Start Self-Hosted Docker Stack (Full: L1 Memory + L2 Web Intel)
echo  [5] Start Self-Hosted Docker Stack with NVIDIA GPU (TEI CUDA)
echo  [6] Run Silent-Filtered Verification Suite (xenonite verify)
echo  [7] Re-run Pre-Flight System Audit (xenonite check)
echo  [8] Exit
echo ====================================================================
set "USER_CHOICE="
set /p USER_CHOICE="Your choice [1-8] (Default: 1): "

if "%USER_CHOICE%"=="" set "USER_CHOICE=1"
if "%USER_CHOICE%"=="1" (
    "%VENV_PY%" -m xenonite_stack install --persona standard
    "%VENV_PY%" -m xenonite_stack verify
    goto :menu
)
if "%USER_CHOICE%"=="2" (
    "%VENV_PY%" -m xenonite_stack install --persona mr-robot
    "%VENV_PY%" -m xenonite_stack verify
    goto :menu
)
if "%USER_CHOICE%"=="3" (
    echo.
    "%VENV_PY%" -m xenonite_stack print-mcp
    goto :menu
)
if "%USER_CHOICE%"=="4" (
    "%VENV_PY%" -m xenonite_stack docker up full
    goto :menu
)
if "%USER_CHOICE%"=="5" (
    "%VENV_PY%" -m xenonite_stack docker up full --gpu
    goto :menu
)
if "%USER_CHOICE%"=="6" (
    "%VENV_PY%" -m xenonite_stack verify
    goto :menu
)
if "%USER_CHOICE%"=="7" (
    "%VENV_PY%" -m xenonite_stack check
    goto :menu
)
if "%USER_CHOICE%"=="8" (
    goto :end
)

echo [WARN] Invalid selection.
goto :menu

:end
echo [*] Done. Remember to restart your AI IDE after installing MCP/Hooks.
endlocal
