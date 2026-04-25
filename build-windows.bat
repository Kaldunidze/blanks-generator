@echo off
REM build-windows.bat — builds a portable single-file Windows executable
REM Run from the project root in a normal Command Prompt or PowerShell.

echo =^> Installing dependencies...
python -m pip install dearpygui typst pillow pyinstaller

REM Optional: bundle a Cyrillic UI font
set FONT_SRC=%WINDIR%\Fonts\arial.ttf
if exist "%FONT_SRC%" (
    if not exist assets mkdir assets
    copy "%FONT_SRC%" assets\font.ttf
    set FONT_FLAG=--add-data "assets\font.ttf;assets"
    echo =^> Bundling Cyrillic font from %FONT_SRC%
) else (
    set FONT_FLAG=
)

echo =^> Building with PyInstaller...
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --collect-all dearpygui ^
    --collect-all typst ^
    --collect-all PIL ^
    %FONT_FLAG% ^
    app.py

echo.
echo Done!  --^>  dist\app.exe
