@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo       SCREEN RECORDER EXE BUILDER
echo ==========================================

python -m pip install -r requirements.txt
if errorlevel 1 goto :failed

python -m pip install pyinstaller
if errorlevel 1 goto :failed

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist ScreenRecorder.spec del /q ScreenRecorder.spec

if exist "ffmpeg\ffmpeg.exe" (
    echo FFmpeg found. Building with bundled FFmpeg...
    python -m PyInstaller ^
      --noconfirm ^
      --clean ^
      --windowed ^
      --name ScreenRecorder ^
      --collect-all customtkinter ^
      --add-binary "ffmpeg\ffmpeg.exe;ffmpeg" ^
      main.py
) else (
    echo FFmpeg was not found. Building without bundled FFmpeg...
    echo The app can still use FFmpeg if it is installed in PATH.
    python -m PyInstaller ^
      --noconfirm ^
      --clean ^
      --windowed ^
      --name ScreenRecorder ^
      --collect-all customtkinter ^
      main.py
)

if errorlevel 1 goto :failed

echo.
echo ==========================================
echo BUILD SUCCESSFUL
echo ==========================================
echo EXE:
echo dist\ScreenRecorder\ScreenRecorder.exe
echo.
echo If FFmpeg was bundled, it is inside the app's ffmpeg folder.
echo.
pause
exit /b 0

:failed
echo.
echo ==========================================
echo BUILD FAILED
echo ==========================================
echo Check the error above.
echo.
pause
exit /b 1
