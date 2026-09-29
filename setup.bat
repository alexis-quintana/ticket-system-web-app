@echo off
REM ============================================================
REM setup.bat
REM Crea el entorno virtual (.venv) e instala las dependencias
REM del proyecto (Flask, PyMySQL) desde requirements.txt.
REM Se ejecuta UNA SOLA VEZ por PC / carpeta del proyecto.
REM ============================================================

REM Nos aseguramos de trabajar siempre en la carpeta donde esta este .bat,
REM sin importar desde donde se haya lanzado.
cd /d "%~dp0"

echo.
echo === Verificando entorno virtual (.venv) ===

if exist ".venv\Scripts\activate.bat" (
    echo El entorno .venv ya existe. Se omite la creacion.
) else (
    echo Creando entorno virtual...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo.
        echo [ERROR] No se pudo crear el entorno virtual.
        echo Verifica que Python este instalado y agregado al PATH.
        pause
        exit /b 1
    )
)

echo.
echo === Activando entorno virtual ===
call ".venv\Scripts\activate.bat"

echo.
echo === Instalando dependencias (requirements.txt) ===
pip install -r requirements.txt

echo.
echo === Listo ===
echo El entorno quedo creado e instalado en la carpeta .venv de este proyecto.
echo A partir de ahora, usa run.bat para levantar el servidor Flask.
echo.
pause
