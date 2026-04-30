@echo off
REM build-windows.bat — builds a portable single-file Windows executable
REM Run from the project root in a normal Command Prompt or PowerShell.

echo =^> Installing dependencies...
python -m pip install dearpygui typst pillow pyinstaller

REM Optional: bundle a Cyrillic UI font
set FONT_SRC=
for %%F in (
    "%WINDIR%\Fonts\arialuni.ttf"
    "%WINDIR%\Fonts\arial.ttf"
    "%WINDIR%\Fonts\segoeui.ttf"
    "%WINDIR%\Fonts\tahoma.ttf"
) do (
    if not defined FONT_SRC if exist %%~F set FONT_SRC=%%~F
)

if defined FONT_SRC (
    if not exist assets mkdir assets
    copy /Y "%FONT_SRC%" assets\font.ttf >nul
    set FONT_FLAG=--add-data "assets\font.ttf;assets"
    echo =^> Bundling Cyrillic font from %FONT_SRC%
) else (
    set FONT_FLAG=
    echo =^> No system Cyrillic font found; build will rely on target machine fonts
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
