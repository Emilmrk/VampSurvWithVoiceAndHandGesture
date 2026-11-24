# VampSurvWithVoiceAndHandGesture

Sistema de **Interacción Humano-Computador (IHC) y Accesibilidad** desarrollado en Python para controlar la computadora y jugar a **Vampire Survivors** (u otros títulos compatibles) sin necesidad de teclado ni ratón físico, combinando **Visión por Computador** y **Reconocimiento de Voz Inteligente**.

---

## Arquitectura del Proyecto

```text
├── main.py            # Punto de entrada, gestión de hilos y manejo seguro de Ctrl+C / --config
├── config.py          # Configuración global (cámara 60 FPS, sensibilidad, ROI, carga de .env)
├── state.py           # Estado compartido thread-safe entre hilos (AppState)
├── gestos.py          # Visión por computador (MediaPipe Hands, suavizado adaptativo, 120 Hz, HUD)
├── voz.py             # Captura y transcripción de voz (Vosk offline / Google Speech API)
├── nlu.py             # Intérprete NLU con Gemini API y rotación automática de modelos por cuota
├── launcher.py        # Selector interactivo de juego, auto-detección Steam y persistencia
├── game.py            # Simulación de periféricos (PyDirectInput/PyAutoGUI/SetCursorPos) y comandos
├── setup.bat          # Instalador automático todo-en-uno para Windows (CMD / PowerShell)
├── setup.sh           # Instalador automático todo-en-uno para Git Bash, Linux y macOS
├── testvoz.py         # Utilidad de diagnóstico rápido para micrófono y reconocimiento de voz
├── runandawait.py     # Utilidad de prueba para síntesis de voz (Text-to-Speech)
├── requirements.txt   # Dependencias del proyecto (Python 3.10 - 3.12)
├── .env.example       # Plantilla de variables de entorno (copiar a .env para usar Gemini NLU)
├── assets/            # Capturas de referencia y recursos del repositorio
├── screenshots/       # Capturas tomadas por comando de voz durante la ejecución (gitignored)
└── wheels/            # Instalador precompilado de PyAudio para Windows (Python 3.12)
```

---

## Características Principales

1. **Control Gestual Fluido y de Baja Latencia (60 FPS + Interpolador 120 Hz)**:
   - Auto-detección de cámara con backend DirectShow (`CAP_DSHOW`) y formato `MJPG` en Windows.
   - **Suavizado Adaptativo + Estabilización Anti-Desvío**: elimina micro-temblores en reposo, amortigua el desvío natural de los dedos al iniciar un pellizco y responde con agilidad al desplazarse.
   - **Histéresis de Pellizco y Zona Activa (ROI)**: evita clics fantasmas y reduce la fatiga del brazo.
   - **Modo Mouse** y **Modo Joystick Virtual (`WASD` / `Flechas`)** con detección de diagonales y pausa rápida (`[P]`).
2. **Reconocimiento de Voz Híbrido (Offline + NLU con Gemini)**:
   - Prioriza **Vosk** (procesamiento local offline con latencia < 50 ms) con respaldo automático en Google Web Speech API.
   - **Coincidencia local instantánea** (`< 1 ms`) con diccionario fonético y tolerancia fuzzy.
   - **Comprensión natural con Gemini API** (opcional, vía `.env`): interpreta frases naturales o transcripciones imprecisas y cuenta con **router dinámico de modelos** con enfriamiento automático por cuota.
3. **Selector Flexible de Juego y Modo Libre Persistente**:
   - Auto-detecta *Vampire Survivors* en bibliotecas comunes de Steam.
   - Permite elegir cualquier ejecutable o trabajar en **Modo Libre** (guardado en `user_config.json` y modificable con `--config`).
4. **Cierre Seguro Multiplataforma**:
   - Tecla **`Q`**, botón **`[X]`** de la ventana o **`Ctrl + C`** en consola liberan automáticamente clics y teclas mantenidas.

---

## Instalación Rápida (Recomendada)

El proyecto incluye instaladores automáticos que verifican Python (`3.10`–`3.12`, recomendado **3.12** por compatibilidad con `mediapipe==0.10.14`), crean el entorno virtual `venv`, instalan PyAudio/dependencias, generan `.env` y precargan el modelo offline de Vosk.

