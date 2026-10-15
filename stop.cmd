@echo off
REM Double-click to stop DueDil.Agent and free port 8501. Equivalent to: .\scripts\project.ps1 stop

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\project.ps1" stop

echo.
echo Everything of this project is stopped. Other projects are unaffected.
pause
