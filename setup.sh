#!/usr/bin/env bash
set -e

echo "====================================================================="
echo "  INSTALADOR AUTOMATICO - CONTROL POR GESTOS Y VOZ"
echo "====================================================================="
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

NO_PROMPT=0
if [ "${1:-}" = "--no-prompt" ]; then
    NO_PROMPT=1
fi

find_python() {
    for candidate in "python3.12" "py -3.12" "python3.11" "python3.10" "python3" "python"; do
        if $candidate -c "import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 12) else 1)" >/dev/null 2>&1; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

PY_CMD="$(find_python || true)"
if [ -z "$PY_CMD" ]; then
    echo "[ERROR] Se requiere Python 3.10 - 3.12 (recomendado Python 3.12)."
    echo "        mediapipe==0.10.14 no es compatible con Python 3.13 o superior."
    exit 1
fi

PY_VER="$($PY_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")"
echo "[1/5] Python compatible detectado: $PY_CMD (v$PY_VER)"

if [ ! -d "venv" ]; then
    echo "[2/5] Creando entorno virtual en ./venv ..."
    $PY_CMD -m venv venv
else
    echo "[2/5] Entorno virtual ./venv ya existente (reutilizando)."
fi

if [ -f "venv/Scripts/python.exe" ]; then
    VENV_PY="venv/Scripts/python.exe"
    IS_WINDOWS=1
elif [ -f "venv/bin/python" ]; then
    VENV_PY="venv/bin/python"
    IS_WINDOWS=0
else
    echo "[ERROR] No se encontro el ejecutable de Python dentro de venv."
    exit 1
fi

echo "[3/5] Instalando dependencias en el entorno virtual..."
"$VENV_PY" -m pip install --upgrade pip --quiet

if [ "$IS_WINDOWS" = "1" ] && [ -f "wheels/PyAudio-0.2.14-cp312-cp312-win_amd64.whl" ]; then
    if "$VENV_PY" -c "import sys, platform; sys.exit(0 if sys.version_info[:2]==(3,12) and platform.machine().endswith('64') else 1)" >/dev/null 2>&1; then
        echo "      Instalando PyAudio precompilado desde wheels/ ..."
        "$VENV_PY" -m pip install "wheels/PyAudio-0.2.14-cp312-cp312-win_amd64.whl" --quiet
    fi
fi

if ! "$VENV_PY" -m pip install -r requirements.txt; then
    echo ""
    echo "[ERROR] Fallo la instalacion de dependencias."
    if [ "$IS_WINDOWS" = "0" ]; then
        echo "[TIP Linux/macOS] Si fallo PyAudio, instala portaudio antes:"
        echo "  Ubuntu/Debian: sudo apt-get install -y portaudio19-dev python3-tk"
        echo "  macOS:         brew install portaudio"
    fi
    exit 1
fi

echo "[4/5] Configurando variables de entorno (.env)..."
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
    cp ".env.example" ".env"
    echo "      Archivo .env creado desde .env.example."
    if [ "$NO_PROMPT" = "0" ] && [ -t 0 ]; then
        echo ""
        read -r -p "Ingresa tu GEMINI_API_KEY opcional (o presiona Enter para omitir): " USER_API_KEY || true
        if [ -n "${USER_API_KEY:-}" ]; then
            "$VENV_PY" -c "import sys, pathlib; p=pathlib.Path('.env'); k=sys.argv[1].strip(); txt=p.read_text(encoding='utf-8'); p.write_text(txt.replace('GEMINI_API_KEY=', f'GEMINI_API_KEY={k}', 1), encoding='utf-8')" "$USER_API_KEY"
            echo "      GEMINI_API_KEY guardada en .env."
        fi
    fi
elif [ -f ".env" ]; then
    echo "      Archivo .env existente detectado (se conserva sin cambios)."
fi

echo "[5/5] Precargando modelo de voz offline (Vosk ES) y verificando modulos..."
if "$VENV_PY" -c "import vosk; vosk.Model(lang='es')" >/dev/null 2>&1; then
    echo "      Modelo offline Vosk (es) listo en cache."
else
    echo "[AVISO] No se pudo descargar el modelo offline de Vosk (usara Google Speech si hay internet)."
fi

"$VENV_PY" -c "import config, state, launcher, game, gestos, voz, nlu; print('[OK] Todos los modulos verificados correctamente.')"

echo ""
echo "====================================================================="
echo "  INSTALACION COMPLETADA CON EXITO"
echo "====================================================================="
if [ "$IS_WINDOWS" = "1" ]; then
    echo "  Para iniciar el sistema:"
    echo "    ./venv/Scripts/python.exe main.py"
    echo "  Para elegir o cambiar el juego / activar Modo Libre:"
    echo "    ./venv/Scripts/python.exe main.py --config"
else
    echo "  Para iniciar el sistema:"
    echo "    ./venv/bin/python main.py"
    echo "  Para elegir o cambiar el juego / activar Modo Libre:"
    echo "    ./venv/bin/python main.py --config"
fi
echo "====================================================================="
