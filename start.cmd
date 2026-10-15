@echo off
REM Double-click to start DueDil.Agent. Equivalent to: .\scripts\project.ps1 start
REM Nothing in this project starts by itself; this file is how you start it.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\project.ps1" start

echo.
echo The app is at http://localhost:8501  (close this window when you are done)
pause