### Opción A: Instalación Automática en 1 paso

**En Windows (PowerShell o CMD):**
```powershell
git clone https://github.com/Emilmrk/VampSurvWithVoiceAndHandGesture.git
cd VampSurvWithVoiceAndHandGesture
.\setup.bat
```

**En Git Bash / Linux / macOS:**
```bash
git clone https://github.com/Emilmrk/VampSurvWithVoiceAndHandGesture.git
cd VampSurvWithVoiceAndHandGesture
bash setup.sh
```

### Opción B: Instalación Manual (paso a paso)

```powershell
# 1. Crear y activar entorno virtual con Python 3.12
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1

# 2. (Windows) Instalar PyAudio precompilado e instalar dependencias
pip install .\wheels\PyAudio-0.2.14-cp312-cp312-win_amd64.whl
pip install -r requirements.txt

# 3. Configurar comprensión natural opcional con Gemini API
Copy-Item .env.example .env
```

Edita `.env` si deseas habilitar interpretación natural con tu clave gratuita de [Google AI Studio](https://aistudio.google.com/apikey):
```env
GEMINI_API_KEY=tu_clave_de_api_aqui
GEMINI_MODEL=auto
```
*(El archivo `.env` está protegido por `.gitignore` para no exponer credenciales).*

---

## Ejecución

```powershell
# Iniciar el sistema completo (con el entorno virtual)
.\venv\Scripts\python.exe main.py

# Forzar el menú de selección de juego o cambiar entre Modo Libre y ejecutable
.\venv\Scripts\python.exe main.py --config

# Probar únicamente el micrófono y el reconocimiento de voz
.\venv\Scripts\python.exe testvoz.py
```

---

## Guía de Controles

### Gestos de la Mano y Atajos en Ventana
| Gesto / Atajo | Modo | Acción |
| :--- | :--- | :--- |
| **Mover dedo índice** | Mouse | Desplaza el cursor dentro de la Zona Activa (ROI). |
| **Inclinar la mano** | Joystick (`WASD`/`Flechas`) | Activa movimiento direccional y diagonales fuera de la zona muerta. |
| **Pellizco (Pulgar + Índice)** | Mouse / Joystick | Clic izquierdo sostenido (arrastre) / Tecla `Espacio` en Joystick. |
| **Pellizco (Pulgar + Medio)** | Mouse | Clic derecho (menús o cofres). |
| **Palma Abierta (5 dedos)** | Todos | **Freno de seguridad**: suelta al instante cualquier clic o tecla activa. |
| **Tecla `M`** (en ventana) | — | Alterna entre **Modo Mouse**, **Modo WASD** y **Modo Flechas**. |
| **Tecla `D`** (en ventana) | — | Activa o desactiva manualmente el **Modo Arrastre**. |
| **Tecla `P`** (en ventana) | — | **Pausa / Reanuda** el envío de clics, teclas y cursor sin cerrar la cámara. |
| **Tecla `Q` / `[X]` / `Ctrl+C`** | — | Cierra el programa de forma segura sin necesidad de voz. |

### Comandos de Voz
| Categoría | Comandos directos | Ejemplos naturales (con Gemini `.env`) |
| :--- | :--- | :--- |
| **Juego** | `"abrir juego"`, `"cerrar juego"` | *"inicia el juego"*, *"cierra vampire survivors"* |
| **Modos** | `"modo ratón"`, `"modo teclado"`, `"modo flechas"`, `"cambiar modo"` | *"quiero usar las flechitas"*, *"siguiente modo"* |
| **Movimiento** | `"mover"`, `"detener"`, `"arriba"`, `"abajo"`, `"izquierda"`, `"derecha"` | *"suelta el mouse"*, *"muévete hacia la derecha"* |
| **Acciones** | `"clic"`, `"clic derecho"`, `"doble clic"`, `"espacio"`, `"enter"`, `"escape"`, `"captura"` | *"pausa el juego"*, *"clic secundario"*, *"saca una foto"* |
| **Sistema** | `"salir del programa"` | *"cierra la aplicación"* |
