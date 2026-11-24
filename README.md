# VampSurvWithVoiceAndHandGesture

Sistema de **Interacción Humano-Computador (IHC) y Accesibilidad** desarrollado en Python para controlar la computadora y jugar a **Vampire Survivors** (u otros títulos compatibles) sin necesidad de teclado ni ratón físico, combinando **Visión por Computador** y **Reconocimiento de Voz Inteligente**.

---

## Arquitectura del Proyecto

```text
├── main.py            # Punto de entrada, gestión de hilos y manejo seguro de Ctrl+C / --config
├── config.py          # Configuración global (cámara 60 FPS, sensibilidad, ROI, carga de .env)
├── state.py           # Estado compartido thread-safe entre hilos (AppState)
├── gestos.py          # Visión por computador (MediaPipe Hands, suavizado EMA, Joystick Virtual)
├── voz.py             # Captura y transcripción de voz (Vosk offline / Google Speech API)
├── nlu.py             # Intérprete NLU con Gemini API y rotación automática de modelos por cuota
├── launcher.py        # Selector interactivo de juego, auto-detección Steam y persistencia
├── game.py            # Simulación de periféricos (PyDirectInput/PyAutoGUI) y enrutador de comandos
├── testvoz.py         # Utilidad de diagnóstico rápido para micrófono y reconocimiento de voz
├── runandawait.py     # Utilidad de prueba para síntesis de voz (Text-to-Speech)
├── requirements.txt   # Dependencias del proyecto
├── .env.example       # Plantilla de variables de entorno (copiar a .env para usar Gemini NLU)
├── assets/            # Capturas de pantalla generadas y recursos
└── wheels/            # Instalador precompilado de PyAudio para Windows (Python 3.12)
```

---

## Características Principales

1. **Control Gestual de Baja Latencia (60 FPS)**:
   - Auto-detección de cámara con backend DirectShow (`CAP_DSHOW`) en Windows.
   - **Suavizado Exponencial (EMA)** y **Zona Activa de Interacción (ROI)** para evitar temblores en el cursor y reducir la fatiga del brazo.
   - **Modo Mouse** y **Modo Joystick Virtual (`WASD` / `Flechas`)** con detección de diagonales.
2. **Reconocimiento de Voz Híbrido (Offline + NLU con Gemini)**:
   - Prioriza **Vosk** (procesamiento local offline con latencia < 50 ms) con respaldo automático en Google Web Speech API.
   - **Coincidencia local instantánea** para comandos directos (`< 1 ms`).
   - **Comprensión natural con Gemini API** (opcional, vía `.env`): si el micrófono transcribe mal una palabra o hablas de forma natural (ej. *"pausa el juego por favor"*, *"suelta el mouse"*), Gemini interpreta la intención y ejecuta la acción correcta.
   - **Router dinámico de modelos**: lista automáticamente los modelos disponibles en tu cuenta de Google, prioriza el más avanzado y rota al siguiente si se agota la cuota, volviendo al modelo superior cuando la cuota se recupera.
3. **Selector Flexible de Juego y Modo Libre**:
   - Auto-detecta la instalación de *Vampire Survivors* en rutas comunes de Steam.
   - Permite elegir cualquier otro ejecutable `.exe` mediante explorador de archivos o trabajar en **Modo Libre** sin abrir ningún juego (guardando la preferencia en `user_config.json`).
4. **Cierre Seguro y Multiplataforma**:
   - Múltiples formas de detener el sistema sin depender de la voz: tecla **`q`**, botón **`[X]`** de la ventana o **`Ctrl + C`** en consola, liberando automáticamente clics y teclas activas.

---

## Instalación y Configuración

> [!TIP]
> Se recomienda ampliamente crear un **entorno virtual (`venv`)** para aislar las dependencias del proyecto y evitar conflictos con otras instalaciones de Python.

### 1. Clonar el repositorio y crear el entorno virtual
```powershell
git clone <URL_DEL_REPOSITORIO>
cd IHCfinal

# Crear entorno virtual (recomendado Python 3.12)
python -m venv venv

# Activar entorno virtual en Windows (PowerShell)
.\venv\Scripts\Activate.ps1
```
*(En Linux/macOS usa `source venv/bin/activate`. Si PowerShell bloquea scripts, ejecuta previamente `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`).*

### 2. Instalar dependencias
```powershell
pip install -r requirements.txt
```
*(Si `pyaudio` falla al compilar en Windows por falta de Visual C++ Build Tools, instala el paquete precompilado incluido):*
```powershell
pip install .\wheels\PyAudio-0.2.14-cp312-cp312-win_amd64.whl
```

### 3. Configurar comprensión natural con Gemini API (Opcional)
Copia la plantilla `.env.example` a un archivo `.env` en la raíz del proyecto e ingresa tu clave gratuita de [Google AI Studio](https://aistudio.google.com/apikey):

```powershell
Copy-Item .env.example .env
```
Edita `.env`:
```env
GEMINI_API_KEY=tu_clave_de_api_aqui
GEMINI_MODEL=auto
```
*(El archivo `.env` está incluido en `.gitignore` para proteger tus credenciales).*

---

## Ejecución

```powershell
# Iniciar el sistema completo (auto-detecta el juego o abre el asistente de configuración)
python main.py

# Forzar el menú de selección de juego o cambio de ruta
python main.py --config

# Probar únicamente el micrófono y el reconocimiento de voz
python testvoz.py
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
| **Tecla `Q` / `[X]` / `Ctrl+C`** | — | Cierra el programa de forma segura sin necesidad de voz. |

### Comandos de Voz
| Categoría | Comandos directos | Ejemplos naturales (con Gemini `.env`) |
| :--- | :--- | :--- |
| **Juego** | `"abrir juego"`, `"cerrar juego"` | *"inicia el juego"*, *"cierra vampire survivors"* |
| **Modos** | `"modo ratón"`, `"modo teclado"`, `"modo flechas"` | *"quiero usar las flechitas"*, *"cambia a mouse"* |
| **Movimiento** | `"mover"`, `"detener"`, `"arriba"`, `"abajo"`, `"izquierda"`, `"derecha"` | *"suelta el mouse"*, *"muévete hacia la derecha"* |
| **Acciones** | `"clic"`, `"doble clic"`, `"espacio"`, `"enter"`, `"escape"`, `"captura"` | *"pausa el juego"*, *"saca una foto"*, *"despacio"* |
| **Sistema** | `"salir del programa"` | *"cierra la aplicación"* |
