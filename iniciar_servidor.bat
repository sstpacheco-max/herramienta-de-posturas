@echo off
title Servidor de Vision Artificial - SST 4.0
echo ===================================================
echo   Iniciando Servidor de Vision Artificial SST 4.0
echo ===================================================
cd /d "D:\aplicacion de rastreo de  malas posturas y epps\cv_backend"
echo Directorio actual: %cd%
echo Activando entorno virtual y ejecutando main.py...
.\venv\Scripts\python.exe main.py
if %errorlevel% neq 0 (
    echo.
    echo ERROR: El servidor se detuvo de forma inesperada con codigo %errorlevel%.
    pause
)
pause
