@echo off
echo =======================================
echo RimWorld Trait Roller - Setup and Run
echo =======================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH!
    echo Please install Python from: https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

echo [1/3] Installing required Python packages...
echo.

pip install --upgrade pip
pip install pyautogui==0.9.54
pip install Pillow==10.2.0
pip install keyboard==0.13.5
pip install opencv-python==4.9.0.80
pip install numpy==1.26.4

echo.
echo [2/3] Optional: Installing OCR support (pytesseract)...
pip install pytesseract==0.3.10

echo.
echo =======================================
echo Installation complete!
echo =======================================
echo.
echo [3/3] Starting RimWorld Trait Roller...
echo.
echo NOTE: If OCR doesn't work, use simple_clicker.py instead
echo.

python rimworld_trait_roller.py

if errorlevel 1 (
    echo.
    echo =======================================
    echo Program crashed! Trying simple version...
    echo =======================================
    pause
    python simple_clicker.py
)

pause