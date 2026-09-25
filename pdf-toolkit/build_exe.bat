@echo off
REM Genere un .exe autonome dans dist\PDFToolkit\ (aucun Python requis pour l'utiliser)
cd /d "%~dp0"
if not exist .venv ( call lancer.bat & exit /b )
.venv\Scripts\pip install pyinstaller
.venv\Scripts\pyinstaller --noconfirm --windowed --name PDFToolkit app.py
echo.
echo Termine : dist\PDFToolkit\PDFToolkit.exe
pause
