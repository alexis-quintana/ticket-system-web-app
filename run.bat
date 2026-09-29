@echo off
REM ============================================================
REM run.bat
REM Activa el entorno virtual (.venv) y arranca el servidor Flask.
REM Se ejecuta CADA VEZ que quieras levantar el proyecto.
REM Antes de correrlo, asegurate de tener Apache y MySQL
REM iniciados en el XAMPP Control Panel.
REM ============================================================

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo [ERROR] No se encontro el entorno virtual .venv
    echo Ejecuta primero setup.bat para crearlo.
    echo.
    pause
    exit /b 1
)

echo.
echo === Activando entorno virtual ===
call ".venv\Scripts\activate.bat"

echo.
echo === Iniciando servidor Flask ===
echo Recuerda tener Apache y MySQL activos en XAMPP.
echo.
flask --app main run --debug

pause
