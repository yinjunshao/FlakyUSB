@echo off
TITLE Flaky USB Auto-Recover Tool
setlocal

set "SCRIPT_DIR=%~dp0"
set "EXE_PATH=%SCRIPT_DIR%dist\FlakyUSBRecover.exe"

echo ===================================================
echo   Starting Flaky USB Auto-Recover Tool...
echo ===================================================

:: Preferred path for end-users: run packaged EXE (no Python install needed)
IF EXIST "%EXE_PATH%" (
    echo [INFO] Launching packaged executable...
    "%EXE_PATH%"
    goto :done
)

:: Fallback for contributors/developers
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] No packaged EXE found at:
    echo         %EXE_PATH%
    echo [ERROR] Python is also not installed or not in PATH.
    echo.
    echo To build a no-install EXE, run build_exe.bat on a machine with Python.
    pause
    exit /b 1
)

echo [INFO] EXE not found. Running Python script fallback...
python "%SCRIPT_DIR%flaky_usb_recover.py"

:done
endlocal

pause
