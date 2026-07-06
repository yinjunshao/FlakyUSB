@echo off
setlocal
cd /d "%~dp0"

echo ===================================================
echo   Building FlakyUSBRecover.exe (PyInstaller)
echo ===================================================

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Install Python 3.10+ and re-run this script.
    exit /b 1
)

echo [1/3] Installing build dependency...
python -m pip install --upgrade pip >nul
python -m pip install -r requirements-build.txt
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install build dependencies.
    exit /b 1
)

echo [2/3] Building executable...
python -m PyInstaller --clean --noconfirm --onefile --name FlakyUSBRecover flaky_usb_recover.py
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed.
    exit /b 1
)

echo [3/3] Done.
echo Output: dist\FlakyUSBRecover.exe
echo You can now distribute the project folder and users can run Run_USB_Recover.bat.

endlocal
