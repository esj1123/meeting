@echo off
setlocal
cd /d "%~dp0"

set "PY_EXE="
set "PY_LABEL="

call :try_python py "Python launcher"
call :try_python python "Python on PATH"
call :try_python "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" "Codex bundled Python"

if not defined PY_EXE (
  echo No usable Python with tkinter was found.
  echo Checked: py, python, and %%USERPROFILE%%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
  echo Install Python with tkinter or run scripts\meeting_workflow_app.py with a working Python interpreter.
  pause
  exit /b 1
)

if /I "%~1"=="--check" (
  echo Using %PY_LABEL%: %PY_EXE%
  "%PY_EXE%" -c "import sys, tkinter; print(sys.executable); print('tkinter ok')"
  if errorlevel 1 exit /b 1
  "%PY_EXE%" scripts\meeting_workflow_app.py --check
  exit /b %errorlevel%
)

echo Starting 09_Meeting manual GPT workflow with %PY_LABEL%...
"%PY_EXE%" scripts\meeting_workflow_app.py
if errorlevel 1 (
  echo.
  echo START_MEETING_WORKFLOW failed.
  pause
  exit /b 1
)

endlocal
exit /b 0

:try_python
if defined PY_EXE exit /b 0
set "CANDIDATE=%~1"
if not exist "%CANDIDATE%" (
  if not "%~x1"=="" exit /b 0
)
"%CANDIDATE%" -c "import tkinter" >nul 2>nul
if not errorlevel 1 (
  set "PY_EXE=%CANDIDATE%"
  set "PY_LABEL=%~2"
)
exit /b 0
