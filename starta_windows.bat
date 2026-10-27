@echo off
cd /d "%~dp0"
py -3.12 -m venv .venv
if errorlevel 1 goto failure
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failure
.venv\Scripts\python.exe -m streamlit run streamlit_app.py
goto end
:failure
echo Installationen kunde inte slutfas. Kontrollera Python 3.12 och internetanslutningen.
pause
:end
