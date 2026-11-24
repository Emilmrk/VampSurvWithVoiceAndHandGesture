@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo =====================================================================
echo   INSTALADOR AUTOMATICO - CONTROL POR GESTOS Y VOZ (WINDOWS)
echo =====================================================================
echo.

cd /d "%~dp0"

set "PY_CMD="
py -3.12 -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)" >nul 2>&1
if %errorlevel%==0 (
    set "PY_CMD=py -3.12"
) else (
    python -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3, 10), (3, 11), (3, 12)) else 1)" >nul 2>&1
    if !errorlevel!==0 (
        set "PY_CMD=python"
    ) else (
        py -3.11 -c "import sys; sys.exit(0)" >nul 2>&1
        if !errorlevel!==0 (
            set "PY_CMD=py -3.11"
        ) else (
            py -3.10 -c "import sys; sys.exit(0)" >nul 2>&1
            if !errorlevel!==0 (
                set "PY_CMD=py -3.10"
            )
        )
    )
)

if "%PY_CMD%"=="" (
    echo [ERROR] Se requiere Python 3.10 - 3.12 ^(recomendado Python 3.12^).
    echo         mediapipe==0.10.14 no es compatible con Python 3.13 o superior.
    echo         Descarga Python 3.12 desde: https://www.python.org/downloads/
    exit /b 1
)

for /f "delims=" %%v in ('%PY_CMD% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"') do set "PY_VER=%%v"
echo [1/5] Python compatible detectado: %PY_CMD% ^(v%PY_VER%^)

if not exist "venv\Scripts\python.exe" (
    echo [2/5] Creando entorno virtual en .\venv ...
    %PY_CMD% -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual.
        exit /b 1
    )
) else (
    echo [2/5] Entorno virtual .\venv ya existente ^(reutilizando^).
)

set "VENV_PY=venv\Scripts\python.exe"

echo [3/5] Instalando dependencias en el entorno virtual...
"%VENV_PY%" -m pip install --upgrade pip --quiet

"%VENV_PY%" -c "import sys, platform; sys.exit(0 if sys.version_info[:2]==(3,12) and platform.machine().endswith('64') else 1)" >nul 2>&1
if %errorlevel%==0 if exist "wheels\PyAudio-0.2.14-cp312-cp312-win_amd64.whl" (
    echo       Instalando PyAudio precompilado desde wheels\ ...
    "%VENV_PY%" -m pip install "wheels\PyAudio-0.2.14-cp312-cp312-win_amd64.whl" --quiet
)

"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de dependencias en requirements.txt.
    exit /b 1
)

echo [4/5] Configurando variables de entorno ^(.env^)...
if not exist ".env" (
    if exist ".env.example" (
        copy /Y ".env.example" ".env" >nul
        echo       Archivo .env creado desde .env.example.
        if not "%~1"=="--no-prompt" (
            echo.
            set "USER_API_KEY="
            set /p "USER_API_KEY=Ingresa tu GEMINI_API_KEY opcional ^(o presiona Enter para omitir^): "
            if not "!USER_API_KEY!"=="" (
                "%VENV_PY%" -c "import sys, pathlib; p=pathlib.Path('.env'); k=sys.argv[1].strip(); txt=p.read_text(encoding='utf-8'); p.write_text(txt.replace('GEMINI_API_KEY=', f'GEMINI_API_KEY={k}', 1), encoding='utf-8')" "!USER_API_KEY!"
                echo       GEMINI_API_KEY guardada en .env.
            )
        )
    )
) else (
    echo       Archivo .env existente detectado ^(se conserva sin cambios^).
)

echo [5/5] Precargando modelo de voz offline ^(Vosk ES^) y verificando modulos...
"%VENV_PY%" -c "import vosk; vosk.Model(lang='es')" >nul 2>&1
if errorlevel 1 (
    echo [AVISO] No se pudo descargar el modelo offline de Vosk ^(usara Google Speech si hay internet^).
) else (
    echo       Modelo offline Vosk ^(es^) listo en cache.
)

"%VENV_PY%" -c "import config, state, launcher, game, gestos, voz, nlu; print('[OK] Todos los modulos verificados correctamente.')"
if errorlevel 1 (
    echo [ERROR] La verificacion de modulos fallo.
    exit /b 1
)

echo.
echo =====================================================================
echo   INSTALACION COMPLETADA CON EXITO
echo =====================================================================
echo   Para iniciar el sistema:
echo     .\venv\Scripts\python.exe main.py
echo.
echo   Para elegir o cambiar el juego / activar Modo Libre:
echo     .\venv\Scripts\python.exe main.py --config
echo =====================================================================
endlocal
