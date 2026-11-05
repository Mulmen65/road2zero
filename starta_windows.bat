@echo off
rem Startar en Road2Zero-app lokalt: starta_windows.bat [plan^|cityscenario^|op]   (standard: plan)
cd /d "%~dp0"
set APP=%1
if "%APP%"=="" set APP=plan
if not exist "%APP%\streamlit_app.py" (
  echo Okand app: %APP%. Valj plan, cityscenario eller op.
  goto failure
)
if not exist .venv py -3.12 -m venv .venv
if errorlevel 1 goto failure
.venv\Scripts\python.exe -m pip install -q -r requirements.txt
if errorlevel 1 goto failure
.venv\Scripts\python.exe -m streamlit run %APP%\streamlit_app.py
goto end
:failure
echo Installationen kunde inte slutforas. Kontrollera Python 3.12 och internetanslutningen.
pause
:end
